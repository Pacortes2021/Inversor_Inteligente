"""One-job-at-a-time cooperative worker; scheduling remains an app concern."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..domain.providers import ProviderStatus
from ..ports.providers import ProviderPort
from .repository import CacheRepository, JobRepository


class Worker:
    def __init__(
        self,
        *,
        worker_id: str,
        jobs: JobRepository,
        cache: CacheRepository,
        providers: dict[str, ProviderPort],
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self.worker_id = worker_id
        self.jobs = jobs
        self.cache = cache
        self.providers = providers
        self.cache_ttl_seconds = cache_ttl_seconds

    def run_once(self, *, now: datetime) -> bool:
        job = self.jobs.claim(self.worker_id, now=now)
        if job is None:
            return False
        current = self.jobs.get(job.job_id)
        if current is not None and current.cancel_requested:
            self.jobs.acknowledge_cancel(job.job_id, self.worker_id, now=now)
            return True
        provider = self.providers.get(job.request.provider)
        if provider is None:
            error = "not_covered"
            self.cache.record_failure(job.request, now=now, error=error)
            self.jobs.record_attempt(
                job, now=now, status="failure", error=error, retry_after_seconds=None
            )
            self.jobs.fail(job.job_id, self.worker_id, now=now, error=error)
            return True

        try:
            result = provider.fetch(job.request)
        except Exception:
            error = "provider_unavailable"
            self.cache.record_failure(job.request, now=now, error=error)
            self.jobs.record_attempt(
                job, now=now, status="failure", error=error, retry_after_seconds=None
            )
            self.jobs.fail(job.job_id, self.worker_id, now=now, error=error)
            return True
        current = self.jobs.get(job.job_id)
        if current is not None and current.cancel_requested:
            self.jobs.acknowledge_cancel(job.job_id, self.worker_id, now=now)
            return True
        error = None if result.error is None else str(result.error)
        self.jobs.record_attempt(
            job,
            now=now,
            status=result.status,
            error=error,
            retry_after_seconds=result.retry_after_seconds,
        )
        if result.status in (ProviderStatus.SUCCESS, ProviderStatus.PARTIAL) and result.data:
            self.cache.store_valid(
                job.request,
                result.data,
                fetched_at=result.fetched_at,
                expires_at=result.fetched_at + timedelta(seconds=self.cache_ttl_seconds),
            )
            self.jobs.complete(
                job.job_id,
                self.worker_id,
                now=now,
                partial=result.status == ProviderStatus.PARTIAL,
            )
        elif result.status == ProviderStatus.SUCCESS:
            self.cache.store_valid(
                job.request,
                [],
                fetched_at=result.fetched_at,
                expires_at=result.fetched_at + timedelta(seconds=self.cache_ttl_seconds),
            )
            self.jobs.complete(job.job_id, self.worker_id, now=now)
        else:
            failure = error or "provider_unavailable"
            self.cache.record_failure(job.request, now=now, error=failure)
            self.jobs.fail(
                job.job_id,
                self.worker_id,
                now=now,
                error=failure,
                retry_after_seconds=result.retry_after_seconds,
            )
        return True
