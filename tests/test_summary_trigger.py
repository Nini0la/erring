from __future__ import annotations

from datetime import UTC, datetime, timedelta

from erring import crud
from erring.summary import maybe_update_summary, should_run_summary


def test_summary_triggers_after_20_unsummarized_messages(conn):
    user = crud.create_user(conn)
    for i in range(20):
        crud.save_message(conn, user["id"], "s1", "user", f"message {i}")

    assert should_run_summary(conn, user_id=user["id"]) is True


def test_summary_triggers_after_30_minutes_inactivity(conn):
    user = crud.create_user(conn)
    crud.save_message(conn, user["id"], "s1", "user", "old message")
    latest = conn.execute(
        "SELECT created_at FROM conversation_messages WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    now = datetime.fromisoformat(latest["created_at"]) + timedelta(minutes=31)

    assert should_run_summary(conn, user_id=user["id"], now=now) is True


def test_maybe_update_summary_marks_messages_summarized(conn):
    user = crud.create_user(conn)
    for i in range(2):
        crud.save_message(conn, user["id"], "s1", "user", f"message {i}")

    result = maybe_update_summary(
        conn,
        user_id=user["id"],
        force=True,
        completion_fn=lambda messages: "Updated compressed understanding.",
    )

    assert result["content"] == "Updated compressed understanding."
    assert crud.count_unsummarized_messages(conn, user["id"]) == 0


def test_summary_does_not_trigger_for_recent_short_history(conn):
    user = crud.create_user(conn)
    crud.save_message(conn, user["id"], "s1", "user", "recent message")

    assert should_run_summary(conn, user_id=user["id"], now=datetime.now(UTC)) is False

