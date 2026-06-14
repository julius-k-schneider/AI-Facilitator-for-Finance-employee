import json
import logging
import os
import uuid
from datetime import timedelta
from urllib import error, request

from django.db import transaction
from django.utils import timezone

from accounts.models import Mission
from accounts.services.mission_validation import MissionValidationError, validate_generated_payload


logger = logging.getLogger(__name__)


class AiMissionGenerationError(RuntimeError):
    pass


SYSTEM_PROMPT = """You create short daily learning missions for finance employees.
Return valid JSON only, without markdown or commentary. Every mission must be bilingual in German and English,
take 3-8 minutes and train practical AI competence in a finance context. Single-answer types must have exactly one
unambiguous correct answer. Multiple-choice missions may have one, several, or all answer options as correct.
Never use or invent personal, confidential, Lufthansa-internal, SAP, customer, or employee data. Do not present legal
or compliance advice as guaranteed truth. Only use these automatically scored types: multiple_choice,
compliance_decision, prompt_selection. Include concise bilingual feedback explaining the correct answer.
Descriptions must be short, natural summaries of the specific mission topic. Do not mention the expected duration,
do not explain that the learner must choose or determine an answer, and do not reuse a generic description template."""


def next_calendar_week(reference_date=None):
    today = reference_date or timezone.localdate()
    start = today + timedelta(days=7 - today.weekday())
    return start, start + timedelta(days=6)


def build_user_prompt(target_slots):
    schedule = ', '.join(f'{day.isoformat()}: {count}' for day, count in sorted(target_slots.items()))
    return f"""Create exactly the requested missions for this schedule: {schedule}.
Use 10-50 points per mission and 2-6 answer options. Return this exact structure:
{{"missions":[{{"date":"YYYY-MM-DD","type":"multiple_choice|compliance_decision|prompt_selection",
"title_de":"...","title_en":"...","description_de":"...","description_en":"...","points":30,
"content":{{"question_de":"...","question_en":"...","options_de":["..."],"options_en":["..."],
"correct_option_indices":[0],"feedback_de":"...","feedback_en":"..."}}}}]}}
For multiple_choice, correct_option_indices must contain one to all option indices. For compliance_decision and
prompt_selection it must contain exactly one index. Include a meaningful mix of multiple-choice missions with one
correct answer and with several correct answers.
Use only the dates and counts in the requested schedule."""


def extract_json(content):
    if not isinstance(content, str) or not content.strip():
        raise AiMissionGenerationError('AI returned an empty response')
    text = content.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        text = '\n'.join(lines[1:-1]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error_value:
        raise AiMissionGenerationError('AI returned invalid JSON') from error_value


def call_ai(target_slots):
    api_key = os.environ.get('KICONNECT_API_KEY', '').strip()
    model = os.environ.get('KICONNECT_MODEL', '').strip()
    base_url = os.environ.get('KICONNECT_BASE_URL', 'https://chat.kiconnect.nrw/api/v1').rstrip('/')
    path = os.environ.get('KICONNECT_CHAT_COMPLETIONS_PATH', '/chat/completions')
    if not api_key or not model:
        raise AiMissionGenerationError('AI generation is not configured')

    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': build_user_prompt(target_slots)},
        ],
        'temperature': 0.6,
    }).encode('utf-8')
    api_request = request.Request(
        f'{base_url}{path}',
        data=body,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with request.urlopen(api_request, timeout=90) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        return extract_json(response_data['choices'][0]['message']['content'])
    except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exception:
        logger.exception('KICOnnect mission generation failed')
        raise AiMissionGenerationError('AI service is currently unavailable') from exception


def generate_candidates(target_slots):
    if not target_slots:
        return []
    try:
        return validate_generated_payload(call_ai(target_slots), target_slots)
    except MissionValidationError as exception:
        logger.warning('Rejected invalid AI mission response: %s', exception)
        raise AiMissionGenerationError(f'AI response failed validation: {exception}') from exception


def apply_candidate(mission, candidate):
    mission.mission_type = candidate['mission_type']
    mission.scheduled_date = candidate['scheduled_date']
    mission.title_de = candidate['title_de']
    mission.title_en = candidate['title_en']
    mission.description_de = candidate['description_de']
    mission.description_en = candidate['description_en']
    mission.content = candidate['content']
    mission.max_points = candidate['max_points']


def generate_next_week(created_by, force=False, reference_date=None):
    week_start, week_end = next_calendar_week(reference_date)
    with transaction.atomic():
        missions = Mission.objects.select_for_update().filter(scheduled_date__range=(week_start, week_end))
        if force:
            missions.filter(status=Mission.STATUS_REVIEW, generated_by_ai=True).delete()

        target_slots = {}
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            occupied = Mission.objects.filter(
                scheduled_date=day,
                status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
            ).count()
            if occupied < 2:
                target_slots[day] = 2 - occupied

        candidates = generate_candidates(target_slots)
        batch_id = uuid.uuid4()
        created = []
        for candidate in candidates:
            mission = Mission(
                created_by=created_by,
                status=Mission.STATUS_REVIEW,
                generated_by_ai=True,
                generation_batch_id=batch_id,
            )
            apply_candidate(mission, candidate)
            mission.save()
            created.append(mission)
    return created, week_start, week_end


def regenerate_review_mission(mission, requested_by):
    if mission.status != Mission.STATUS_REVIEW or not mission.generated_by_ai:
        raise AiMissionGenerationError('Only AI review missions can be regenerated')
    candidate = generate_candidates({mission.scheduled_date: 1})[0]
    with transaction.atomic():
        locked = Mission.objects.select_for_update().get(id=mission.id)
        apply_candidate(locked, candidate)
        locked.created_by = requested_by
        locked.generation_batch_id = uuid.uuid4()
        locked.reviewed_by = None
        locked.reviewed_at = None
        locked.save()
    return locked
