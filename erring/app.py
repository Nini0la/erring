from __future__ import annotations

import sqlite3

from erring import crud
from erring.context import build_conversation_messages, build_reflection_messages
from erring.conversation import run_conversation_call
from erring.llm import LLMCallable
from erring.models import CoreLoopResult
from erring.reflection import execute_reflection_action, run_reflection_call
from erring.summary import should_run_summary


def handle_user_message(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    session_id: str,
    content: str,
    reflection_completion_fn: LLMCallable | None = None,
    conversation_completion_fn: LLMCallable | None = None,
) -> CoreLoopResult:
    user_message = crud.save_message(conn, user_id, session_id, "user", content)

    reflection_messages = build_reflection_messages(
        conn,
        user_id=user_id,
        current_user_message=content,
    )
    decision = run_reflection_call(reflection_messages, completion_fn=reflection_completion_fn)

    operation_result = None
    operation_executed = None
    assistant_message = None

    if decision.action == "ASK_CLARIFICATION":
        response = decision.question or "Can you clarify that?"
        crud.write_operation_log(
            conn,
            user_id=user_id,
            session_id=session_id,
            message_id=user_message["id"],
            reflection_json=decision.model_dump(),
            operation_executed=None,
            result={"response": response},
        )
        assistant_message = crud.save_message(conn, user_id, session_id, "assistant", response)
        should_run_summary(conn, user_id=user_id)
        return CoreLoopResult(
            user_message_id=user_message["id"],
            assistant_message_id=assistant_message["id"],
            reflection=decision,
            response=response,
            operation_result=None,
        )

    if decision.action != "NO_ACTION":
        operation_result = execute_reflection_action(conn, user_id=user_id, decision=decision)
        operation_executed = decision.action

    crud.write_operation_log(
        conn,
        user_id=user_id,
        session_id=session_id,
        message_id=user_message["id"],
        reflection_json=decision.model_dump(),
        operation_executed=operation_executed,
        result=operation_result,
    )

    user = crud.get_user(conn, user_id)
    conversation_messages = build_conversation_messages(
        conn,
        user_id=user_id,
        current_user_message=content,
        operation_result=operation_result,
        cold_start=user["onboarding_status"] != "complete",
    )
    response = run_conversation_call(
        conversation_messages,
        completion_fn=conversation_completion_fn,
    )
    assistant_message = crud.save_message(conn, user_id, session_id, "assistant", response)
    should_run_summary(conn, user_id=user_id)

    return CoreLoopResult(
        user_message_id=user_message["id"],
        assistant_message_id=assistant_message["id"],
        reflection=decision,
        response=response,
        operation_result=operation_result,
    )

