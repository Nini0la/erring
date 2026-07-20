# Erring Work Status

This file tracks important work to address soon, but not in the current task.

## Summary Maintenance Is Not Wired Into the Core Loop

### Current issue

- `maybe_update_summary()` contains the actual summary workflow: check the
  trigger, call the summary model, update Accumulated Experience, and mark
  messages as summarized.
- `handle_user_message()` currently calls `should_run_summary()` and discards
  its Boolean result. It never calls `maybe_update_summary()`.
- As a result, automatic summary maintenance does not run. The current database
  has 31 unsummarized messages, zero summarized messages, and a blank
  Accumulated Experience record.

### Trigger considerations

- The 20-unsummarized-message trigger can be handled after saving the assistant
  response.
- The 30-minute inactivity trigger cannot be detected correctly by checking
  after saving a new user message, because that new message resets the latest
  activity time.

### Recommended v0 work

1. Call `maybe_update_summary()` after the assistant response is saved so the
   20-message trigger executes.
2. Check for an inactivity-triggered summary before saving the next incoming
   user message.
3. Add a core-loop integration test proving that a due summary is written and
   its source messages are marked as summarized.
4. Keep summary failures from invalidating or losing an otherwise successful
   user-facing response.

### Later improvement

- Move inactivity checks and summary generation to a background scheduler so
  summary calls do not delay user responses.
- Consider renaming `maybe_update_summary()` to `update_summary_if_due()` for
  clearer intent.

## User-Facing Trust and Capability Guardrails

### Current issues

- During onboarding, the user-facing call receives `general_system.md` plus
  `cold_start.md`; it does not receive `conversation.md`. Normal conversation
  guardrails therefore do not apply while onboarding remains incomplete.
- The current user remains in `not_started`, so every response continues to use
  the cold-start path.
- The model is not given authoritative runtime identity or capability
  information. It has already invented a model name, streak tracking, and a
  `Routines` store.
- Conversation history can contain possible commitments that were never
  persisted. The model has described some of these mentions as active
  commitments.
- `cold_start.md` refers to a `Routines` store that does not exist in the v0
  schema.

### Recommended implementation order

1. Compose every user-facing system prompt from `general_system.md` and
   `conversation.md`. Add `cold_start.md` as an onboarding overlay instead of
   using it as a replacement for conversation behavior.
2. Add global boundaries to `general_system.md`:
   - Erring is not a general assistant or search engine.
   - Erring has no web access and must not imply that it searched or verified
     external information.
   - Erring must not guess current facts, model identity, tools,
     implementation details, or capabilities.
   - Unknown information receives a brief, honest limitation.
   - Erring must not claim that an operation occurred unless a supplied
     operation result confirms it.
3. Correct `cold_start.md` to use only the v0 memory entities: projects,
   commitments, and observations. Remove unsupported `Routines` storage,
   recurrence, and streak claims.
4. Inject an authoritative runtime-facts block from application code. Include
   the current date, timezone, web availability, supported memory types, and
   explicit unsupported capabilities such as notifications, recurring
   schedules, and streak tracking. Omit the underlying model name if the
   product policy is not to disclose it.
5. Distinguish conversation mentions from structured memory. Use language such
   as "you previously mentioned" for conversation-only context. Use "active",
   "stored", "created", "updated", or "tracked" only when structured memory or
   an operation result supports the claim.
6. Implement explicit onboarding transitions:
   `not_started -> in_progress -> complete`. Allow the user to skip onboarding,
   and load active structured memory normally after completion.
7. Add behavioral tests covering:
   - model-identity questions without invention
   - current-information requests without false browsing claims
   - architecture questions without speculation
   - mentioned but uncreated commitments
   - acknowledgment of successful operations only
   - daily commitments without unsupported recurrence or streak promises
   - cold-start responses receiving normal conversation guardrails

### Priority

Proceed with the thin local Telegram adapter now that the core loop has
completed a real persisted operation. Continue this trust and capability work
immediately alongside testing through CLI and Telegram, and complete it before
cloud deployment or broader user access.

## Interface and Deployment Strategy

### Current status

- The local Telegram adapter is implemented with
  `uv run erring telegram`.
- It uses long polling, private text-message filters, owner allowlisting,
  persisted Telegram-to-Erring identity mapping, the existing core loop, and
  shared structured memory with the CLI.
- Automated adapter, identity, response-splitting, CLI registration, schema,
  and core tests pass.
- Live Telegram validation remains pending a BotFather token and the owner's
  Telegram user ID.

### Product boundary

- Erring is the product. CLI, Telegram, and any future REST or web interface are
  adapters over the same core memory and accountability engine.
- Keep the CLI as the canonical local testing and debugging interface:
  `uv run erring chat`.
- Add Telegram as an optional interface:
  `uv run erring telegram`.
- Telegram-specific code must not contain reflection, prompt, commitment, or
  memory policy. It should translate messages to and from the existing core
  loop.

### Recommended local Telegram v0

1. Use long polling so Telegram can run locally without cloud deployment or
   webhook configuration.
2. Accept private chats only initially.
3. Keep the bot token in `.env`.
4. Add an explicit mapping from Telegram user IDs to internal Erring user IDs.
   Map the owner's Telegram identity to the existing Erring user so CLI and
   Telegram share commitments, projects, observations, and accumulated
   experience.
5. Use distinct channel session IDs while keeping structured memory user-wide.
6. Process messages sequentially per chat to avoid conflicting memory
   operations.
7. Keep Telegram responses as plain text initially.
8. Add only minimal transport commands such as `/start` and `/help`; keep
   product behavior in the core.
9. Log Telegram transport errors separately from reflection, conversation, and
   CRUD failures.

### Alibaba Cloud

- Alibaba Cloud is not currently configured.
- It is not required for local Telegram development: `uv run erring telegram`
  can run on a laptop while the process remains open.
- Defer deployment until the local Telegram adapter and chat behavior are
  reliable.
- Deploy the same Telegram adapter rather than creating cloud-specific product
  logic.
- Before deployment, decide how to provide durable database storage. Local
  SQLite requires a persistent volume; a managed database may be preferable
  later.
- Cloud deployment must also cover process supervision, secrets, logging, and
  the choice between continued polling and webhooks.

### Intended progression

```text
1. Local CLI
2. Local CLI + local Telegram adapter
3. Improve prompts, onboarding, summaries, and memory behavior
4. Deploy the existing Telegram process and durable storage to Alibaba Cloud
```
