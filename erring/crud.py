from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from erring.db import rows_to_dicts

UNCATEGORIZED_PROJECT_NAME = "Uncategorized"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _fetch_one(conn: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> dict[str, Any]:
    row = conn.execute(query, params).fetchone()
    if row is None:
        raise LookupError("Expected row was not found")
    return dict(row)


def create_user(conn: sqlite3.Connection, onboarding_status: str = "not_started") -> dict[str, Any]:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO users (onboarding_status, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (onboarding_status, now, now),
    )
    user_id = cursor.lastrowid
    get_or_create_uncategorized_project(conn, user_id)
    conn.execute(
        """
        INSERT INTO experience_summaries (user_id, content, created_at, updated_at)
        VALUES (?, '', ?, ?)
        """,
        (user_id, now, now),
    )
    conn.commit()
    return get_user(conn, user_id)


def get_user(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))


def update_user_onboarding_status(
    conn: sqlite3.Connection, user_id: int, onboarding_status: str
) -> dict[str, Any]:
    now = utc_now()
    conn.execute(
        """
        UPDATE users
        SET onboarding_status = ?, updated_at = ?
        WHERE id = ?
        """,
        (onboarding_status, now, user_id),
    )
    conn.commit()
    return get_user(conn, user_id)


def get_or_create_uncategorized_project(
    conn: sqlite3.Connection, user_id: int
) -> dict[str, Any]:
    existing = conn.execute(
        """
        SELECT * FROM projects
        WHERE user_id = ? AND name = ?
        """,
        (user_id, UNCATEGORIZED_PROJECT_NAME),
    ).fetchone()
    if existing:
        return dict(existing)
    return create_project(conn, user_id, UNCATEGORIZED_PROJECT_NAME)


def save_message(
    conn: sqlite3.Connection,
    user_id: int,
    session_id: str,
    role: str,
    content: str,
) -> dict[str, Any]:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO conversation_messages (user_id, session_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, session_id, role, content, now),
    )
    conn.commit()
    return get_message(conn, cursor.lastrowid)


