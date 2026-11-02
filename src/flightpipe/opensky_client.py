"""OpenSky Network REST client: OAuth2 client-credentials + /states/all + airport flights.

Flow (docs/FLOW.md step 1):
    ingest task -> OpenSkyClient.fetch_states() -> TokenManager.get_token()
                -> GET /states/all?lamin..lomax -> raw JSON dict

WHY OAuth2: OpenSky retired basic auth in March 2026; client credentials is
the only supported flow. Tokens live ~30 minutes, so we cache and refresh
60 s early instead of requesting a token on every call (saves auth round trips
and avoids hammering their auth server).

Failure handling (docs/FAILURE.md F-01..F-03):
  * 429 (daily credits exhausted) -> raise CreditsExhausted, do NOT retry
    (retrying burns nothing but time and looks abusive).
  * 5xx / timeouts -> retry with exponential backoff, then raise.
  * 401 -> refresh token once, then raise.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from flightpipe.config import BoundingBox, Settings

log = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 30  # WHY: never hang an Airflow worker slot forever
MAX_RETRIES = 3
TOKEN_REFRESH_MARGIN_S = 60


class OpenSkyError(RuntimeError):
    """Base error for OpenSky problems."""


class CreditsExhausted(OpenSkyError):
    """HTTP 429: daily API credits used up. Not retryable today."""


@dataclass
class _CachedToken:
    value: str
    expires_at: float


class TokenManager:
    """Fetches and caches an OAuth2 bearer token."""

    def __init__(self, client_id: str, client_secret: str, token_url: str, session: requests.Session):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._session = session
        self._cached: _CachedToken | None = None

    def get_token(self, force_refresh: bool = False) -> str:
        now = time.time()
        if (
            not force_refresh
            and self._cached is not None
            and now < self._cached.expires_at - TOKEN_REFRESH_MARGIN_S
        ):
            return self._cached.value

        resp = self._session.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        if resp.status_code != 200:
            # Never log the secret or the response body (may echo credentials).
            raise OpenSkyError(f"Token request failed with HTTP {resp.status_code}")
        payload = resp.json()
        self._cached = _CachedToken(
            value=payload["access_token"],
            expires_at=now + float(payload.get("expires_in", 1800)),
        )
        log.info("Obtained new OpenSky token (expires in %ss)", payload.get("expires_in"))
        return self._cached.value


class OpenSkyClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()
        self._tokens: TokenManager | None = None
        self.last_credits_remaining: int | None = None  # read by the DAG for run metrics
        if settings.has_opensky_credentials:
            self._tokens = TokenManager(
                settings.opensky_client_id,  # type: ignore[arg-type]
                settings.opensky_client_secret,  # type: ignore[arg-type]
                settings.opensky_token_url,
                self._session,
            )
        else:
            # Anonymous works but with far fewer daily credits. Warn loudly.
            log.warning("No OpenSky credentials set: using anonymous access (low credit limit)")

    def _headers(self, force_refresh: bool = False) -> dict[str, str]:
        if self._tokens is None:
            return {}
        return {"Authorization": f"Bearer {self._tokens.get_token(force_refresh)}"}

    def fetch_states(self, bbox: BoundingBox | None = None) -> dict:
        """Return the raw /states/all JSON for the bounding box.

        Returns a dict like {"time": 1730000000, "states": [[...], ...]}.
        "states" can be null when no aircraft are in the box; callers must
        handle that (see transform.parse_states).
        """
        bbox = bbox or self._settings.bbox
        return self._get("/states/all", bbox.as_params())

    def fetch_airport_flights(self, airport: str, direction: str, begin: int, end: int) -> list[dict]:
        """Arrivals or departures for one airport (ICAO code) between two unix times.

        Endpoint: /flights/arrival or /flights/departure (FEATURE-004).
        OpenSky builds this data in a nightly batch, so we only ask for
        COMPLETED UTC days (D-013). The interval must be under 7 days.
        HTTP 404 means "no flights found" and is returned as an empty list.
        """
        if direction not in ("arrival", "departure"):
            raise ValueError(f"direction must be 'arrival' or 'departure', got {direction!r}")
        if not 0 < end - begin < 7 * 86400:
            raise ValueError("OpenSky allows 0 < end - begin < 7 days for airport flights")
        data = self._get(
            f"/flights/{direction}",
            {"airport": airport, "begin": begin, "end": end},
            not_found_ok=True,
        )
        return data or []

    def _get(self, path: str, params: dict, not_found_ok: bool = False):
        """GET with the shared failure policy (FAILURE.md F-01..F-03).

        Used by every endpoint so retries, token refresh and credit tracking
        behave identically. Returns parsed JSON, or None for 404 when
        not_found_ok (OpenSky's way of saying "empty result").
        """
        url = f"{self._settings.opensky_api_url}{path}"
        refreshed = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._session.get(
                    url,
                    params=params,
                    headers=self._headers(force_refresh=refreshed),
                    timeout=REQUEST_TIMEOUT_S,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                log.warning("OpenSky network error on attempt %s: %s", attempt, exc)
                self._backoff(attempt)
                continue

            if resp.status_code == 200:
                remaining = resp.headers.get("X-Rate-Limit-Remaining")
                if remaining is not None:
                    self.last_credits_remaining = int(remaining)
                    log.info("OpenSky credits remaining today (%s): %s", path, remaining)
                return resp.json()
            if resp.status_code == 404 and not_found_ok:
                return None
            if resp.status_code == 429:
                raise CreditsExhausted(f"OpenSky daily credits exhausted for {path} (HTTP 429)")
            if resp.status_code == 401 and self._tokens is not None and not refreshed:
                refreshed = True  # token may have expired early; refresh once
                continue
            if 500 <= resp.status_code < 600:
                log.warning("OpenSky HTTP %s on attempt %s", resp.status_code, attempt)
                self._backoff(attempt)
                continue
            raise OpenSkyError(f"Unexpected OpenSky response HTTP {resp.status_code}")

        raise OpenSkyError(f"OpenSky failed after {MAX_RETRIES} attempts")

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(2**attempt, 30))
