import json
import os
from urllib import error, request

from accounts.services.ai_mission_generator import AiMissionGenerationError, extract_json


CHAT_CHALLENGE_TYPE = 'ai_chat_challenge'
FINAL_TYPES = {'number', 'single_choice', 'compliance_decision', 'evidence_boolean'}

SYSTEM_PROMPT = """Create one beginner-friendly bilingual AI Chat Challenge for a finance employee.
The learner gets a small finance case, may ask an AI assistant up to three questions, and then submits final answers.
The chat must support reasoning but must not directly provide the final answer values or option labels.
Return compact valid JSON only. Never use real personal, customer, Lufthansa-internal, or confidential data."""

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


def _configuration():
    api_key = os.environ.get('KICONNECT_API_KEY', '').strip()
    model = os.environ.get('KICONNECT_MODEL', '').strip()
    base_url = os.environ.get('KICONNECT_BASE_URL', 'https://chat.kiconnect.nrw/api/v1').rstrip('/')
    path = os.environ.get('KICONNECT_CHAT_COMPLETIONS_PATH', '/chat/completions')
    if not api_key or not model:
        raise AiMissionGenerationError('AI generation is not configured')
    return api_key, model, f'{base_url}{path}'


def _completion(messages, json_mode=False, temperature=0.4, max_tokens=3000):
    api_key, model, url = _configuration()
    payload = {'model': model, 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens}
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    api_request = request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with request.urlopen(api_request, timeout=90) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        return response_data['choices'][0]['message']['content']
    except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exception:
        raise AiMissionGenerationError('AI service is currently unavailable') from exception


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise AiMissionGenerationError(f'AI chat challenge field {field} is invalid')
    return value.strip()


def validate_challenge(payload):
    if not isinstance(payload, dict):
        raise AiMissionGenerationError('AI chat challenge is invalid')
    questions = payload.get('final_questions')
    if not isinstance(questions, list) or len(questions) != 2:
        raise AiMissionGenerationError('AI chat challenge requires exactly two final questions')
    normalized_questions = []
    for index, question in enumerate(questions):
        question_type = question.get('type')
        if question_type not in FINAL_TYPES:
            raise AiMissionGenerationError('AI chat challenge contains an unsupported final question')
        normalized = {
            'id': str(question.get('id') or f'q{index + 1}'),
            'type': question_type,
            'prompt_de': _text(question.get('prompt_de'), 'prompt_de'),
            'prompt_en': _text(question.get('prompt_en'), 'prompt_en'),
            'feedback_de': _text(question.get('feedback_de'), 'feedback_de'),
            'feedback_en': _text(question.get('feedback_en'), 'feedback_en'),
            'solution': question.get('solution'),
        }
        if question_type == 'number':
            try:
                normalized['solution'] = float(question.get('solution'))
                normalized['tolerance'] = max(0, float(question.get('tolerance', 0)))
            except (TypeError, ValueError) as exception:
                raise AiMissionGenerationError('AI chat challenge has an invalid numeric solution') from exception
        else:
            options_de = question.get('options_de')
            options_en = question.get('options_en')
            if not isinstance(options_de, list) or not isinstance(options_en, list) or len(options_de) != len(options_en) or len(options_de) < 2:
                raise AiMissionGenerationError('AI chat challenge final options are invalid')
            normalized['options_de'] = [_text(value, 'option_de') for value in options_de]
            normalized['options_en'] = [_text(value, 'option_en') for value in options_en]
            if question_type == 'single_choice':
                try:
                    normalized['solution'] = int(question.get('solution'))
                except (TypeError, ValueError) as exception:
                    raise AiMissionGenerationError('AI chat challenge choice solution is invalid') from exception
                if normalized['solution'] < 0 or normalized['solution'] >= len(options_de):
                    raise AiMissionGenerationError('AI chat challenge choice solution is outside the options')
            elif question_type == 'evidence_boolean':
                if not isinstance(question.get('solution'), bool) or len(options_de) != 2:
                    raise AiMissionGenerationError('AI chat challenge evidence solution is invalid')
                normalized['solution'] = question['solution']
                normalized['option_values'] = [True, False]
            elif len(options_de) != 3:
                raise AiMissionGenerationError('AI chat challenge compliance options are invalid')
            elif normalized['solution'] not in {'green', 'yellow', 'red'}:
                raise AiMissionGenerationError('AI chat challenge compliance solution is invalid')
            if question_type == 'single_choice':
                normalized['option_values'] = list(range(len(options_de)))
            elif question_type == 'compliance_decision':
                normalized['option_values'] = ['green', 'yellow', 'red']
        normalized_questions.append(normalized)
    return {
        'type': CHAT_CHALLENGE_TYPE,
        'title_de': _text(payload.get('title_de'), 'title_de'),
        'title_en': _text(payload.get('title_en'), 'title_en'),
        'description_de': _text(payload.get('description_de'), 'description_de'),
        'description_en': _text(payload.get('description_en'), 'description_en'),
        'task_de': _text(payload.get('task_de'), 'task_de'),
        'task_en': _text(payload.get('task_en'), 'task_en'),
        'case_data_de': [_text(value, 'case_data_de') for value in payload.get('case_data_de', [])],
        'case_data_en': [_text(value, 'case_data_en') for value in payload.get('case_data_en', [])],
        'chat_system_prompt_de': _text(payload.get('chat_system_prompt_de'), 'chat_system_prompt_de'),
        'chat_system_prompt_en': _text(payload.get('chat_system_prompt_en'), 'chat_system_prompt_en'),
        'final_questions': normalized_questions,
    }


def generate_chat_challenge():
    return validate_challenge(extract_json(_completion([
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': USER_PROMPT},
    ], json_mode=True)))


def chat_reply(challenge, history, message, language):
    language = 'en' if language == 'en' else 'de'
    task = challenge[f'task_{language}']
    case_data = challenge[f'case_data_{language}']
    system = challenge[f'chat_system_prompt_{language}']
    messages = [{
        'role': 'system',
        'content': f'{system}\nTask: {task}\nCase data: {json.dumps(case_data, ensure_ascii=False)}\nGive hints and explain reasoning, but never state final answer values or identify the correct final option.',
    }]
    messages.extend(history)
    messages.append({'role': 'user', 'content': message})
    return _completion(messages, temperature=0.5, max_tokens=700).strip()


def evaluate_final_answers(challenge, answers, language):
    language = 'en' if language == 'en' else 'de'
    results = []
    for question in challenge['final_questions']:
        answer = answers.get(question['id'])
        if question['type'] == 'number':
            try:
                correct = abs(float(answer) - question['solution']) <= question['tolerance']
            except (TypeError, ValueError):
                correct = False
        elif question['type'] == 'single_choice':
            try:
                correct = int(answer) == question['solution']
            except (TypeError, ValueError):
                correct = False
        else:
            correct = answer == question['solution']
        results.append({
            'id': question['id'],
            'correct': correct,
            'feedback': question[f'feedback_{language}'],
        })
    return {'correct': all(item['correct'] for item in results), 'items': results}
