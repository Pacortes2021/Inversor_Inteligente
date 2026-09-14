"""Identified, rate-limited backend access to the public SEC data APIs."""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Mapping, Protocol

import requests

from ...domain import Document, ProviderResult, SecCapture, SecFiling, SecIdentity, SecUnitFact
from ...domain.sec import decimal_from_sec
from ...jobs import RefreshRequest
from ..persistence import FactRepository, RawStore


IDENTITY_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


@dataclass(frozen=True)
class SecHttpResponse:
    status_code: int
    content: bytes
    headers: Mapping[str, str]


class SecTransport(Protocol):
    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> SecHttpResponse: ...


class RequestsSecTransport:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def get(self, url: str, *, headers: Mapping[str, str], timeout: float) -> SecHttpResponse:
        response = self.session.get(url, headers=dict(headers), timeout=timeout)
        return SecHttpResponse(response.status_code, response.content, dict(response.headers))


class SecRateLimiter:
    """A process-wide serial gate; default policy stays below SEC's published maximum."""

    def __init__(
        self,
        requests_per_second: float = 2.0,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_second <= 0 or requests_per_second > 10:
            raise ValueError("SEC request rate must be in (0, 10]")
        self.minimum_interval = 1.0 / requests_per_second
        self.monotonic = monotonic
        self.sleep = sleep
        self._lock = threading.Lock()
        self._last_request: float | None = None

    def acquire(self) -> None:
        with self._lock:
            now = self.monotonic()
            if self._last_request is not None:
                delay = self.minimum_interval - (now - self._last_request)
                if delay > 0:
                    self.sleep(delay)
                    now = self.monotonic()
            self._last_request = now


DEFAULT_SEC_RATE_LIMITER = SecRateLimiter()


def normalize_cik(value: object) -> str:
    rendered = str(value).strip().upper()
    if rendered.startswith("CIK"):
        rendered = rendered[3:]
    if not rendered.isdigit() or not 1 <= len(rendered) <= 10:
        raise ValueError("CIK must contain one to ten digits")
    return rendered.zfill(10)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    return next((value for key, value in headers.items() if key.lower() == target), None)


def retry_after_seconds(headers: Mapping[str, str], *, now: datetime, default: int) -> int:
    raw = _header(headers, "Retry-After")
    if raw is None:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        try:
            deadline = parsedate_to_datetime(raw)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0, math.ceil((deadline.astimezone(timezone.utc) - now).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            return default


class SecProvider:
    def __init__(
        self,
        *,
        contact: str,
        raw_store: RawStore,
        documents: FactRepository,
        transport: SecTransport | None = None,
        rate_limiter: SecRateLimiter = DEFAULT_SEC_RATE_LIMITER,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        timeout_seconds: float = 30,
    ) -> None:
        if "@" not in contact or any(character.isspace() for character in contact):
            raise ValueError("SEC contact must be an identified email address")
        self.headers = {
            "User-Agent": f"InversorInteligente/2.0 ({contact})",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        self.raw_store = raw_store
        self.documents = documents
        self.transport = transport or RequestsSecTransport()
        self.rate_limiter = rate_limiter
        self.clock = clock
        self.timeout_seconds = timeout_seconds

    def fetch(self, request: RefreshRequest) -> ProviderResult[SecCapture]:
        fetched_at = self.clock()
        try:
            url, cik = self._resource(request)
        except ValueError:
            return self._failure(request, "invalid_payload", fetched_at)

        self.rate_limiter.acquire()
        try:
            response = self.transport.get(
                url, headers=self.headers, timeout=self.timeout_seconds
            )
        except requests.RequestException:
            return self._failure(request, "provider_unavailable", self.clock())
        fetched_at = self.clock()

        if response.status_code in (403, 429):
            default = 600 if response.status_code == 403 else 60
            return self._failure(
                request,
                "rate_limited",
                fetched_at,
                retry_after=retry_after_seconds(response.headers, now=fetched_at, default=default),
            )
        if response.status_code == 401:
            return self._failure(request, "auth_required", fetched_at)
        if response.status_code == 404:
            return self._failure(request, "not_covered", fetched_at)
        if response.status_code < 200 or response.status_code >= 300:
            return self._failure(request, "provider_unavailable", fetched_at)

        document = self._store_document(
            capability=request.capability,
            url=url,
            response=response,
            fetched_at=fetched_at,
        )
        try:
            payload = json.loads(response.content, parse_float=str, parse_int=str)
            capture = self._parse_capture(
                capability=request.capability,
                payload=payload,
                document=document,
                requested_cik=cik,
                resource_key=request.resource_key,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._failure(request, "invalid_payload", fetched_at)
        return ProviderResult[SecCapture](
            provider="sec",
            capability=request.capability,
            status="success",
            data=[capture],
            source="sec_data_api",
            fetchedAt=fetched_at,
            retryAfterSeconds=None,
            error=None,
        )

    def _resource(self, request: RefreshRequest) -> tuple[str, str | None]:
        if request.provider != "sec":
            raise ValueError("SEC adapter only accepts provider=sec")
        if request.capability == "identity":
            return IDENTITY_URL, None
        raw_cik = request.parameters.get("cik", request.resource_key)
        cik = normalize_cik(raw_cik)
        if request.capability == "submissions":
            return SUBMISSIONS_URL.format(cik=cik), cik
        if request.capability == "companyfacts":
            return COMPANYFACTS_URL.format(cik=cik), cik
        raise ValueError("unsupported SEC capability")

    def _store_document(
        self,
        *,
        capability: str,
        url: str,
        response: SecHttpResponse,
        fetched_at: datetime,
    ) -> Document:
        blob = self.raw_store.put(response.content)
        media_type = (_header(response.headers, "Content-Type") or "application/json").split(
            ";", 1
        )[0]
        document = Document(
            documentId=f"sec-{capability}-{blob.sha256[:24]}",
            provider="sec",
            sha256=blob.sha256,
            relativePath=blob.relative_path,
            sourceUrl=url,
            mediaType=media_type,
            fetchedAt=fetched_at,
            sizeBytes=blob.size_bytes,
        )
        return self.documents.add_document(document)

    def _parse_capture(
        self,
        *,
        capability: str,
        payload: object,
        document: Document,
        requested_cik: str | None,
        resource_key: str,
    ) -> SecCapture:
        if not isinstance(payload, dict):
            raise ValueError("SEC payload root must be an object")
        if capability == "identity":
            ticker = resource_key.upper()
            identities = []
            for entry in payload.values():
                if not isinstance(entry, dict) or str(entry.get("ticker", "")).upper() != ticker:
                    continue
                identities.append(
                    SecIdentity(
                        cik=normalize_cik(entry["cik_str"]),
                        ticker=ticker,
                        title=str(entry["title"]),
                        exchange=str(entry["exchange"]) if entry.get("exchange") else None,
                        documentId=document.document_id,
                    )
                )
            return SecCapture(
                capability="identity", document=document, identities=identities
            )

        payload_cik = normalize_cik(payload["cik"])
        if payload_cik != requested_cik:
            raise ValueError("SEC payload CIK does not match request")
        if capability == "submissions":
            filings = self._parse_filings(payload, payload_cik, document.document_id)
            return SecCapture(
                capability="submissions",
                cik=payload_cik,
                document=document,
                filings=filings,
                entityName=str(payload.get("name")) if payload.get("name") else None,
            )
        if capability == "companyfacts":
            facts = self._parse_facts(payload, payload_cik, document.document_id)
            return SecCapture(
                capability="companyfacts",
                cik=payload_cik,
                document=document,
                facts=facts,
                entityName=str(payload.get("entityName")) if payload.get("entityName") else None,
            )
        raise ValueError("unsupported SEC capability")

    @staticmethod
    def _parse_filings(payload: dict, cik: str, document_id: str) -> list[SecFiling]:
        recent = payload["filings"]["recent"]
        if not isinstance(recent, dict):
            raise ValueError("SEC recent filings must be columnar data")
        required = ("accessionNumber", "form", "filingDate")
        columns = [recent[name] for name in required]
        if any(not isinstance(column, list) for column in columns):
            raise ValueError("SEC filing columns must be arrays")
        length = len(columns[0])
        if any(len(column) != length for column in columns):
            raise ValueError("SEC filing columns have inconsistent lengths")

        def optional(name: str, index: int):
            column = recent.get(name)
            if not isinstance(column, list) or index >= len(column):
                return None
            return column[index] or None

        return [
            SecFiling(
                cik=cik,
                accessionNumber=recent["accessionNumber"][index],
                form=recent["form"][index],
                filingDate=recent["filingDate"][index],
                reportDate=optional("reportDate", index),
                acceptanceDatetime=optional("acceptanceDateTime", index),
                primaryDocument=optional("primaryDocument", index),
                documentId=document_id,
            )
            for index in range(length)
        ]

    @staticmethod
    def _parse_facts(payload: dict, cik: str, document_id: str) -> list[SecUnitFact]:
        taxonomies = payload["facts"]
        if not isinstance(taxonomies, dict):
            raise ValueError("SEC facts must be grouped by taxonomy")
        parsed: list[SecUnitFact] = []
        for taxonomy, concepts in taxonomies.items():
            if not isinstance(concepts, dict):
                raise ValueError("SEC taxonomy must contain concepts")
            for tag, concept in concepts.items():
                if not isinstance(concept, dict) or not isinstance(concept.get("units"), dict):
                    raise ValueError("SEC concept must contain units")
                for unit, observations in concept["units"].items():
                    if not isinstance(observations, list):
                        raise ValueError("SEC unit observations must be an array")
                    for observation in observations:
                        if not isinstance(observation, dict):
                            raise ValueError("SEC observation must be an object")
                        fiscal_year = observation.get("fy")
                        parsed.append(
                            SecUnitFact(
                                cik=cik,
                                taxonomy=taxonomy,
                                tag=tag,
                                label=str(concept.get("label", tag)),
                                description=str(concept.get("description", "")),
                                unit=unit,
                                value=decimal_from_sec(observation["val"]),
                                start=observation.get("start"),
                                end=observation["end"],
                                filed=observation["filed"],
                                accessionNumber=observation["accn"],
                                form=observation["form"],
                                fiscalYear=int(fiscal_year) if fiscal_year is not None else None,
                                fiscalPeriod=(
                                    str(observation["fp"]) if observation.get("fp") else None
                                ),
                                frame=(
                                    str(observation["frame"])
                                    if observation.get("frame")
                                    else None
                                ),
                                documentId=document_id,
                            )
                        )
        return parsed

    @staticmethod
    def _failure(
        request: RefreshRequest,
        error: str,
        fetched_at: datetime,
        *,
        retry_after: int | None = None,
    ) -> ProviderResult[SecCapture]:
        return ProviderResult[SecCapture](
            provider="sec",
            capability=request.capability,
            status="failure",
            data=[],
            source="sec_data_api",
            fetchedAt=fetched_at,
            retryAfterSeconds=retry_after,
            error=error,
        )
