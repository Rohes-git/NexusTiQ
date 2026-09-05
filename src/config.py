"""Application configuration.

Reads environment variables. Does not make external network calls.
GEMINI_API_KEY is optional — the application starts cleanly without it.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    app_name: str = "ClaimLens"
    app_version: str = "0.1.0"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


def _load_settings() -> Settings:
    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
    )


settings = _load_settings()