def get_message(conn: sqlite3.Connection, message_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM conversation_messages WHERE id = ?", (message_id,))


def get_recent_messages(
    conn: sqlite3.Connection, user_id: int, limit: int = 20
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM conversation_messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return list(reversed(rows_to_dicts(rows)))


def count_unsummarized_messages(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM conversation_messages
        WHERE user_id = ? AND summarized_at IS NULL
        """,
        (user_id,),
    ).fetchone()
    return int(row["count"])


def get_unsummarized_messages(
    conn: sqlite3.Connection, user_id: int, limit: int | None = None
) -> list[dict[str, Any]]:
    query = """
        SELECT * FROM conversation_messages
        WHERE user_id = ? AND summarized_at IS NULL
        ORDER BY id ASC
    """
    params: tuple[Any, ...]
    if limit is not None:
        query += " LIMIT ?"
        params = (user_id, limit)
    else:
        params = (user_id,)
    return rows_to_dicts(conn.execute(query, params).fetchall())


def mark_messages_summarized(
    conn: sqlite3.Connection,
    user_id: int,
    message_ids: list[int],
    summary_batch_id: str | None = None,
) -> None:
    if not message_ids:
        return
    now = utc_now()
    batch_id = summary_batch_id or str(uuid4())
    placeholders = ",".join("?" for _ in message_ids)
    conn.execute(
        f"""
        UPDATE conversation_messages
        SET summarized_at = ?, summary_batch_id = ?
        WHERE user_id = ? AND id IN ({placeholders})
        """,
        (now, batch_id, user_id, *message_ids),
    )
    conn.commit()


def create_project(
    conn: sqlite3.Connection,
    user_id: int,
    name: str,
    status: str = "active",
) -> dict[str, Any]:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO projects (user_id, name, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, name, status, now, now),
    )
    conn.commit()
    return get_project(conn, cursor.lastrowid)


def get_project(conn: sqlite3.Connection, project_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM projects WHERE id = ?", (project_id,))


def update_project(
    conn: sqlite3.Connection,
    project_id: int,
    *,
    name: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    current = get_project(conn, project_id)
    now = utc_now()
    conn.execute(
        """
        UPDATE projects
        SET name = ?, status = ?, updated_at = ?
        WHERE id = ?
        """,
        (name or current["name"], status or current["status"], now, project_id),
    )
    conn.commit()
    return get_project(conn, project_id)


def read_projects(
    conn: sqlite3.Connection,
    user_id: int,
    status: str | None = "active",
) -> list[dict[str, Any]]:
    if status is None:
        rows = conn.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY name ASC", (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM projects
            WHERE user_id = ? AND status = ?
            ORDER BY name ASC
            """,
            (user_id, status),
        ).fetchall()
    return rows_to_dicts(rows)


def create_commitment(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    *,
    project_id: int | None = None,
    source_type: str = "explicit",
    time_status: str = "untimed",
    due_at: str | None = None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = (
        get_project(conn, project_id)
        if project_id is not None
        else get_or_create_uncategorized_project(conn, user_id)
    )
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO commitments (
          user_id, project_id, title, status, source_type, time_status,
          due_at, created_at, updated_at, completed_at, notes, metadata_json
        )
        VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, NULL, ?, ?)
        """,
        (
            user_id,
            project["id"],
            title,
            source_type,
            time_status,
            due_at,
            now,
            now,
            notes,
            _json_dumps(metadata or {}),
        ),
    )
    conn.commit()
    return get_commitment(conn, cursor.lastrowid)


def get_commitment(conn: sqlite3.Connection, commitment_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM commitments WHERE id = ?", (commitment_id,))


def read_commitments(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    status: str | None = "active",
    time_status: str | None = None,
    project_id: int | None = None,
) -> list[dict[str, Any]]:
    clauses = ["user_id = ?"]
    params: list[Any] = [user_id]
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if time_status is not None:
        clauses.append("time_status = ?")
        params.append(time_status)
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT * FROM commitments
        WHERE {where}
        ORDER BY COALESCE(due_at, '9999-12-31T23:59:59') ASC, created_at ASC
        """,
        tuple(params),
    ).fetchall()
    return rows_to_dicts(rows)


def update_commitment(
    conn: sqlite3.Connection,
    commitment_id: int,
    *,
    title: str | None = None,
    project_id: int | None = None,
    status: str | None = None,
    source_type: str | None = None,
    time_status: str | None = None,
    due_at: str | None = None,
    completed_at: str | None = None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = get_commitment(conn, commitment_id)
    now = utc_now()
    next_status = status or current["status"]
    next_completed_at = completed_at
    if next_status == "completed" and not next_completed_at:
        next_completed_at = now
    elif next_status != "completed":
        next_completed_at = None

    conn.execute(
        """
        UPDATE commitments
        SET title = ?,
            project_id = ?,
            status = ?,
            source_type = ?,
            time_status = ?,
            due_at = ?,
            updated_at = ?,
            completed_at = ?,
            notes = ?,
            metadata_json = ?
        WHERE id = ?
        """,
        (
            title or current["title"],
            project_id or current["project_id"],
            next_status,
            source_type or current["source_type"],
            time_status or current["time_status"],
            due_at if due_at is not None else current["due_at"],
            now,
            next_completed_at,
            notes if notes is not None else current["notes"],
            _json_dumps(metadata) if metadata is not None else current["metadata_json"],
            commitment_id,
        ),
    )
    conn.commit()
    return get_commitment(conn, commitment_id)


def archive_commitment(conn: sqlite3.Connection, commitment_id: int) -> dict[str, Any]:
    return update_commitment(conn, commitment_id, status="archived")


def create_observation(
    conn: sqlite3.Connection,
    user_id: int,
    content: str,
    *,
    project_id: int | None = None,
) -> dict[str, Any]:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO observations (user_id, project_id, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, project_id, content, now, now),
    )
    conn.commit()
    return get_observation(conn, cursor.lastrowid)


def get_observation(conn: sqlite3.Connection, observation_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM observations WHERE id = ?", (observation_id,))


def update_observation(
    conn: sqlite3.Connection,
    observation_id: int,
    *,
    content: str | None = None,
    project_id: int | None = None,
) -> dict[str, Any]:
    current = get_observation(conn, observation_id)
    now = utc_now()
    conn.execute(
        """
        UPDATE observations
        SET content = ?, project_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            content or current["content"],
            project_id if project_id is not None else current["project_id"],
            now,
            observation_id,
        ),
    )
    conn.commit()
    return get_observation(conn, observation_id)


def read_observations(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    project_id: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if project_id is None:
        rows = conn.execute(
            """
            SELECT * FROM observations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM observations
            WHERE user_id = ? AND project_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, project_id, limit),
        ).fetchall()
    return rows_to_dicts(rows)


def get_accumulated_experience(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    return _fetch_one(conn, "SELECT * FROM experience_summaries WHERE user_id = ?", (user_id,))


def update_accumulated_experience(
    conn: sqlite3.Connection, user_id: int, content: str
) -> dict[str, Any]:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO experience_summaries (user_id, content, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          content = excluded.content,
          updated_at = excluded.updated_at
        """,
        (user_id, content, now, now),
    )
    conn.commit()
    return get_accumulated_experience(conn, user_id)


def write_operation_log(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    session_id: str,
    message_id: int | None,
    reflection_json: dict[str, Any],
    operation_executed: str | None,
    result: Any,
) -> dict[str, Any]:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO operation_log (
          user_id, session_id, message_id, reflection_json,
          operation_executed, result_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            session_id,
            message_id,
            _json_dumps(reflection_json),
            operation_executed,
            _json_dumps(result) if result is not None else None,
            now,
        ),
    )
    conn.commit()
    return _fetch_one(conn, "SELECT * FROM operation_log WHERE id = ?", (cursor.lastrowid,))
