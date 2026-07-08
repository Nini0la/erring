from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReflectionAction = Literal[
    "NO_ACTION",
    "ASK_CLARIFICATION",
    "CREATE_COMMITMENT",
    "UPDATE_COMMITMENT",
    "READ_COMMITMENTS",
    "ARCHIVE_COMMITMENT",
    "CREATE_PROJECT",
    "UPDATE_PROJECT",
    "READ_PROJECTS",
    "CREATE_OBSERVATION",
    "UPDATE_OBSERVATION",
    "READ_OBSERVATIONS",
]

READ_ACTIONS = {"READ_COMMITMENTS", "READ_PROJECTS", "READ_OBSERVATIONS"}
WRITE_ACTIONS = {
    "CREATE_COMMITMENT",
    "UPDATE_COMMITMENT",
    "ARCHIVE_COMMITMENT",
    "CREATE_PROJECT",
    "UPDATE_PROJECT",
    "CREATE_OBSERVATION",
    "UPDATE_OBSERVATION",
}
EXECUTABLE_ACTIONS = READ_ACTIONS | WRITE_ACTIONS


class ReflectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReflectionAction
    question: str | None = None
    reason: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_single_decision(self) -> ReflectionDecision:
        if self.action == "ASK_CLARIFICATION":
            if not self.question:
                raise ValueError("ASK_CLARIFICATION requires question")
            if self.arguments:
                raise ValueError("ASK_CLARIFICATION cannot include executable arguments")
        elif self.question:
            raise ValueError("Only ASK_CLARIFICATION may include question")

        if self.action in WRITE_ACTIONS and not self.arguments:
            raise ValueError(f"{self.action} requires arguments")

        if self.action == "NO_ACTION" and self.arguments:
            raise ValueError("NO_ACTION cannot include arguments")

        return self


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class CoreLoopResult(BaseModel):
    user_message_id: int
    assistant_message_id: int | None
    reflection: ReflectionDecision
    response: str
    operation_result: dict[str, Any] | list[dict[str, Any]] | None = None
