"""
Application configuration.

Every setting is read from an environment variable - there is no
hard-coded database connection anywhere in this file. Locally, that
environment variable comes from a `.env` file you create yourself
(copy `.env.example` to `.env`); in a deployed environment (Render,
etc.) it comes from that platform's own environment variable
configuration. The application code never knows or cares which.

`DATABASE_URL` in particular has no default value on purpose: a
missing or wrong database is a configuration mistake that should fail
loudly and immediately (a clear error on startup), not silently fall
back to a value that happens to work on one developer's machine.
"""

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved as an absolute path (rather than the relative ".env" pydantic
# would otherwise resolve against the current working directory) so a
# backend/.env file is found the same way whether you run uvicorn from
# backend/, run alembic from backend/, or run pytest from the project
# root.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # No default: every environment (local, CI, Render) must set this
    # explicitly. See backend/.env.example for the local dev value.
    database_url: str

    # Default lookahead window for "who needs relief soon" queries.
    # Kept configurable (not hard-coded to 30) per the product requirement,
    # but 30 is a sensible operational default.
    default_relief_window_days: int = 30

    # Employees rotating off a site must have this many rest days before
    # they can start a new assignment. This models a simple, explainable
    # rest/rotation rule rather than a complex labor-law engine.
    minimum_rest_days: int = 2

    # The frontend origin(s) allowed to call this API, as a plain string:
    # a single origin, a comma-separated list
    # (https://kinvera.vercel.app,http://localhost:3000), or a JSON array
    # (["https://kinvera.vercel.app"]). Stored as `str` rather than
    # `list[str]` on purpose - pydantic-settings auto-JSON-decodes any
    # list-typed env var and rejects a plain comma-separated value before
    # our own parsing ever runs. `api_cors_origins` below does that
    # parsing and is what the rest of the app actually uses.
    api_cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias="API_CORS_ORIGINS")

    @property
    def api_cors_origins(self) -> list[str]:
        raw = self.api_cors_origins_raw.strip()
        if raw.startswith("["):
            return json.loads(raw)
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
