from __future__ import annotations

from erring import crud
from erring.app import handle_user_message


def test_core_loop_returns_clarification_without_conversation_call(conn):
    user = crud.create_user(conn)

    result = handle_user_message(
        conn,
        user_id=user["id"],
        session_id="s1",
        content="Remind me to finish the OCR pipeline.",
        reflection_completion_fn=lambda messages: """
        {
          "action": "ASK_CLARIFICATION",
          "question": "When would you like to finish it?",
          "reason": "The commitment is missing a timeline."
        }
        """,
        conversation_completion_fn=lambda messages: "should not be used",
    )

    assert result.response == "When would you like to finish it?"
    assert result.reflection.action == "ASK_CLARIFICATION"
    assert crud.read_commitments(conn, user["id"]) == []


def test_core_loop_executes_create_commitment_and_conversation(conn):
    user = crud.create_user(conn)

    result = handle_user_message(
        conn,
        user_id=user["id"],
        session_id="s1",
        content="I do not know yet. Keep it untimed.",
        reflection_completion_fn=lambda messages: """
        {
          "action": "CREATE_COMMITMENT",
          "arguments": {
            "title": "finish the OCR pipeline",
            "source_type": "explicit",
            "time_status": "untimed"
          }
        }
        """,
        conversation_completion_fn=lambda messages: "Got it. I stored that as untimed.",
    )

    commitments = crud.read_commitments(conn, user["id"])

    assert result.response == "Got it. I stored that as untimed."
    assert result.reflection.action == "CREATE_COMMITMENT"
    assert len(commitments) == 1
    assert commitments[0]["title"] == "finish the OCR pipeline"
    assert commitments[0]["time_status"] == "untimed"


def test_core_loop_executes_read_commitments(conn):
    user = crud.create_user(conn)
    crud.create_commitment(conn, user["id"], "finish the OCR pipeline")

    result = handle_user_message(
        conn,
        user_id=user["id"],
        session_id="s1",
        content="What active commitments do I have?",
        reflection_completion_fn=lambda messages: """
        {
          "action": "READ_COMMITMENTS",
          "arguments": {"status": "active"}
        }
        """,
        conversation_completion_fn=lambda messages: "You have one: finish the OCR pipeline.",
    )

    assert result.response == "You have one: finish the OCR pipeline."
    assert isinstance(result.operation_result, list)
    assert result.operation_result[0]["title"] == "finish the OCR pipeline"

