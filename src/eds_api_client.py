"""Date-bounded Energi Data Service client for the DK1 research project.

The guard rails in this module are part of the research design.  Every request
must remain inside the configured development period and area-scoped datasets
must explicitly request DK1.  The locked holdout is rejected before any
network call is made.
"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests
import yaml


BASE_URL = "https://api.energidataservice.dk/dataset"
DATASET_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
AREA_SCOPED_DATASETS = {
    "Elspotprices",
    "Forecasts_Hour",
    "ProductionConsumptionSettlement",
    "RegulatingBalancePowerdata",
    "Transmissionlines",
}


class ScopeViolation(ValueError):
    """Raised before a request that violates the frozen research boundary."""


class ApiResponseError(RuntimeError):
    """Raised when the API response is unavailable or structurally invalid."""


@dataclass(frozen=True)
class RequestSpec:
    dataset: str
    start_date: str
    end_date_exclusive: str
    filters: dict[str, list[str]] | None = None
    sort: str = "HourUTC"
    limit: int = 0
    timezone_name: str = "DK"


@dataclass(frozen=True)
class FetchResult:
    spec: RequestSpec
    payload: dict[str, Any]
    raw_bytes: bytes
    request_url: str
    retrieved_at_utc: str
    attempts: int
    response_headers: dict[str, str]


def _git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or None


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())


class BoundedEnergiDataClient:
    """Energi Data Service client that cannot cross the configured holdout."""

    def __init__(
        self,
        config_path: Path,
        *,
        session: requests.Session | None = None,
        timeout_seconds: float = 60.0,
        max_attempts: int = 4,
        max_retry_wait_seconds: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        unlock_holdout: bool = False,
    ) -> None:
        self.config_path = Path(config_path).resolve()
        self.repo_root = self.config_path.resolve().parents[1]
        config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        self.price_area = str(config["project"]["price_area"])
        self.boundary_timezone = str(config["periods"]["boundary_timezone"])
        self.development_start = date.fromisoformat(
            config["periods"]["development"]["start_date"]
        )
        holdout = config["periods"]["holdout"]
        if unlock_holdout:
            # P10.3 only: the owner-approved locked-holdout evaluation. The config
            # must have been deliberately unlocked (D036 / D037).
            if holdout["state"] == "locked" or holdout["fetch_allowed"] is not True:
                raise ScopeViolation(
                    "unlock_holdout requires the config holdout to be explicitly unlocked "
                    "(state != 'locked' and fetch_allowed: true)."
                )
            self.development_end_exclusive = date.fromisoformat("2025-01-01")
        else:
            self.development_end_exclusive = date.fromisoformat(
                config["periods"]["holdout"]["start_date"]
            )
            if holdout["state"] not in ("locked", "evaluated") or holdout["fetch_allowed"] is not False:
                raise ScopeViolation(
                    "The research config must keep the holdout locked (or 'evaluated' after the one-shot P10.3)."
                )

        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "dk1-power-market-research/0.1 (+bounded-development-client)",
                "Accept": "application/json",
            }
        )
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_retry_wait_seconds = max_retry_wait_seconds
        self.sleep = sleep

    def validate_spec(self, spec: RequestSpec) -> None:
        if not DATASET_PATTERN.fullmatch(spec.dataset):
            raise ScopeViolation(f"Unsafe dataset name: {spec.dataset!r}")

        start = date.fromisoformat(spec.start_date)
        end = date.fromisoformat(spec.end_date_exclusive)
        if start < self.development_start:
            raise ScopeViolation(
                f"Request starts before development: {start} < {self.development_start}."
            )
        if end > self.development_end_exclusive:
            raise ScopeViolation(
                "Request crosses the locked holdout boundary: "
                f"{end} > {self.development_end_exclusive}."
            )
        if start >= end:
            raise ScopeViolation("Request end must be later than request start.")
        if spec.timezone_name != "DK":
            raise ScopeViolation("Date boundaries must be submitted with timezone=DK.")
        if spec.limit < 0:
            raise ScopeViolation("API limit cannot be negative.")

        filters = spec.filters or {}
        if spec.dataset in AREA_SCOPED_DATASETS:
            requested_areas = filters.get("PriceArea")
            if requested_areas != [self.price_area]:
                raise ScopeViolation(
                    f"{spec.dataset} must explicitly filter PriceArea to "
                    f"[{self.price_area!r}]."
                )
        elif "PriceArea" in filters and filters["PriceArea"] != [self.price_area]:
            raise ScopeViolation("Any PriceArea filter must be restricted to DK1.")

    def request_params(self, spec: RequestSpec) -> dict[str, Any]:
        self.validate_spec(spec)
        params: dict[str, Any] = {
            "start": spec.start_date,
            "end": spec.end_date_exclusive,
            "sort": spec.sort,
            "limit": spec.limit,
            "timezone": spec.timezone_name,
        }
        if spec.filters:
            params["filter"] = json.dumps(
                spec.filters, ensure_ascii=False, separators=(",", ":")
            )
        return params

    def fetch(self, spec: RequestSpec) -> FetchResult:
        params = self.request_params(spec)
        url = f"{BASE_URL}/{spec.dataset}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as error:
                last_error = error
                if attempt == self.max_attempts:
                    break
                self.sleep(min(2 ** (attempt - 1), self.max_retry_wait_seconds))
                continue

            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                wait_seconds = retry_after if retry_after is not None else 2 ** attempt
                last_error = ApiResponseError(
                    f"HTTP 429 rate limit; Retry-After={response.headers.get('Retry-After')}"
                )
                if (
                    attempt == self.max_attempts
                    or wait_seconds > self.max_retry_wait_seconds
                ):
                    break
                self.sleep(wait_seconds)
                continue

            if 500 <= response.status_code < 600:
                last_error = ApiResponseError(f"HTTP {response.status_code}")
                if attempt == self.max_attempts:
                    break
                self.sleep(min(2 ** (attempt - 1), self.max_retry_wait_seconds))
                continue

            try:
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, requests.JSONDecodeError) as error:
                raise ApiResponseError(
                    f"Invalid response for {spec.dataset}: {error}"
                ) from error

            self._validate_payload(spec, payload)
            retained_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"content-type", "etag", "last-modified"}
            }
            return FetchResult(
                spec=spec,
                payload=payload,
                raw_bytes=response.content,
                request_url=response.url,
                retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                attempts=attempt,
                response_headers=retained_headers,
            )

        raise ApiResponseError(
            f"Request failed after {self.max_attempts} attempts: {last_error}"
        ) from last_error

    def _validate_payload(self, spec: RequestSpec, payload: Any) -> None:
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise ApiResponseError("API payload must be an object containing records[].")
        records = payload["records"]
        if payload.get("total") is not None:
            total = int(payload["total"])
            complete_response = spec.limit == 0 and total == len(records)
            valid_limited_response = (
                spec.limit > 0 and len(records) <= spec.limit and total >= len(records)
            )
            if not (complete_response or valid_limited_response):
                raise ApiResponseError(
                    "API total does not match the response size and request limit."
                )
        if not records:
            return

        frame = pd.DataFrame(records)
        if "HourUTC" in frame:
            utc = pd.to_datetime(frame["HourUTC"], utc=True, errors="raise")
            local_dates = utc.dt.tz_convert(self.boundary_timezone).dt.date
            start = date.fromisoformat(spec.start_date)
            end = date.fromisoformat(spec.end_date_exclusive)
            if not ((local_dates >= start) & (local_dates < end)).all():
                raise ScopeViolation("API returned rows outside the requested local dates.")
            if (local_dates >= self.development_end_exclusive).any():
                raise ScopeViolation("API returned a locked-holdout row.")

        if "PriceArea" in frame and not frame["PriceArea"].eq(self.price_area).all():
            raise ScopeViolation("API returned a non-DK1 price area.")

    def save(self, result: FetchResult, raw_path: Path, manifest_path: Path) -> None:
        raw_path = Path(raw_path)
        manifest_path = Path(manifest_path)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        raw_tmp = raw_path.with_suffix(raw_path.suffix + ".tmp")
        raw_tmp.write_bytes(result.raw_bytes)
        raw_tmp.replace(raw_path)

        manifest = {
            "source_organization": "Energinet",
            "retrieved_at_utc": result.retrieved_at_utc,
            "request": asdict(result.spec),
            "request_url": result.request_url,
            "attempts": result.attempts,
            "response_headers": result.response_headers,
            "api_reported_total": result.payload.get("total"),
            "records_returned": len(result.payload["records"]),
            "bytes": len(result.raw_bytes),
            "sha256": hashlib.sha256(result.raw_bytes).hexdigest(),
            "local_file": str(raw_path),
            "research_config": str(self.config_path.relative_to(self.repo_root)),
            "git_head_before_run": _git_head(self.repo_root),
            "holdout_state": "LOCKED_AND_NOT_REQUESTED",
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end-exclusive", required=True)
    parser.add_argument("--sort", default="HourUTC")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-price-area-filter", action="store_true")
    parser.add_argument("--raw-path", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("config/research_config.yaml")
    )
    args = parser.parse_args()

    filters = None if args.no_price_area_filter else {"PriceArea": ["DK1"]}
    spec = RequestSpec(
        dataset=args.dataset,
        start_date=args.start,
        end_date_exclusive=args.end_exclusive,
        filters=filters,
        sort=args.sort,
        limit=args.limit,
    )
    client = BoundedEnergiDataClient(args.config)
    result = client.fetch(spec)
    client.save(result, args.raw_path, args.manifest_path)
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "records": len(result.payload["records"]),
                "saved_to": str(args.raw_path),
                "manifest": str(args.manifest_path),
                "holdout": "LOCKED_AND_NOT_REQUESTED",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
