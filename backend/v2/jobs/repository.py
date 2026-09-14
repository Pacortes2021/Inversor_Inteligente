"""Transactional job leasing and last-valid cache persistence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from ..adapters.persistence import Database
from ..domain.common import canonical_json, jsonable, utc_datetime
from .models import Job, JobStatus, RefreshRequest
from .policies import retry_delay_seconds


class JobRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue(
        self, idempotency_key: str, request: RefreshRequest, *, now: datetime
    ) -> Job:
        now = utc_datetime(now)
        request_json = canonical_json(jsonable(request))
        request_hash = hashlib.sha256(request_json.encode("utf-8")).hexdigest()
        job_id = f"job-{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:24]}"
        timestamp = now.isoformat()
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise ValueError("idempotency key was already used for another request")
                return self._job(existing)
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id, idempotency_key, kind, request_json, request_hash,
                    status, attempt, max_attempts, progress, next_attempt_at,
                    cancel_requested, created_at, updated_at
                ) VALUES (?, ?, 'refresh', ?, ?, 'queued', 0, ?, 'queued', ?, 0, ?, ?)
                """,
                (
                    job_id,
                    idempotency_key,
                    request_json,
                    request_hash,
                    request.max_attempts,
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(row)

    def get(self, job_id: str) -> Job | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else self._job(row)

    def lease_is_current(self, job: Job, *, at: datetime) -> bool:
        with self.database.connect() as connection:
            try:
                self._owned_running(
                    connection,
                    job.job_id,
                    job.lease_owner or "",
                    at=utc_datetime(at),
                    expected_attempt=job.attempt,
                )
            except ValueError:
                return False
        return True

    def claim(self, worker_id: str, *, now: datetime, lease_seconds: int = 60) -> Job | None:
        now = utc_datetime(now)
        timestamp = now.isoformat()
        lease_expires_at = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE jobs SET status = 'cancelled', progress = 'cancelled',
                    lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE status = 'running' AND lease_expires_at <= ? AND cancel_requested = 1
                """,
                (timestamp, timestamp),
            )
            connection.execute(
                """
                UPDATE jobs SET status = 'failed', progress = 'lease_expired_attempts_exhausted',
                    lease_owner = NULL, lease_expires_at = NULL,
                    last_error = 'lease_expired', updated_at = ?
                WHERE status = 'running' AND lease_expires_at <= ?
                  AND cancel_requested = 0 AND attempt >= max_attempts
                """,
                (timestamp, timestamp),
            )
            connection.execute(
                """
                UPDATE jobs SET status = 'queued', progress = 'lease_recovered',
                    lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE status = 'running' AND lease_expires_at <= ?
                  AND cancel_requested = 0 AND attempt < max_attempts
                """,
                (timestamp, timestamp),
            )
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued' AND cancel_requested = 0
                  AND attempt < max_attempts AND next_attempt_at <= ?
                ORDER BY next_attempt_at, created_at, job_id LIMIT 1
                """,
                (timestamp,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE jobs SET status = 'running', attempt = attempt + 1,
                    progress = 'running', lease_owner = ?, lease_expires_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (worker_id, lease_expires_at, timestamp, row["job_id"]),
            )
            claimed = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
        return self._job(claimed)

    def complete(
        self,
        job_id: str,
        worker_id: str,
        *,
        now: datetime,
        partial: bool = False,
        expected_attempt: int | None = None,
    ) -> Job:
        now = utc_datetime(now)
        status = JobStatus.PARTIAL if partial else JobStatus.SUCCEEDED
        with self.database.transaction() as connection:
            self._owned_running(
                connection, job_id, worker_id, at=now, expected_attempt=expected_attempt
            )
            connection.execute(
                """
                UPDATE jobs SET status = ?, progress = ?, lease_owner = NULL,
                    lease_expires_at = NULL, updated_at = ? WHERE job_id = ?
                """,
                (status, status, now.isoformat(), job_id),
            )
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(row)

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        now: datetime,
        error: str,
        retry_after_seconds: int | None = None,
        expected_attempt: int | None = None,
    ) -> Job:
        now = utc_datetime(now)
        with self.database.transaction() as connection:
            row = self._owned_running(
                connection, job_id, worker_id, at=now, expected_attempt=expected_attempt
            )
            terminal = row["attempt"] >= row["max_attempts"]
            status = JobStatus.FAILED if terminal else JobStatus.QUEUED
            delay = retry_delay_seconds(
                job_id=job_id,
                attempt=row["attempt"],
                retry_after_seconds=retry_after_seconds,
            )
            next_attempt = now if terminal else now + timedelta(seconds=delay)
            connection.execute(
                """
                UPDATE jobs SET status = ?, progress = ?, last_error = ?,
                    next_attempt_at = ?, lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = ? WHERE job_id = ?
                """,
                (
                    status,
                    "failed" if terminal else "retry_scheduled",
                    error,
                    next_attempt.isoformat(),
                    now.isoformat(),
                    job_id,
                ),
            )
            updated = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(updated)

    def record_attempt(
        self,
        job: Job,
        *,
        now: datetime,
        status: str,
        error: str | None,
        retry_after_seconds: int | None,
    ) -> None:
        with self.database.transaction() as connection:
            self._owned_running(
                connection,
                job.job_id,
                job.lease_owner or "",
                at=utc_datetime(now),
                expected_attempt=job.attempt,
            )
            connection.execute(
                """
                INSERT INTO provider_attempts(
                    job_id, attempt, provider, capability, status, error,
                    retry_after_seconds, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.attempt,
                    job.request.provider,
                    job.request.capability,
                    status,
                    error,
                    retry_after_seconds,
                    utc_datetime(now).isoformat(),
                ),
            )

    def cancel(self, job_id: str, *, now: datetime) -> Job | None:
        now = utc_datetime(now)
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            if row["status"] == JobStatus.QUEUED:
                connection.execute(
                    "UPDATE jobs SET status = 'cancelled', progress = 'cancelled', cancel_requested = 1, updated_at = ? WHERE job_id = ?",
                    (now.isoformat(), job_id),
                )
            elif row["status"] == JobStatus.RUNNING:
                connection.execute(
                    "UPDATE jobs SET cancel_requested = 1, progress = 'cancellation_requested', updated_at = ? WHERE job_id = ?",
                    (now.isoformat(), job_id),
                )
            updated = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(updated)

    def acknowledge_cancel(self, job_id: str, worker_id: str, *, now: datetime) -> Job:
        now = utc_datetime(now)
        with self.database.transaction() as connection:
            row = self._owned_running(connection, job_id, worker_id, at=now)
            if not row["cancel_requested"]:
                raise ValueError("job cancellation was not requested")
            connection.execute(
                """
                UPDATE jobs SET status = 'cancelled', progress = 'cancelled',
                    lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (now.isoformat(), job_id),
            )
            updated = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(updated)

    @staticmethod
    def _owned_running(
        connection,
        job_id: str,
        worker_id: str,
        *,
        at: datetime | None = None,
        expected_attempt: int | None = None,
    ):
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None or row["status"] != JobStatus.RUNNING or row["lease_owner"] != worker_id:
            raise ValueError("worker does not own a running job lease")
        if at is not None and (
            row["lease_expires_at"] is None or row["lease_expires_at"] <= at.isoformat()
        ):
            raise ValueError("worker job lease has expired")
        if expected_attempt is not None and row["attempt"] != expected_attempt:
            raise ValueError("worker job attempt is stale")
        return row

    @staticmethod
    def _job(row) -> Job:
        return Job.model_validate(
            {
                "jobId": row["job_id"],
                "idempotencyKey": row["idempotency_key"],
                "kind": row["kind"],
                "request": json.loads(row["request_json"]),
                "status": row["status"],
                "attempt": row["attempt"],
                "maxAttempts": row["max_attempts"],
                "progress": row["progress"],
                "leaseOwner": row["lease_owner"],
                "leaseExpiresAt": row["lease_expires_at"],
                "nextAttemptAt": row["next_attempt_at"],
                "cancelRequested": bool(row["cancel_requested"]),
                "lastError": row["last_error"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
        )


class CacheRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def key(request: RefreshRequest) -> str:
        identity = {
            "provider": request.provider,
            "capability": request.capability,
            "resourceKey": request.resource_key,
            "parameters": request.parameters,
            "parserVersion": request.parser_version,
        }
        return hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()

    def store_valid(
        self,
        request: RefreshRequest,
        payload: list[Any],
        *,
        fetched_at: datetime,
        expires_at: datetime,
        job_id: str | None = None,
        worker_id: str | None = None,
        job_attempt: int | None = None,
        lease_at: datetime | None = None,
    ) -> None:
        key = self.key(request)
        fetched_at = utc_datetime(fetched_at)
        expires_at = utc_datetime(expires_at)
        with self.database.transaction() as connection:
            lease_fields = (job_id, worker_id, job_attempt, lease_at)
            if any(value is not None for value in lease_fields):
                if any(value is None for value in lease_fields):
                    raise ValueError("lease validation requires job, worker, attempt and timestamp")
                lease_at = utc_datetime(lease_at)
                job = connection.execute(
                    "SELECT status, attempt, lease_owner, lease_expires_at FROM jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
                if (
                    job is None
                    or job["status"] != JobStatus.RUNNING
                    or job["lease_owner"] != worker_id
                    or job["attempt"] != job_attempt
                    or job["lease_expires_at"] is None
                    or job["lease_expires_at"] <= lease_at.isoformat()
                ):
                    raise ValueError("cannot publish cache without a current job lease")
            connection.execute(
                """
                INSERT INTO cache_entries(
                    cache_key, provider, capability, resource_key, parser_version,
                    valid_payload_json, valid_fetched_at, valid_expires_at,
                    last_attempt_at, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    valid_payload_json = CASE
                        WHEN cache_entries.valid_fetched_at IS NULL
                          OR excluded.valid_fetched_at >= cache_entries.valid_fetched_at
                        THEN excluded.valid_payload_json ELSE cache_entries.valid_payload_json END,
                    valid_fetched_at = CASE
                        WHEN cache_entries.valid_fetched_at IS NULL
                          OR excluded.valid_fetched_at >= cache_entries.valid_fetched_at
                        THEN excluded.valid_fetched_at ELSE cache_entries.valid_fetched_at END,
                    valid_expires_at = CASE
                        WHEN cache_entries.valid_fetched_at IS NULL
                          OR excluded.valid_fetched_at >= cache_entries.valid_fetched_at
                        THEN excluded.valid_expires_at ELSE cache_entries.valid_expires_at END,
                    last_attempt_at = excluded.last_attempt_at,
                    last_error = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    request.provider,
                    request.capability,
                    request.resource_key,
                    request.parser_version,
                    canonical_json(payload),
                    fetched_at.isoformat(),
                    expires_at.isoformat(),
                    fetched_at.isoformat(),
                    fetched_at.isoformat(),
                ),
            )

    def record_failure(self, request: RefreshRequest, *, now: datetime, error: str) -> None:
        key = self.key(request)
        now = utc_datetime(now)
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO cache_entries(
                    cache_key, provider, capability, resource_key, parser_version,
                    last_attempt_at, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    last_attempt_at = excluded.last_attempt_at,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    request.provider,
                    request.capability,
                    request.resource_key,
                    request.parser_version,
                    now.isoformat(),
                    error,
                    now.isoformat(),
                ),
            )

    def last_valid(self, request: RefreshRequest) -> list[Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT valid_payload_json FROM cache_entries WHERE cache_key = ?",
                (self.key(request),),
            ).fetchone()
        if row is None or row["valid_payload_json"] is None:
            return None
        return json.loads(row["valid_payload_json"])
