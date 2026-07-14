from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_path: Path
    model: str
    api_key: str | None
    base_url: str | None


def load_settings() -> Settings:
    load_dotenv()
    database_path = Path(os.environ.get("ERRING_DB_PATH", "erring.sqlite3"))
    model = os.environ.get("ERRING_MODEL", "deepseek-chat")
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("ERRING_BASE_URL", "https://api.deepseek.com")
    return Settings(database_path=database_path, model=model, api_key=api_key, base_url=base_url)
