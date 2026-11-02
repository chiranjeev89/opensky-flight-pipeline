"""Central configuration, read from environment variables only.

WHY: secrets must never live in code (docs/CONSTRAINTS.md rule C-03). Every
value here comes from the environment (.env locally, GitHub/Azure secrets in CI
or cloud). Defaults are safe for local development against Azurite.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Azurite's well-known *public* development key. It is not a secret: it is
# published by Microsoft and only works against the local emulator.
AZURITE_CONN_STR = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://azurite:10000/devstoreaccount1;"
)


@dataclass(frozen=True)
class BoundingBox:
    """Geographic box for the /states/all query.

    WHY a box and not worldwide: credit cost scales with area. Germany is
    7.79 x 9.17 = ~71 square degrees, which falls in the 25-100 sq deg
    tier (2 credits per call) instead of 4 credits for the whole world.
    See docs/DECISIONS.md D-002.
    """

    lamin: float = 47.27
    lomin: float = 5.87
    lamax: float = 55.06
    lomax: float = 15.04

    @property
    def area_sq_deg(self) -> float:
        return (self.lamax - self.lamin) * (self.lomax - self.lomin)

    def as_params(self) -> dict[str, float]:
        return {"lamin": self.lamin, "lomin": self.lomin, "lamax": self.lamax, "lomax": self.lomax}


def _env(name: str, default: str) -> str:
    """Env var, treating an EMPTY value as unset.

    WHY (BUG-003): docker compose `env_file: .env` passes `AZURE_STORAGE_CONNECTION_STRING=`
    as an empty string, and os.getenv(name, default) returns "" instead of the default.
    """
    return os.getenv(name) or default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    opensky_client_id: str | None = field(default_factory=lambda: os.getenv("OPENSKY_CLIENT_ID") or None)
    opensky_client_secret: str | None = field(
        default_factory=lambda: os.getenv("OPENSKY_CLIENT_SECRET") or None
    )
    opensky_api_url: str = field(
        default_factory=lambda: _env("OPENSKY_API_URL", "https://opensky-network.org/api")
    )
    opensky_token_url: str = field(
        default_factory=lambda: _env(
            "OPENSKY_TOKEN_URL",
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
        )
    )
    azure_conn_str: str = field(
        default_factory=lambda: _env("AZURE_STORAGE_CONNECTION_STRING", AZURITE_CONN_STR)
    )
    azure_container: str = field(default_factory=lambda: _env("AZURE_CONTAINER", "flight-lake"))
    local_lake_dir: str = field(default_factory=lambda: _env("LOCAL_LAKE_DIR", "/opt/lake"))
    bbox: BoundingBox = field(
        default_factory=lambda: BoundingBox(
            lamin=_float_env("BBOX_LAMIN", 47.27),
            lomin=_float_env("BBOX_LOMIN", 5.87),
            lamax=_float_env("BBOX_LAMAX", 55.06),
            lomax=_float_env("BBOX_LOMAX", 15.04),
        )
    )

    # FEATURE-004: airports for arrivals/departures (ICAO codes). Frankfurt + Munich
    # = Germany's two hubs. 2 airports x 2 directions = 4 API calls per day.
    airports: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            a.strip().upper() for a in _env("AIRPORTS", "EDDF,EDDM").split(",") if a.strip()
        )
    )

    @property
    def has_opensky_credentials(self) -> bool:
        return bool(self.opensky_client_id and self.opensky_client_secret)


def get_settings() -> Settings:
    """Build settings at call time (not import time) so tests can patch env vars."""
    return Settings()
