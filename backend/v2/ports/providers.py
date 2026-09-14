"""Narrow provider interface consumed by the persistent worker."""

from __future__ import annotations

from typing import Any, Protocol

from ..domain.providers import ProviderResult
from ..jobs.models import RefreshRequest


class ProviderPort(Protocol):
    def fetch(self, request: RefreshRequest) -> ProviderResult[Any]: ...
