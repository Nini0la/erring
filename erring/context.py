from __future__ import annotations

import json
import sqlite3
from typing import Any

from erring import crud
from erring.models import LLMMessage
from erring.prompts import load_system_with_task


def _json_block(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def build_reflection_messages(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    current_user_message: str,
    recent_limit: int = 12,
) -> list[LLMMessage]:
    recent = crud.get_recent_messages(conn, user_id, limit=recent_limit)
    commitments = crud.read_commitments(conn, user_id, status="active")
    projects = crud.read_projects(conn, user_id, status="active")
    observations = crud.read_observations(conn, user_id, limit=10)

    context = f"""
Recent conversation:
{_json_block(recent)}

Active projects:
{_json_block(projects)}

Active commitments:
{_json_block(commitments)}

Relevant observations:
{_json_block(observations)}

Latest user message:
{current_user_message}
""".strip()

    return [
        LLMMessage(role="system", content=load_system_with_task("reflection")),
        LLMMessage(role="user", content=context),
    ]


def build_conversation_messages(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    current_user_message: str,
    operation_result: Any = None,
    cold_start: bool = False,
    recent_limit: int = 12,
) -> list[LLMMessage]:
    task_prompt = "cold_start" if cold_start else "conversation"
    recent = crud.get_recent_messages(conn, user_id, limit=recent_limit)
    commitments = [] if cold_start else crud.read_commitments(conn, user_id, status="active")
    observations = [] if cold_start else crud.read_observations(conn, user_id, limit=10)
    experience = None if cold_start else crud.get_accumulated_experience(conn, user_id)

    context = f"""
Recent conversation:
{_json_block(recent)}

Active commitments:
{_json_block(commitments)}

Relevant observations:
{_json_block(observations)}

Accumulated experience:
{_json_block(experience)}

Operation or read result:
{_json_block(operation_result)}

Current user message:
{current_user_message}
""".strip()

    return [
        LLMMessage(role="system", content=load_system_with_task(task_prompt)),
        LLMMessage(role="user", content=context),
    ]


def build_summary_messages(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    unsummarized_limit: int = 50,
) -> list[LLMMessage]:
    current_summary = crud.get_accumulated_experience(conn, user_id)
    messages = crud.get_unsummarized_messages(conn, user_id, limit=unsummarized_limit)
    operation_rows = conn.execute(
        """
        SELECT * FROM operation_log
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    operations = [dict(row) for row in reversed(operation_rows)]

    context = f"""
Current accumulated experience:
{_json_block(current_summary)}

Unsummarized messages:
{_json_block(messages)}

Recent memory operations:
{_json_block(operations)}
""".strip()

    return [
        LLMMessage(role="system", content=load_system_with_task("summary")),
        LLMMessage(role="user", content=context),
    ]


def build_followthrough_messages(
    conn: sqlite3.Connection,
    *,
    user_id: int,
) -> list[LLMMessage]:
    commitments = crud.read_commitments(conn, user_id, status="active")
    untimed = crud.read_commitments(conn, user_id, status="active", time_status="untimed")

    context = f"""
Active commitments:
{_json_block(commitments)}

Untimed commitments:
{_json_block(untimed)}
""".strip()

    return [
        LLMMessage(role="system", content=load_system_with_task("followthrough")),
        LLMMessage(role="user", content=context),
    ]
