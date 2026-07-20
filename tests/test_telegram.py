from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from erring import crud
from erring.config import Settings
from erring.db import connect, initialize_database
from erring.telegram import (
    build_telegram_application,
    process_telegram_text,
    split_telegram_response,
    telegram_session_id,
)


def test_link_telegram_identity_updates_profile_without_changing_user(conn):
    user = crud.create_user(conn)

    created = crud.link_telegram_identity(
        conn,
        user_id=user["id"],
        telegram_user_id=123456,
        telegram_chat_id=123456,
        username="first_name",
        first_name="First",
    )
    updated = crud.link_telegram_identity(
        conn,
        user_id=user["id"],
        telegram_user_id=123456,
        telegram_chat_id=654321,
        username="updated_name",
        first_name="Updated",
    )

    assert created["user_id"] == user["id"]
    assert updated["id"] == created["id"]
    assert updated["telegram_chat_id"] == 654321
    assert updated["username"] == "updated_name"


def test_process_telegram_text_uses_existing_user_and_stable_session(tmp_path: Path):
    database_path = tmp_path / "telegram.sqlite3"
    conn = connect(database_path)
    initialize_database(conn)
    user = crud.create_user(conn)
    conn.close()
    received: dict = {}

    def fake_core_handler(conn, **kwargs):
        received.update(kwargs)
        assert crud.get_user(conn, kwargs["user_id"])["id"] == user["id"]
        return SimpleNamespace(response="Stored.")

    response = process_telegram_text(
        database_path,
        telegram_user_id=123456,
        telegram_chat_id=987654,
        content="I will finish the report tomorrow.",
        username="erring_owner",
        first_name="Owner",
        core_handler=fake_core_handler,
    )

    check_conn = connect(database_path)
    identity = crud.get_telegram_identity(check_conn, 123456)
    check_conn.close()

    assert response == "Stored."
    assert identity is not None
    assert identity["user_id"] == user["id"]
    assert received == {
        "user_id": user["id"],
        "session_id": telegram_session_id(987654),
        "content": "I will finish the report tomorrow.",
    }


def test_split_telegram_response_respects_message_limit():
    response = " ".join(["commitment"] * 1000)

    chunks = split_telegram_response(response, limit=100)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 100 for chunk in chunks)
    assert " ".join(chunks) == response


def test_build_telegram_application_requires_token(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "telegram.sqlite3",
        model="deepseek-chat",
        api_key=None,
        base_url="https://api.deepseek.com",
        telegram_bot_token=None,
        telegram_allowed_user_id=None,
    )

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        build_telegram_application(settings)


def test_build_telegram_application_registers_local_polling_handlers(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "telegram.sqlite3",
        model="deepseek-chat",
        api_key=None,
        base_url="https://api.deepseek.com",
        telegram_bot_token="123456:TEST_TOKEN",
        telegram_allowed_user_id=123456,
    )

    application = build_telegram_application(settings)

    assert sum(len(handlers) for handlers in application.handlers.values()) == 3
    assert application.bot.token == "123456:TEST_TOKEN"
