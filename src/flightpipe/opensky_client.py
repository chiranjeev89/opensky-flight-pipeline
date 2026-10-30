"""OpenSky Network REST client: OAuth2 client-credentials + /states/all.

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
        url = f"{self._settings.opensky_api_url}/states/all"
        refreshed = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._session.get(
                    url,
                    params=bbox.as_params(),
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
                    log.info("OpenSky credits remaining today: %s", remaining)
                return resp.json()
            if resp.status_code == 429:
                raise CreditsExhausted("OpenSky daily credits exhausted (HTTP 429)")
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
