this is mostly information about the task prompts, which are used to guide the model's behavior in different contexts. Each task prompt is designed to elicit specific types of responses from the model, depending on the nature of the interaction.

run_reflection_call()
  → uses Reflection Task Prompt

run_conversation_call()
  → uses Conversation Task Prompt

run_followthrough_call()
  → uses Follow-through Task Prompt

run_summary_call()
  → uses Summary Task Prompt

  So task prompts are not “remembered” by the AI.
They are inserted by code before that specific call.

example:

[General System Prompt]
You are Erring...

[Task Prompt]
You are the Commitment Reflection Compiler...

[Context]
Recent conversation...
Relevant commitments...
Accumulated experience...
Relevant observations...

[Input]
User just said: "I should call Tolu."

Do note, that the cold_start prompt is a task prompt, but it is only used once per user, at the beginning of the conversation. It is not used for every response.

Actual call shape

For a new user: context window = [general_system.md] + [cold_start.md] + [recent conversation] + [user message]

For normal use: context window = [general_system.md] + [conversation.md] + [recent conversation] + [relevant commitments] + [accumulated experience] + [relevant observations] + [user message]


Conceptually:
Conversation Task
        │
        ├── Cold Start
        └── Normal Conversation

could be implemented as a single task prompt with conditional logic, but it is easier to reason about as two separate task prompts.
e.g.: 
if user.onboarding_complete:
    prompt = conversation.md
else:
    prompt = cold_start.md