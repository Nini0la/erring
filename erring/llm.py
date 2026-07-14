from __future__ import annotations

import json
import re
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
    if not settings.api_key:
        raise RuntimeError("Missing API key. Set DEEPSEEK_API_KEY in .env.")

    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    selected_model = model or settings.model

    response = client.chat.completions.create(
        model=selected_model,
        messages=_message_dicts(messages),
    )
    return _extract_response_text(response)


def call_openai_json(messages: list[LLMMessage], model: str | None = None) -> str:
    from openai import OpenAI

    settings = load_settings()
    if not settings.api_key:
        raise RuntimeError("Missing API key. Set DEEPSEEK_API_KEY in .env.")

    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    selected_model = model or settings.model
    response = client.chat.completions.create(
        model=selected_model,
        messages=_message_dicts(messages),
        response_format={"type": "json_object"},
    )
    return _extract_response_text(response)


def _extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        return text[start : end + 1]

    return text


def parse_reflection_json(raw_text: str) -> ReflectionDecision:
    json_text = _extract_json_object(raw_text)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Reflection output was not valid JSON") from exc

    try:
        return ReflectionDecision.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Reflection output did not match the expected contract") from exc
