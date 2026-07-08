from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from erring.config import load_settings
from erring.models import LLMMessage, ReflectionDecision

LLMCallable = Callable[[list[LLMMessage]], str]


def _message_dicts(messages: list[LLMMessage]) -> list[dict[str, str]]:
    return [message.model_dump() for message in messages]


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    choices = getattr(response, "choices", None)
    if choices:
        message = choices[0].message
        return str(message.content)

    raise RuntimeError("Could not extract text from LLM response")


def call_openai_text(messages: list[LLMMessage], model: str | None = None) -> str:
    from openai import OpenAI

    settings = load_settings()
    client = OpenAI()
    selected_model = model or settings.model

    if hasattr(client, "responses"):
        response = client.responses.create(
            model=selected_model,
            input=_message_dicts(messages),
        )
    else:
        response = client.chat.completions.create(
            model=selected_model,
            messages=_message_dicts(messages),
        )
    return _extract_response_text(response)


def parse_reflection_json(raw_text: str) -> ReflectionDecision:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Reflection output was not valid JSON") from exc

    try:
        return ReflectionDecision.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Reflection output did not match the expected contract") from exc

