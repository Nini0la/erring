# Erring Implementation Plan

## Current Focus

Build the core Erring memory loop.

Do not optimize for the recording demo yet. Demo scenarios can be useful later, but the implementation should first make the underlying memory system reliable, inspectable, and testable.

Erring is a persistent memory agent focused on commitments, clarification, and follow-through. It is not a general assistant, search engine, or encyclopedia.

## v0 Principles

- Reflection is event-driven.
- Reflection decides whether the latest user message requires a structured memory operation.
- Reflection handles commitments, projects, observations, reads, clarifications, and no-op decisions.
- Reflection does not update accumulated experience.
- Summary is a separate call whose only job is maintaining Accumulated Experience.
- One reflection result equals one decision.
- Reflection can ask a clarification question or choose a CRUD/read action, but not both.
- The LLM never writes SQL.
- CRUD tools are fixed application functions.
- Every user has an `Uncategorized` project.
- Every commitment belongs to a project, defaulting to `Uncategorized`.
- Archive instead of delete for v0.
- Memory operations should be transparent through `operation_log`.

## Proposed Stack

- Python 3.11+
- uv
- sqlite3
- pydantic
- openai
- pytest
- ruff

Avoid LangChain/LlamaIndex for v0. Erring has a specific control flow, and explicit code will be easier to inspect and test.

Optional later:

- typer for a CLI
- rich for readable terminal output
- python-dotenv for local environment loading

## Target File Layout

```text
erring/
  __init__.py
  config.py
  db.py
  schema.sql
  models.py
  prompts.py
  crud.py
  reflection.py
  conversation.py
  summary.py
  followthrough.py
  context.py
  app.py

prompts/
  general_system.md
  reflection.md
  conversation.md
  summary.md
  followthrough.md
  cold_start.md

tests/
  test_schema.py
  test_crud.py
  test_reflection_models.py
  test_core_loop.py
  test_summary_trigger.py
```

## Runtime Loop

```text
receive user message
  -> save user message to conversation history
  -> run reflection call
  -> validate reflection JSON
  -> if ASK_CLARIFICATION:
       save operation log
       return clarification response
  -> if CRUD/read action:
       execute fixed application tool
       save operation log
  -> build context window
  -> run conversation call
  -> save assistant message
  -> check whether summary should be triggered
  -> return assistant response
```

For read actions, the read result should be included in the context passed to the conversation call.

For clarification actions, v0 can return the clarification directly without running a separate conversation call.

## Prompt Files

The current prompt notes should become runtime prompt files:

```text
prompts/general_system.md
prompts/reflection.md
prompts/conversation.md
prompts/summary.md
prompts/followthrough.md
prompts/cold_start.md
```

### General System Prompt

Stable identity and behavioral constraints:

- You are Erring.
- Help the user remember, clarify, and follow through on commitments.
- Be brief and conversational.
- Do not invent facts.
- Ask for clarification when commitment details are ambiguous or missing.

### Reflection Prompt

Strict structured-output prompt.

Reflection answers:

> Did something happen in the latest user message that requires changing or reading structured memory?

Reflection scope:

- commitments
- projects
- observations
- reads over those stores
- clarification
- no action

Reflection must not update accumulated experience.

### Conversation Prompt

Produces the user-facing response after memory operations have been handled.

It receives:

- general system prompt
- conversation task prompt
- recent conversation
- relevant commitments
- relevant observations
- accumulated experience
- operation/read result, if any
- current user message

### Summary Prompt

Maintains Accumulated Experience only.

Summary answers:

> Given recent conversation and memory changes, what should Erring's compressed understanding now be?

It should not create commitments, projects, or observations.

### Follow-through Prompt

Later loop for accountability checks.

It should look at:

- due soon commitments
- overdue commitments
- untimed commitments
- recently missed commitments
- commitments needing clarification

Then it generates focused follow-through questions.

## Database Schema

Use SQLite for v0.

### users

```text
id
onboarding_status
created_at
updated_at
```

`onboarding_status` can start as:

```text
not_started | in_progress | complete
```

### conversation_messages

```text
id
user_id
session_id
role
content
created_at
summarized_at
```

`summarized_at` tracks whether a message has been included in Accumulated Experience.

### projects

```text
id
user_id
name
status
created_at
updated_at
```

Every user gets an `Uncategorized` project on creation.

Suggested statuses:

```text
active | archived
```

### commitments

```text
id
user_id
project_id
title
status
source_type
time_status
due_at
created_at
updated_at
completed_at
notes
metadata_json
```

Suggested statuses:

