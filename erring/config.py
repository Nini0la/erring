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
    telegram_bot_token: str | None
    telegram_allowed_user_id: int | None


def _optional_int(value: str | None, *, name: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_settings() -> Settings:
    load_dotenv()
    database_path = Path(os.environ.get("ERRING_DB_PATH", "erring.sqlite3"))
    model = os.environ.get("ERRING_MODEL", "deepseek-chat")
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("ERRING_BASE_URL", "https://api.deepseek.com")
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get(
        "TELEGRAM_TOKEN"
    )
    telegram_allowed_user_id = _optional_int(
        os.environ.get("TELEGRAM_ALLOWED_USER_ID"),
        name="TELEGRAM_ALLOWED_USER_ID",
    )
    return Settings(
        database_path=database_path,
        model=model,
        api_key=api_key,
        base_url=base_url,
        telegram_bot_token=telegram_bot_token,
        telegram_allowed_user_id=telegram_allowed_user_id,
    )
