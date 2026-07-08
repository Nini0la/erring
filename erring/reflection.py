from __future__ import annotations

import sqlite3
from typing import Any

from erring import crud
from erring.llm import LLMCallable, call_openai_text, parse_reflection_json
from erring.models import ReflectionDecision


def run_reflection_call(
    messages,
    *,
    completion_fn: LLMCallable | None = None,
) -> ReflectionDecision:
    raw = (completion_fn or call_openai_text)(messages)
    return parse_reflection_json(raw)


def execute_reflection_action(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    decision: ReflectionDecision,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    action = decision.action
    args = decision.arguments

    if action in {"NO_ACTION", "ASK_CLARIFICATION"}:
        return None

    if action == "CREATE_COMMITMENT":
        return crud.create_commitment(
            conn,
            user_id,
            args["title"],
            project_id=args.get("project_id"),
            source_type=args.get("source_type", "explicit"),
            time_status=args.get("time_status", "untimed"),
            due_at=args.get("due_at"),
            notes=args.get("notes"),
            metadata=args.get("metadata") or args.get("metadata_json"),
        )

    if action == "UPDATE_COMMITMENT":
        commitment_id = args["commitment_id"]
        return crud.update_commitment(
            conn,
            commitment_id,
            title=args.get("title"),
            project_id=args.get("project_id"),
            status=args.get("status"),
            source_type=args.get("source_type"),
            time_status=args.get("time_status"),
            due_at=args.get("due_at"),
            completed_at=args.get("completed_at"),
            notes=args.get("notes"),
            metadata=args.get("metadata") or args.get("metadata_json"),
        )

    if action == "READ_COMMITMENTS":
        return crud.read_commitments(
            conn,
            user_id,
            status=args.get("status", "active"),
            time_status=args.get("time_status"),
            project_id=args.get("project_id"),
        )

    if action == "ARCHIVE_COMMITMENT":
        return crud.archive_commitment(conn, args["commitment_id"])

    if action == "CREATE_PROJECT":
        return crud.create_project(conn, user_id, args["name"], status=args.get("status", "active"))

    if action == "UPDATE_PROJECT":
        return crud.update_project(
            conn,
            args["project_id"],
            name=args.get("name"),
            status=args.get("status"),
        )

    if action == "READ_PROJECTS":
        return crud.read_projects(conn, user_id, status=args.get("status", "active"))

    if action == "CREATE_OBSERVATION":
        return crud.create_observation(
            conn,
            user_id,
            args["content"],
            project_id=args.get("project_id"),
        )

    if action == "UPDATE_OBSERVATION":
        return crud.update_observation(
            conn,
            args["observation_id"],
            content=args.get("content"),
            project_id=args.get("project_id"),
        )

    if action == "READ_OBSERVATIONS":
        return crud.read_observations(
            conn,
            user_id,
            project_id=args.get("project_id"),
            limit=args.get("limit", 20),
        )

    raise ValueError(f"Unhandled reflection action: {action}")