```text
active | completed | cancelled | archived
```

Suggested source types:

```text
explicit | inferred
```

Suggested time statuses:

```text
timed | untimed
```

### observations

```text
id
user_id
project_id
content
created_at
updated_at
```

Observations are loose memory:

- facts
- preferences
- project nuance
- important user statements
- recurring patterns

They are not commitments.

### experience_summaries

```text
id
user_id
content
created_at
updated_at
```

For v0, one current summary row per user is enough.

### operation_log

```text
id
user_id
session_id
message_id
reflection_json
operation_executed
result_json
created_at
```

This is for transparency and debugging. It should show what reflection decided, what application operation ran, and what happened.

## Reflection Contract

Reflection returns exactly one structured decision.

Suggested actions:

```text
NO_ACTION
ASK_CLARIFICATION
CREATE_COMMITMENT
UPDATE_COMMITMENT
READ_COMMITMENTS
ARCHIVE_COMMITMENT
CREATE_PROJECT
UPDATE_PROJECT
READ_PROJECTS
CREATE_OBSERVATION
UPDATE_OBSERVATION
READ_OBSERVATIONS
```

Example clarification:

```json
{
  "action": "ASK_CLARIFICATION",
  "question": "When would you like to finish it?",
  "reason": "The user made an explicit commitment without a timeline."
}
```

Example operation:

```json
{
  "action": "CREATE_COMMITMENT",
  "arguments": {
    "title": "finish the OCR pipeline",
    "project_id": null,
    "source_type": "explicit",
    "time_status": "untimed",
    "due_at": null,
    "notes": null
  }
}
```

The application layer should resolve `project_id: null` to the user's `Uncategorized` project where needed.

## CRUD Tools

Implement fixed application functions.

User and setup:

```python
create_user()
get_user()
get_or_create_uncategorized_project()
```

Conversation:

```python
save_message()
get_recent_messages()
mark_messages_summarized()
count_unsummarized_messages()
```

Commitments:

```python
create_commitment()
read_commitments()
update_commitment()
archive_commitment()
```

Projects:

```python
create_project()
update_project()
read_projects()
```

Observations:

```python
create_observation()
update_observation()
read_observations()
```

Experience:

```python
get_accumulated_experience()
update_accumulated_experience()
```

Logging:

```python
write_operation_log()
```

## LLM Call Functions

```python
run_reflection_call()
run_conversation_call()
run_summary_call()
run_followthrough_call()
```

For v0, wire `run_reflection_call()` and `run_conversation_call()` into the main message loop first.

`run_summary_call()` can be implemented once storage and message tracking are ready.

`run_followthrough_call()` can come after the core loop is stable.

## Context Builder

Implement `build_context_window()`.

For normal conversation:

```text
general system prompt
conversation task prompt
recent conversation
relevant commitments
relevant observations
accumulated experience
operation/read result, if any
current user message
```

For cold start:

```text
general system prompt
cold start task prompt
recent conversation
current user message
```

## Summary Trigger

Summary is separate from reflection.

Run summary when either condition is true:

```text
20 unsummarized messages
OR
30 minutes inactivity
```

The summary call updates only Accumulated Experience.

After a successful summary update, mark included messages as summarized.

## Build Order

1. Create runtime prompt files.
2. Add SQLite schema.
3. Add database initialization.
4. Add Pydantic models for reflection and CRUD inputs.
5. Implement CRUD tools.
6. Implement operation logging.
7. Implement prompt loading.
8. Implement reflection call and validation.
9. Implement context builder.
10. Implement conversation call.
11. Wire the main message loop.
12. Add summary trigger checks.
13. Implement summary call.
14. Add follow-through retrieval.
15. Add tests around schema, CRUD, reflection validation, and the core loop.

## Initial Test Coverage

Start with non-LLM tests:

- schema initializes
- creating a user creates an `Uncategorized` project
- commitment CRUD works
- project CRUD works
- observation CRUD works
- operation log records reflection and result
- reflection JSON validates
- summary trigger detects 20 unsummarized messages

Then add mocked LLM loop tests:

- commitment without enough detail produces `ASK_CLARIFICATION`
- refused timeline can produce an untimed commitment on the next turn
- read request executes `READ_COMMITMENTS`
- ambiguous update produces `ASK_CLARIFICATION`
- summary trigger calls the summary path without involving reflection

## Non-goals for v0

- No production auth.
- No hosted service.
- No UI unless needed for manual testing.
- No vector database.
- No complex semantic retrieval.
- No autonomous background scheduler beyond simple summary-trigger logic.
- No demo-specific hardcoding.

