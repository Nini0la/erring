from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from erring import crud
from erring.app import handle_user_message
from erring.config import Settings, load_settings
from erring.db import connect, initialize_database

LOGGER = logging.getLogger(__name__)
TELEGRAM_MESSAGE_LIMIT = 4096

CoreMessageHandler = Callable[..., Any]


def telegram_session_id(chat_id: int) -> str:
    return f"telegram:{chat_id}"


def split_telegram_response(
    response: str,
    *,
    limit: int = TELEGRAM_MESSAGE_LIMIT,
) -> list[str]:
    remaining = response.strip()
    if not remaining:
        return [""]

    chunks: list[str] = []
    while len(remaining) > limit:
        newline = remaining.rfind("\n", 0, limit + 1)
        space = remaining.rfind(" ", 0, limit + 1)
        boundary = max(newline, space)
        if boundary <= 0:
            boundary = limit
        chunks.append(remaining[:boundary].rstrip())
        remaining = remaining[boundary:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def ensure_telegram_identity(
    database_path: str | Path,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> dict[str, Any]:
    conn = connect(database_path)
    try:
        initialize_database(conn)
        identity = crud.get_telegram_identity(conn, telegram_user_id)
        user = (
            crud.get_user(conn, identity["user_id"])
            if identity is not None
            else crud.get_or_create_default_user(conn)
        )
        return crud.link_telegram_identity(
            conn,
            user_id=user["id"],
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            first_name=first_name,
        )
    finally:
        conn.close()


def process_telegram_text(
    database_path: str | Path,
    *,
    telegram_user_id: int,
    telegram_chat_id: int,
    content: str,
    username: str | None = None,
    first_name: str | None = None,
    core_handler: CoreMessageHandler = handle_user_message,
) -> str:
    conn = connect(database_path)
    try:
        initialize_database(conn)
        identity = crud.get_telegram_identity(conn, telegram_user_id)
        if identity is None:
            user = crud.get_or_create_default_user(conn)
            identity = crud.link_telegram_identity(
                conn,
                user_id=user["id"],
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                username=username,
                first_name=first_name,
            )
        else:
            identity = crud.link_telegram_identity(
                conn,
                user_id=identity["user_id"],
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                username=username,
                first_name=first_name,
            )

        result = core_handler(
            conn,
            user_id=identity["user_id"],
            session_id=telegram_session_id(telegram_chat_id),
            content=content,
        )
        return str(result.response)
    finally:
        conn.close()


def _is_allowed(settings: Settings, telegram_user_id: int) -> bool:
    return settings.telegram_allowed_user_id == telegram_user_id


def build_telegram_application(settings: Settings):
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    if not settings.telegram_bot_token or settings.telegram_bot_token == "replace_me":
        raise RuntimeError("Missing Telegram token. Set TELEGRAM_BOT_TOKEN in .env.")

    async def reject_unconfigured(update: Update) -> None:
        if update.effective_message is None or update.effective_user is None:
            return
        if settings.telegram_allowed_user_id is None:
            await update.effective_message.reply_text(
                "Telegram setup is incomplete. "
                f"Set TELEGRAM_ALLOWED_USER_ID={update.effective_user.id} in .env, "
                "then restart Erring."
            )
            return
        await update.effective_message.reply_text("This Erring bot is private.")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if (
            update.effective_message is None
            or update.effective_user is None
            or update.effective_chat is None
        ):
            return
        if not _is_allowed(settings, update.effective_user.id):
            await reject_unconfigured(update)
            return
        await asyncio.to_thread(
            ensure_telegram_identity,
            settings.database_path,
            telegram_user_id=update.effective_user.id,
            telegram_chat_id=update.effective_chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )
        await update.effective_message.reply_text(
            "Erring is connected. Send a message to continue."
        )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if update.effective_message is None or update.effective_user is None:
            return
        if not _is_allowed(settings, update.effective_user.id):
            await reject_unconfigured(update)
            return
        await update.effective_message.reply_text(
            "Send Erring a message about a commitment, project, or something "
            "you want help following through on."
        )

    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if (
            update.effective_message is None
            or update.effective_user is None
            or update.effective_chat is None
            or update.effective_message.text is None
        ):
            return
        if not _is_allowed(settings, update.effective_user.id):
            await reject_unconfigured(update)
            return

        await update.effective_chat.send_action(ChatAction.TYPING)
        try:
            response = await asyncio.to_thread(
                process_telegram_text,
                settings.database_path,
                telegram_user_id=update.effective_user.id,
                telegram_chat_id=update.effective_chat.id,
                content=update.effective_message.text,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
            )
        except Exception:
            LOGGER.exception(
                "Telegram message processing failed for user_id=%s chat_id=%s",
                update.effective_user.id,
                update.effective_chat.id,
            )
            await update.effective_message.reply_text(
                "Erring could not process that message. Check the local logs."
            )
            return

        for chunk in split_telegram_response(response):
            await update.effective_message.reply_text(chunk)

    async def handle_error(
        update: object,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        error = context.error
        LOGGER.error(
            "Unhandled Telegram transport error for update=%r",
            update,
            exc_info=(type(error), error, error.__traceback__) if error else None,
        )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .concurrent_updates(False)
        .build()
    )
    private = filters.ChatType.PRIVATE
    application.add_handler(CommandHandler("start", start, filters=private))
    application.add_handler(CommandHandler("help", help_command, filters=private))
    application.add_handler(
        MessageHandler(private & filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_error_handler(handle_error)
    return application


def run_telegram() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    application = build_telegram_application(settings)

    print("Erring Telegram adapter. Press Ctrl-C to stop.")
    print(f"DB: {settings.database_path}")
    print(f"Model: {settings.model}")
    if settings.telegram_allowed_user_id is None:
        print(
            "Setup mode: send /start to the bot, then add the displayed "
            "TELEGRAM_ALLOWED_USER_ID to .env and restart."
        )

    application.run_polling(allowed_updates=["message"])
    return 0
