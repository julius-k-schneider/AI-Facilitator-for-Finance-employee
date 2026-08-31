# Prompt Catalog

All active LLM prompts are grouped here by request type. Mission generation runs
entirely in n8n, so editing these modules changes what the n8n generator,
reviewer and repair steps are told — and, for the agent and chat prompts, what
Django's own interactive replies use.

1. `mission_generation.py`
   - Quiz-style weekly missions
   - Quiz mission regeneration
   - Choice-based training missions
2. `task_challenges.py`
   - `build_task_challenge_prompts()` builds one generator prompt per task type:
     bulk categorization, plan-versus-actual deviation, duplicate-payment
     detection, invoice extraction, travel-policy violation check, receivables
     aging, VAT-rate audit, and bank reconciliation
   - `DIFFICULTY_INSTRUCTIONS` and `TASK_DIFFICULTY_CONTRACTS` define the binding
     easy/medium/hard data and result profiles
3. `chat_challenges.py`
   - Bounded chat-challenge generation
   - Mini-chat coaching guardrails
4. `personal_agent.py`
   - German personal assistant
   - English personal assistant

These modules hold the prompt text only. The prompts are assembled into the n8n
generation contract in `accounts/services/n8n_mission_generation.py`, which
imports them from here directly.

Keep JSON output contracts synchronized with the deterministic validators in
`accounts/services/mission_validation.py`, `ai_task_challenge.py`, and
`ai_chat_challenge.py` when changing schemas or required fields.
