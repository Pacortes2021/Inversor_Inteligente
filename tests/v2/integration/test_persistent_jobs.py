from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.v2.adapters.persistence import Database
from backend.v2.bootstrap import create_app
from backend.v2.domain import ProviderResult
from backend.v2.jobs import CacheRepository, JobRepository, RefreshRequest, Worker


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
REQUEST = RefreshRequest.model_validate(
    {
        "provider": "synthetic",
        "capability": "facts",
        "resourceKey": "issuer-a:annual",
        "parserVersion": "parser-v1",
        "parameters": {"issuerId": "issuer-a"},
        "maxAttempts": 3,
    }
)


class SequenceProvider:
    def __init__(self, results: list[ProviderResult]) -> None:
        self.results = list(results)

    def fetch(self, request: RefreshRequest) -> ProviderResult:
        return self.results.pop(0)


class LeaseStealingProvider:
    def __init__(self, jobs: JobRepository) -> None:
        self.jobs = jobs

    def fetch(self, request: RefreshRequest) -> ProviderResult:
        recovered = self.jobs.claim("worker-new", now=NOW + timedelta(seconds=60))
        assert recovered is not None and recovered.attempt == 2
        return result(
            status="success",
            data=[{"value": "stale-worker"}],
            fetched_at=NOW + timedelta(seconds=61),
        )


def result(
    *,
    status: str,
    data: list[dict],
    error: str | None = None,
    retry_after: int | None = None,
    fetched_at: datetime = NOW,
):
    return ProviderResult[dict].model_validate(
        {
            "provider": "synthetic",
            "capability": "facts",
            "status": status,
            "data": data,
            "source": "synthetic-test",
            "fetchedAt": fetched_at.isoformat(),
            "retryAfterSeconds": retry_after,
            "error": error,
        }
    )


@pytest.fixture
def repositories(tmp_path):
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    return database, JobRepository(database), CacheRepository(database)


def test_enqueue_is_idempotent_and_key_cannot_be_reused(repositories) -> None:
    database, jobs, _ = repositories
    first = jobs.enqueue("refresh-a", REQUEST, now=NOW)
    repeated = jobs.enqueue("refresh-a", REQUEST, now=NOW + timedelta(seconds=1))
    assert repeated.job_id == first.job_id
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1

    changed = REQUEST.model_copy(update={"resource_key": "issuer-b:annual"})
    with pytest.raises(ValueError, match="another request"):
        jobs.enqueue("refresh-a", changed, now=NOW)


def test_expired_lease_is_recovered_after_interruption(repositories) -> None:
    _, jobs, _ = repositories
    queued = jobs.enqueue("recover-a", REQUEST, now=NOW)
    first = jobs.claim("worker-old", now=NOW, lease_seconds=30)
    assert first is not None and first.job_id == queued.job_id and first.attempt == 1
    assert jobs.claim("worker-new", now=NOW + timedelta(seconds=29)) is None

    recovered = jobs.claim("worker-new", now=NOW + timedelta(seconds=30))
    assert recovered is not None
    assert recovered.job_id == queued.job_id
    assert recovered.lease_owner == "worker-new"
    assert recovered.attempt == 2


def test_expired_final_attempt_becomes_terminal(repositories) -> None:
    _, jobs, _ = repositories
    one_try = REQUEST.model_copy(update={"max_attempts": 1})
    queued = jobs.enqueue("one-attempt-a", one_try, now=NOW)
    assert jobs.claim("worker-old", now=NOW, lease_seconds=30) is not None
    assert jobs.claim("worker-new", now=NOW + timedelta(seconds=30)) is None
    exhausted = jobs.get(queued.job_id)
    assert exhausted is not None
    assert exhausted.status == "failed"
    assert exhausted.progress == "lease_expired_attempts_exhausted"
    assert exhausted.attempt == 1


def test_running_cancellation_is_cooperatively_acknowledged(repositories) -> None:
    _, jobs, _ = repositories
    jobs.enqueue("cancel-running-a", REQUEST, now=NOW)
    running = jobs.claim("worker-a", now=NOW)
    assert running is not None
    requested = jobs.cancel(running.job_id, now=NOW + timedelta(seconds=1))
    assert requested is not None and requested.cancel_requested is True
    cancelled = jobs.acknowledge_cancel(
        running.job_id, "worker-a", now=NOW + timedelta(seconds=2)
    )
    assert cancelled.status == "cancelled"
    assert cancelled.lease_owner is None


