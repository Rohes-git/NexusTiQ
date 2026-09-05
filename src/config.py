"""Application configuration.

Reads environment variables. Does not make network calls.
GEMINI_API_KEY is optional in Milestone 1 — the app starts without it.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    app_name: str = "ClaimLens"
    app_version: str = "0.1.0"

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


def _load_settings() -> Settings:
    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )


settings = _load_settings()
