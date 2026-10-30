"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("AEGIS_ENV", "development")
    rate_limit_per_minute: int = int(os.getenv("AEGIS_RATE_LIMIT", "100/minute").split("/")[0])
    model_dir: Path = BASE_DIR / os.getenv("AEGIS_MODEL_DIR", "models/dlp_slm")
    allowed_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv(
        "AEGIS_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
    ).split(",") if x.strip() and x.strip() != "chrome-extension://*")
    store_redacted_preview: bool = os.getenv("AEGIS_STORE_REDACTED_PREVIEW", "false").lower() == "true"


settings = Settings()
