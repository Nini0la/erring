from __future__ import annotations

import json

from erring import crud


def test_commitment_crud_defaults_to_uncategorized(conn):
    user = crud.create_user(conn)

    commitment = crud.create_commitment(
        conn,
        user["id"],
        "finish the OCR pipeline",
        time_status="untimed",
    )

    project = crud.get_project(conn, commitment["project_id"])
    assert project["name"] == "Uncategorized"
    assert commitment["status"] == "active"
    assert commitment["time_status"] == "untimed"
    assert json.loads(commitment["metadata_json"]) == {}


def test_read_update_and_archive_commitment(conn):
    user = crud.create_user(conn)
    commitment = crud.create_commitment(conn, user["id"], "write implementation plan")

    updated = crud.update_commitment(
        conn,
        commitment["id"],
        status="completed",
        notes="Done",
    )
    archived = crud.archive_commitment(conn, commitment["id"])
    active = crud.read_commitments(conn, user["id"])

    assert updated["completed_at"] is not None
    assert updated["notes"] == "Done"
    assert archived["status"] == "archived"
    assert active == []


def test_projects_observations_and_operation_log(conn):
    user = crud.create_user(conn)
    project = crud.create_project(conn, user["id"], "Erring")
    observation = crud.create_observation(
        conn,
        user["id"],
        "User wants core loops before demo work.",
        project_id=project["id"],
    )
    log = crud.write_operation_log(
        conn,
        user_id=user["id"],
        session_id="s1",
        message_id=None,
        reflection_json={"action": "CREATE_OBSERVATION"},
        operation_executed="CREATE_OBSERVATION",
        result=observation,
    )

    assert project["name"] == "Erring"
    assert observation["project_id"] == project["id"]
    assert log["operation_executed"] == "CREATE_OBSERVATION"
    assert "CREATE_OBSERVATION" in log["reflection_json"]