def test_a15_rate_limit_respects_retry_after_and_keeps_last_valid_cache(repositories) -> None:
    _, jobs, cache = repositories
    cache.store_valid(
        REQUEST,
        [{"value": "old-valid"}],
        fetched_at=NOW - timedelta(hours=2),
        expires_at=NOW - timedelta(hours=1),
    )
    jobs.enqueue("rate-limited-a", REQUEST, now=NOW)
    provider = SequenceProvider(
        [
            result(
                status="failure",
                data=[],
                error="rate_limited",
                retry_after=120,
                fetched_at=NOW + timedelta(seconds=45),
            ),
            result(status="success", data=[{"value": "new-valid"}]),
        ]
    )
    worker = Worker(
        worker_id="worker-a", jobs=jobs, cache=cache, providers={"synthetic": provider}
    )

    assert worker.run_once(now=NOW) is True
    waiting = jobs.get("job-" + hashlib.sha256(b"rate-limited-a").hexdigest()[:24])
    assert waiting is not None and waiting.status == "queued"
    assert waiting.next_attempt_at >= NOW + timedelta(seconds=165)
    assert cache.last_valid(REQUEST) == [{"value": "old-valid"}]
    assert worker.run_once(now=NOW + timedelta(seconds=119)) is False

    assert worker.run_once(now=waiting.next_attempt_at) is True
    assert cache.last_valid(REQUEST) == [{"value": "new-valid"}]
    assert jobs.get(waiting.job_id).status == "succeeded"


def test_worker_that_lost_its_lease_cannot_publish_cache(repositories) -> None:
    _, jobs, cache = repositories
    jobs.enqueue("lease-race-a", REQUEST, now=NOW)
    worker = Worker(
        worker_id="worker-old",
        jobs=jobs,
        cache=cache,
        providers={"synthetic": LeaseStealingProvider(jobs)},
    )
    assert worker.run_once(now=NOW) is True
    assert cache.last_valid(REQUEST) is None
    current = jobs.get("job-" + hashlib.sha256(b"lease-race-a").hexdigest()[:24])
    assert current is not None and current.lease_owner == "worker-new" and current.attempt == 2


def test_older_success_cannot_replace_a_newer_valid_cache_entry(repositories) -> None:
    _, _, cache = repositories
    cache.store_valid(
        REQUEST,
        [{"value": "newer"}],
        fetched_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    cache.store_valid(
        REQUEST,
        [{"value": "older"}],
        fetched_at=NOW - timedelta(days=1),
        expires_at=NOW - timedelta(hours=23),
    )
    assert cache.last_valid(REQUEST) == [{"value": "newer"}]


def test_cache_identity_includes_request_parameters(repositories) -> None:
    _, _, cache = repositories
    changed = REQUEST.model_copy(update={"parameters": {"issuerId": "issuer-b"}})
    cache.store_valid(
        REQUEST,
        [{"issuer": "a"}],
        fetched_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    cache.store_valid(
        changed,
        [{"issuer": "b"}],
        fetched_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    assert cache.last_valid(REQUEST) == [{"issuer": "a"}]
    assert cache.last_valid(changed) == [{"issuer": "b"}]


def test_refresh_api_reuses_job_and_supports_cancellation(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "data"))
    headers = {"Idempotency-Key": "api-refresh-a"}
    payload = REQUEST.model_dump(mode="json", by_alias=True)

    first = client.post("/api/v2/refreshes", json=payload, headers=headers)
    repeated = client.post("/api/v2/refreshes", json=payload, headers=headers)
    assert first.status_code == repeated.status_code == 202
    assert first.json()["jobId"] == repeated.json()["jobId"]

    job_id = first.json()["jobId"]
    cancelled = client.post(f"/api/v2/jobs/{job_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get(f"/api/v2/jobs/{job_id}").json()["status"] == "cancelled"
