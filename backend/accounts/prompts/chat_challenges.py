"""Prompts for generating and coaching the bounded AI chat challenge."""

import json


# Generates the complete challenge, including the case, two final questions, and
# the challenge-specific coaching instructions used later in the mini chat.
SYSTEM_PROMPT = """Create one beginner-friendly bilingual AI Chat Challenge for a finance employee.
The learner gets a small finance case, may ask an AI assistant up to three questions, and then submits final answers.
The chat must support reasoning but must not directly provide the final answer values or option labels.
Return compact valid JSON only. Never use real personal, customer, Lufthansa-internal, or confidential data."""


# Defines the machine-readable contract expected by validate_challenge().
USER_PROMPT = """Return exactly this JSON structure:
{
  "title_de":"...", "title_en":"...",
  "description_de":"...", "description_en":"...",
  "task_de":"...", "task_en":"...",
  "case_data_de":["..."], "case_data_en":["..."],
  "chat_system_prompt_de":"...", "chat_system_prompt_en":"...",
  "final_questions":[
    {"id":"q1","type":"number","prompt_de":"...","prompt_en":"...","solution":12.5,"tolerance":0.1,"feedback_de":"...","feedback_en":"..."},
    {"id":"q2","type":"single_choice","prompt_de":"...","prompt_en":"...","options_de":["..."],"options_en":["..."],"solution":1,"feedback_de":"...","feedback_en":"..."}
  ]
}
Create exactly two final questions. Allowed types are number, single_choice, compliance_decision, evidence_boolean.
For compliance_decision use options green/yellow/red and store the solution as one of those strings.
For evidence_boolean use options true/false and store the solution as a boolean.
For single_choice store the zero-based correct option index. Numeric questions require a non-negative tolerance.
The task should be solvable from the supplied case data with thoughtful use of the mini-chat."""


# Combines the generated challenge-specific instruction with immutable guardrails
# for each learner message in the three-message coaching chat.
def build_coaching_system_prompt(challenge_system_prompt, task, case_data):
    return (
        f'{challenge_system_prompt}\n'
        f'Task: {task}\n'
        f'Case data: {json.dumps(case_data, ensure_ascii=False)}\n'
        'Give hints and explain reasoning, but never state final answer values or identify the correct final option. '
        'Answer in plain text only: no Markdown, no bold markers, no tables. '
        'Use at most one short paragraph plus up to three short bullet lines when helpful.'
    )
