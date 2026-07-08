from __future__ import annotations

from erring.context import build_followthrough_messages
from erring.llm import LLMCallable, call_openai_text


def run_followthrough_call(messages, *, completion_fn: LLMCallable | None = None) -> str:
    return (completion_fn or call_openai_text)(messages).strip()


__all__ = ["build_followthrough_messages", "run_followthrough_call"]

