from __future__ import annotations

import pytest

from erring.llm import parse_reflection_json
from erring.models import ReflectionDecision


def test_clarification_requires_question():
    with pytest.raises(ValueError):
        ReflectionDecision(action="ASK_CLARIFICATION")


def test_clarification_cannot_include_arguments():
    with pytest.raises(ValueError):
        ReflectionDecision(
            action="ASK_CLARIFICATION",
            question="When?",
            arguments={"title": "finish OCR"},
        )


def test_write_action_requires_arguments():
    with pytest.raises(ValueError):
        ReflectionDecision(action="CREATE_COMMITMENT")


def test_parse_reflection_json():
    decision = parse_reflection_json(
        """
        {
          "action": "READ_COMMITMENTS",
          "arguments": {"time_status": "untimed"}
        }
        """
    )

    assert decision.action == "READ_COMMITMENTS"
    assert decision.arguments["time_status"] == "untimed"

