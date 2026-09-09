"""
Application configuration.

Settings are read from environment variables (with sensible local
defaults) rather than hard-coded, so the same code can point at a
different database in tests, local development, or (later) a real
deployment without any code changes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://opspilot:opspilot@localhost:5432/opspilot"

    # Default lookahead window for "who needs relief soon" queries.
    # Kept configurable (not hard-coded to 30) per the product requirement,
    # but 30 is a sensible operational default.
    default_relief_window_days: int = 30

    # Employees rotating off a site must have this many rest days before
    # they can start a new assignment. This models a simple, explainable
    # rest/rotation rule rather than a complex labor-law engine.
    minimum_rest_days: int = 2

    api_cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
