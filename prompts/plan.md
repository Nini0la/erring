Yes. Current coding-agent build plan, updated to where we are now:

Erring Build Plan

User ↔ Conversation LLM
        |
        v
Reflection LLM
        |
        v
Operation Compiler
        |
        v
Fixed CRUD Tools
        |
        v
Memory Stores
        |
        v
Follow-through Response

1. Core Memory Stores

We now have 5 storage layers:

1. Conversation History
2. Commitment Store
3. Context Window
4. Accumulated Experience
5. Notes (called Observations)

A. Conversation History

Raw chat log. Source of truth.

Stores:

message_id
session_id
role
content
created_at

B. Commitment Store

Relational database.

Stores:

id
user_id
project_id
title
status
source_type: explicit | inferred
time_status: timed | untimed
due_at
created_at
updated_at
completed_at
notes
metadata_json

C. Context Window

Not stored permanently as its own DB table yet.

Built before each response from:

Context Window =
General System Prompt
+ Task Prompt
+ Recent Conversation
+ Relevant Commitments
+ Accumulated Experience
+ Relevant Observations
+ Current User Message

D. Accumulated Experience

Recursive summary of what has happened.

Could be:

flat file
or
database row per user

Used to compress history into working context.

E.  Observations

Loose but separate notes. Observations are loose facts/patterns that are not commitments.

Stores:

facts
preferences
project nuance
important user statements
observations

Not the same as commitments.

⸻

2. Main Agent Flow

User message
   ↓
Save to conversation history
   ↓
Reflection LLM
   ↓
Operation decision
   ↓
CRUD tool execution if needed
   ↓
Build context window
   ↓
Conversation LLM response
   ↓
Save assistant response

⸻

3. Reflection LLM

This is the “inner thought.”

It decides:

NO_ACTION
ASK_CLARIFICATION
CREATE_COMMITMENT
UPDATE_COMMITMENT
READ_COMMITMENTS
ARCHIVE_COMMITMENT
CREATE_PROJECT
LINK_TO_PROJECT
CREATE_NOTE
UPDATE_EXPERIENCE_SUMMARY

It does not write SQL.

It outputs structured JSON.

⸻

4. Commitment Decision Tree

Codify this:

Commitment detected?
  |
  no → no commitment write
  |
  yes
    |
    explicit or inferred?
    |
    inferred → ask clarification
    |
    explicit
       |
       has timeline?
          |
          yes → store timed commitment
          |
          no → ask for timeline
                 |
                 user gives time → store timed commitment
                 user refuses/unclear → store untimed commitment

⸻

5. Projects

Add first-class projects.

Tables:

projects
commitments

Always create:

Uncategorized

Onboarding asks:

What goals or projects should I help you follow through on?

⸻

6. CRUD Tools

Prepackaged only.

create_commitment()
read_commitments()
update_commitment()
archive_commitment()
create_project()
link_commitment_to_project()
create_note()
update_accumulated_experience()

No raw SQL from the LLM.

⸻

7. Follow-through

Follow-through is a separate loop.

It checks:

due soon
overdue
untimed
recently missed
needs clarification

Then generates questions like:

Did this happen?
Should we reschedule it?
Do you want to give this a timeline?
Is this still active?

⸻

8. Forgetting

For now: archive, don’t delete.

Statuses:

active
completed
cancelled
archived

Later we can add smarter forgetting.

⸻

Coding Agent Instruction

Build the smallest version where this works:

conversation history
+ reflection call
+ fixed CRUD tools
+ relational commitment store
+ timed/untimed commitments
+ projects
+ follow-through retrieval

No extra features until that loop is working.