from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    model: str


def load_settings() -> Settings:
    database_path = Path(os.environ.get("ERRING_DB_PATH", "erring.sqlite3"))
    model = os.environ.get("ERRING_MODEL", "gpt-4.1-mini")
    return Settings(database_path=database_path, model=model)

