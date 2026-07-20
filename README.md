# erring
A persistent memory agent that remembers, clarifies, and keeps your commitments. To err is human; Erring hopes to help you remember.

## Why?

Humans err. We forget commitments, lose context, leave details unsaid, and remember conversations differently. AI assistants often make this worse by confidently filling in the gaps instead of asking for clarification.

Erring is built on a simple principle: when something matters, remember it; when something is missing, ask.

## Features

- 🧠 Persistent memory across conversations
- ✅ Commitment detection and tracking
- ❓ Clarification when key information is missing
- 🔍 Semantic retrieval of past facts and commitments
- 📜 Transparent memory updates

## Architecture

Erring's memory and conversation loop are independent of its interfaces:

```text
CLI ---------\
              > Erring core -> SQLite
Telegram ----/             -> LLM provider
```

The CLI and Telegram adapter use the same user-wide structured memory.

## Quick Start

Install dependencies and create local configuration:

```bash
uv sync
cp .env.example .env
```

Set `DEEPSEEK_API_KEY` in `.env`, then start the terminal interface:

```bash
uv run erring chat
```

## Telegram Bot

Telegram is an optional local interface. It uses long polling, so Alibaba Cloud,
webhooks, and public hosting are not required.

1. Create a bot with [BotFather](https://t.me/BotFather).
2. Add its token to `.env`:

   ```bash
   TELEGRAM_BOT_TOKEN=replace_with_bot_token
   ```

3. Start the adapter:

   ```bash
   uv run erring telegram
   ```

4. Send `/start` to the bot. In setup mode, it replies with the
   `TELEGRAM_ALLOWED_USER_ID` value to add to `.env`.
5. Restart `uv run erring telegram`.

Only that Telegram user is accepted. The first authorized Telegram identity is
linked to the existing local Erring user, so CLI and Telegram share commitments,
projects, observations, and accumulated experience. Telegram group chats are
ignored in this version.

## Example

**You:** "Remind me to finish the OCR pipeline."

**Erring:** "Sure. When would you like to finish it?"

Later:

**You:** "What did I promise to work on this week?"

**Erring:** "You committed to finishing the OCR pipeline by Friday."

## Vision

Erring is an experiment in building AI that compensates for human fallibility rather than pretending uncertainty doesn't exist.
