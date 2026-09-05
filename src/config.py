"""Application configuration.

Reads environment variables and safely loads the root .env file.
Does not make external network calls.
GEMINI_API_KEY is optional — the application starts cleanly without it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Robust project root resolution (src/config.py -> src/ -> root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV_PATH = PROJECT_ROOT / ".env"


def _ensure_env_loaded(env_path: Optional[Path | str] = None, override: bool = False) -> None:
    """Safely load .env file from project root or custom path without raising errors."""
    target_path = Path(env_path) if env_path is not None else ROOT_ENV_PATH
    if target_path.exists() and load_dotenv is not None:
        load_dotenv(dotenv_path=target_path, override=override)


# Ensure root .env is loaded on initial import
_ensure_env_loaded()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "gemini-embedding-2"
    app_name: str = "ClaimLens"
    app_version: str = "0.1.0"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


def load_settings(env_path: Optional[Path | str] = None, override: bool = False) -> Settings:
    """Load settings from environment variables, optionally loading from a .env file."""
    if env_path is not None:
        _ensure_env_loaded(env_path=env_path, override=override)
    else:
        _ensure_env_loaded(override=override)

    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
        gemini_embedding_model=os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip(),
        app_name=os.environ.get("APP_NAME", "ClaimLens").strip(),
        app_version=os.environ.get("APP_VERSION", "0.1.0").strip(),
        max_upload_size_bytes=int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))),
    )


def reload_settings() -> Settings:
    """Reload global settings instance from current os.environ."""
    global settings
    settings = load_settings()
    return settings


settings = load_settings()
