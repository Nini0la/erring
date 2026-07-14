from __future__ import annotations

import argparse
from uuid import uuid4

from erring import crud
from erring.app import handle_user_message
from erring.config import load_settings
from erring.db import connect, initialize_database


def _get_or_create_default_user(conn) -> dict:
    row = conn.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1").fetchone()
    if row is not None:
        return dict(row)
    return crud.create_user(conn)


def run_chat() -> int:
    settings = load_settings()
    conn = connect(settings.database_path)
    initialize_database(conn)
    user = _get_or_create_default_user(conn)
    session_id = str(uuid4())

    print("Erring CLI. Type /quit to exit.")
    print(f"DB: {settings.database_path}")
    print(f"Model: {settings.model}")

    while True:
        try:
            content = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not content:
            continue
        if content in {"/q", "/quit", "/exit"}:
            return 0

        try:
            result = handle_user_message(
                conn,
                user_id=user["id"],
                session_id=session_id,
                content=content,
            )
        except Exception as exc:
            print(f"Erring error: {exc}")
            continue

        print(f"Erring: {result.response}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="erring")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("chat", help="Start an interactive Erring chat session")

    args = parser.parse_args()
    if args.command in {None, "chat"}:
        return run_chat()

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

