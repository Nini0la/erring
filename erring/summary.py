from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from erring import crud
from erring.context import build_summary_messages
from erring.llm import LLMCallable, call_openai_text

SUMMARY_MESSAGE_THRESHOLD = 20
INACTIVITY_THRESHOLD = timedelta(minutes=30)


def should_run_summary(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    now: datetime | None = None,
) -> bool:
    if crud.count_unsummarized_messages(conn, user_id) >= SUMMARY_MESSAGE_THRESHOLD:
        return True

    latest = conn.execute(
        """
        SELECT created_at
        FROM conversation_messages
        WHERE user_id = ? AND summarized_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if latest is None:
        return False

    current_time = now or datetime.now(UTC)
    latest_time = datetime.fromisoformat(latest["created_at"])
    return current_time - latest_time >= INACTIVITY_THRESHOLD


def run_summary_call(
    messages,
    *,
    completion_fn: LLMCallable | None = None,
) -> str:
    return (completion_fn or call_openai_text)(messages).strip()


def maybe_update_summary(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    completion_fn: LLMCallable | None = None,
    force: bool = False,
) -> dict | None:
    if not force and not should_run_summary(conn, user_id=user_id):
        return None

    unsummarized = crud.get_unsummarized_messages(conn, user_id)
    if not unsummarized:
        return None

    messages = build_summary_messages(conn, user_id=user_id)
    updated_summary = run_summary_call(messages, completion_fn=completion_fn)
    summary = crud.update_accumulated_experience(conn, user_id, updated_summary)
    crud.mark_messages_summarized(conn, user_id, [message["id"] for message in unsummarized])
    return summary

