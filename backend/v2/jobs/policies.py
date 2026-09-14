"""Retry timing policies, isolated for deterministic tests."""

from __future__ import annotations

import hashlib


def retry_delay_seconds(
    *, job_id: str, attempt: int, retry_after_seconds: int | None, base_seconds: int = 5
) -> int:
    exponential = base_seconds * (2 ** max(0, attempt - 1))
    digest = hashlib.sha256(f"{job_id}:{attempt}".encode("utf-8")).digest()
    jitter = digest[0] % max(1, base_seconds)
    return max(retry_after_seconds or 0, exponential + jitter)
