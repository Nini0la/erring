from __future__ import annotations

from erring.llm import LLMCallable, call_openai_text
from erring.models import LLMMessage


def run_conversation_call(
    messages: list[LLMMessage],
    *,
    completion_fn: LLMCallable | None = None,
) -> str:
    return (completion_fn or call_openai_text)(messages).strip()

