# Prompt Catalog

All active LLM prompts are grouped here by request type. Editing these modules
changes the prompts used by both the Django compatibility paths and the n8n
generation contract.

1. `mission_generation.py`
   - Quiz-style weekly missions
   - Quiz mission regeneration
   - Choice-based training missions
2. `task_challenges.py`
   - Bulk categorization
   - Plan-versus-actual deviation
   - Duplicate-payment detection
   - Invoice extraction
   - Easy, medium, and hard task instructions
3. `chat_challenges.py`
   - Bounded chat-challenge generation
   - Mini-chat coaching guardrails
4. `personal_agent.py`
   - German personal assistant
   - English personal assistant

Keep JSON output contracts synchronized with the deterministic validators in
`accounts/services/mission_validation.py`, `ai_task_challenge.py`, and
`ai_chat_challenge.py` when changing schemas or required fields.
