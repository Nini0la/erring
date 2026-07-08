from __future__ import annotations

from erring import crud


def test_create_user_creates_uncategorized_project_and_summary(conn):
    user = crud.create_user(conn)

    projects = crud.read_projects(conn, user["id"])
    summary = crud.get_accumulated_experience(conn, user["id"])

    assert user["onboarding_status"] == "not_started"
    assert [project["name"] for project in projects] == ["Uncategorized"]
    assert summary["content"] == ""

