from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_FILES = {
    "general_system": "general_system.md",
    "reflection": "reflection.md",
    "conversation": "conversation.md",
    "summary": "summary.md",
    "followthrough": "followthrough.md",
    "cold_start": "cold_start.md",
}


def load_prompt(name: str) -> str:
    try:
        filename = PROMPT_FILES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt: {name}") from exc
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def load_system_with_task(task_name: str) -> str:
    return f"{load_prompt('general_system')}\n\n{load_prompt(task_name)}"

