from accounts.prompts.personal_agent import SYSTEM_PROMPT_DE, SYSTEM_PROMPT_EN
from accounts.services.ai_chat_challenge import _completion
from accounts.services.generation_planning import AiMissionGenerationError


def _normalize_history(messages):
    if not isinstance(messages, list):
        return []
    normalized = []
    for item in messages[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        content = str(item.get('content', '')).strip()
        if role in {'user', 'assistant'} and content:
            normalized.append({'role': role, 'content': content[:3000]})
    return normalized


def personal_agent_reply(messages, language='de'):
    normalized = _normalize_history(messages)
    if not normalized or normalized[-1]['role'] != 'user':
        raise AiMissionGenerationError('message required')
    system_prompt = SYSTEM_PROMPT_EN if language == 'en' else SYSTEM_PROMPT_DE
    return _completion([
        {'role': 'system', 'content': system_prompt},
        *normalized,
    ], temperature=0.45, max_tokens=1200).strip()
