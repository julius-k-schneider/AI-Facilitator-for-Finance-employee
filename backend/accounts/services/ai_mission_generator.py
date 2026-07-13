import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from urllib import error, request

from django.db import transaction
from django.utils import timezone

from accounts.models import Mission
from accounts.services.mission_validation import MissionValidationError, validate_generated_payload


logger = logging.getLogger(__name__)
MAX_MISSIONS_PER_REQUEST = 2
DEFAULT_GENERATION_WORKERS = 2
DEFAULT_GENERATION_RETRIES = 2
DEFAULT_MAX_TOKENS = 9000


def is_business_day(day):
    return day.weekday() < 5


class AiMissionGenerationError(RuntimeError):
    pass


class AiMissionRateLimitError(AiMissionGenerationError):
    def __init__(self, retry_after=5):
        super().__init__('AI service rate limit reached')
        self.retry_after = retry_after


SYSTEM_PROMPT = """You create approachable daily AI learning missions for employees in a finance organization.

Target learner:
- An experienced accountant or controller who prepares monthly, quarterly, and year-end reports, handles correction
  bookings and accruals, and works with operational finance data.
- The learner may be older, has solid finance expertise, but little or no practical AI experience.
- The goal is confidence and immediate benefit in daily work, not technical AI specialization.

Difficulty and learning design:
- Keep every mission beginner-friendly to lower-intermediate. A finance professional without AI training must be able
  to solve it from the question and common workplace judgment alone.
- Create a small, actionable learning nugget that takes 3-8 minutes and feels useful rather than academic.
- Use plain business language. Explain unavoidable AI terms in the question or feedback.
- Test one clear learning objective at a time. Avoid trick questions, subtle semantic distinctions, and options that
  are only partially correct unless the mission is explicitly multiple choice.
- Do not require knowledge of machine-learning algorithms, model architecture, statistics, programming, prompt syntax
  jargon, legal paragraph numbers, SAP transaction codes, or specialized aviation processes.
- Prefer practical scenarios such as summarizing a finance report, comparing actuals and plan, drafting a clear prompt,
  checking an AI output, identifying confidential input, spotting a hallucination, or deciding when human review is
  required. Use generic fictional figures only when needed.
- Rotate topics across practical prompting, output verification, data confidentiality, responsible AI use, simple data
  interpretation, and time-saving finance workflows. Do not over-focus on credit decisions or advanced analytics.

Content and safety:
- Return valid JSON only, without markdown or commentary. Every mission must be bilingual in natural German and English.
- Never use or invent personal, confidential, Lufthansa-internal, SAP, customer, or employee data.
- Do not present legal or compliance advice as guaranteed truth. Use broadly accepted German enterprise principles and
  phrase compliance examples cautiously when company-specific rules could differ.
- Only use these automatically scored types: single_choice, multiple_choice, compliance_decision, prompt_selection, prompt_ranking,
  compliance_traffic_light.
- Single-answer types must have exactly one unambiguous correct answer. Multiple-choice missions may have one, several,
  or all answer options as correct.
- Distractors must be plausible but clearly wrong at the intended beginner level.
- Include concise bilingual feedback of 1-2 sentences that addresses the learner's concrete answer. Explain why the
  selected answer is correct or incorrect, but do not prefix it with labels such as "Correct", "Incorrect", "Richtig",
  or "Falsch"; the interface already displays that status.
- Include a separate bilingual micro-learning explanation after every mission. It must help the learner understand the
  underlying principle, not just repeat the correct answer or feedback. Write it as 2-4 plain-language sentences that
  connect the lesson to daily finance work and give the learner a transferable rule of thumb. Feedback answers
  "Why was this answer correct or incorrect?"; micro-learning answers "What should I apply in a similar situation?"
- Prompt-ranking missions contain 3-4 prompts and rank every prompt from worst to best. Make the quality progression
  clear through goal, context, expected output format, and concrete expectations.
- Compliance-traffic-light missions contain exactly three independent scenarios. Classify each as green (allowed),
  yellow (allowed only with safeguards), or red (not allowed), and provide short scenario-specific feedback.
- Descriptions must be one short, natural sentence summarizing the specific topic. Do not mention the expected duration,
  do not say that the learner must choose or determine an answer, and do not reuse a generic description template.
- Keep the JSON compact: titles under 80 characters, descriptions under 140 characters, questions under 240 characters,
  each option or statement under 180 characters, each feedback text under 240 characters, and each micro-learning text
  between 180 and 700 characters."""


def next_calendar_week(reference_date=None):
    today = reference_date or timezone.localdate()
    start = today + timedelta(days=7 - today.weekday())
    return start, start + timedelta(days=6)

def build_user_prompt(target_slots, requested_type=None, target_role='all', difficulty='beginner'):
    schedule = ', '.join(f'{day.isoformat()}: {count}' for day, count in sorted(target_slots.items()))
    type_requirement = f'Every mission must use exactly the type {requested_type}.' if requested_type else ''
    role_contexts = {
        'all': 'The missions should be useful for both accountants and controllers in a finance organization.',
        'accountant': 'The missions should focus on accountant tasks such as closing activities, accruals, correction bookings, reconciliations, journal entries, and safe SAP-related workflows.',
        'controller': 'The missions should focus on controller tasks such as reporting, budget vs. actual analysis, variance analysis, forecasting, KPI interpretation, and management insights.',
    }

    difficulty_contexts = {
        'beginner': 'Keep the missions simple, confidence-building, and suitable for employees with little or no AI experience.',
        'intermediate': 'Use slightly more realistic finance scenarios and require applying AI usage principles, not just recognizing definitions.',
        'advanced': 'Use more complex scenarios where the learner must evaluate prompts, question AI outputs, identify risks, and choose stronger next steps.',
    }

    role_context = role_contexts.get(target_role, role_contexts['all'])
    difficulty_context = difficulty_contexts.get(difficulty, difficulty_contexts['beginner'])
    return f"""Create exactly the requested missions for this schedule: {schedule}.
{type_requirement}
Target role: {target_role}.
{role_context}

Difficulty: {difficulty}.
{difficulty_context}
Use 10-50 points per mission. Return this structure:
{{"missions":[{{"date":"YYYY-MM-DD","type":"single_choice|multiple_choice|compliance_decision|prompt_selection|prompt_ranking|compliance_traffic_light",
"title_de":"...","title_en":"...","description_de":"...","description_en":"...","points":30,
"content":{{...type-specific fields...}}}}]}}
For single_choice, multiple_choice, compliance_decision, and prompt_selection use:
{{"question_de":"...","question_en":"...","options_de":["..."],"options_en":["..."],
"correct_option_indices":[0],"feedback_de":"...","feedback_en":"...",
"micro_learning_de":"...","micro_learning_en":"..."}}
For every micro_learning_de and micro_learning_en value: write 2-4 explanatory sentences. Do not start with
"Micro-Learning:" and do not simply name the correct answer. Explain the principle in a way that helps the learner
handle a similar situation next time. Do not reuse or paraphrase the feedback as the micro-learning text.
For multiple_choice, correct_option_indices must contain one to all option indices. For single_choice,
compliance_decision and prompt_selection it must contain exactly one index. Include a meaningful mix of multiple-choice missions with one
correct answer and with several correct answers.
For prompt_ranking use exactly 3-4 bilingual prompts and provide their zero-based order from worst to best:
{{"question_de":"...","question_en":"...","options_de":["..."],"options_en":["..."],
"correct_order":[0,2,1],"feedback_de":"...","feedback_en":"...",
"micro_learning_de":"...","micro_learning_en":"..."}}
For compliance_traffic_light use exactly three bilingual scenarios, one valid color per scenario, and bilingual
scenario-specific feedback:
{{"question_de":"...","question_en":"...","statements_de":["...","...","..."],
"statements_en":["...","...","..."],"correct_colors":["green","yellow","red"],
"statement_feedback_de":["...","...","..."],"statement_feedback_en":["...","...","..."],
"micro_learning_de":"...","micro_learning_en":"..."}}
The five traffic-light arrays must each contain exactly three items, never more or fewer. The content object must use
only the fields defined for its selected mission type. Do not add explanations outside the JSON object.
Across the requested schedule, favor broadly useful beginner topics and vary the scenarios. At least half of the
missions should focus on practical everyday AI usage such as prompting, checking outputs, confidentiality, or human
review. Include prompt_ranking and compliance_traffic_light regularly when enough slots are available. Use advanced
finance or AI terminology only when the term is explained within the mission.
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
        start = text.find('{')
        if start >= 0:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(text[start:])
                return parsed
            except json.JSONDecodeError:
                pass
        logger.warning(
            'AI returned invalid JSON (%s chars, error at %s). Response tail: %r',
            len(text), error_value.pos, text[-300:],
        )
        raise AiMissionGenerationError('AI returned invalid JSON, likely due to a truncated response') from error_value


def call_ai(target_slots, requested_type=None, target_role='all', difficulty='beginner'):
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
            {'role': 'user', 'content': build_user_prompt(target_slots, requested_type, target_role, difficulty)},
        ],
        'temperature': 0.4,
        'max_tokens': max(1000, int(os.environ.get('KICONNECT_MAX_TOKENS', DEFAULT_MAX_TOKENS))),
        'response_format': {'type': 'json_object'},
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
    except error.HTTPError as exception:
        if exception.code == 429:
            try:
                retry_after = max(1, int(exception.headers.get('Retry-After', '5')))
            except (TypeError, ValueError):
                retry_after = 5
            logger.warning('KICOnnect rate limit reached; retry after %s seconds', retry_after)
            raise AiMissionRateLimitError(retry_after) from exception
        if exception.code == 400:
            logger.warning('AI endpoint rejected JSON mode; retrying without response_format')
            legacy_body = json.loads(body.decode('utf-8'))
            legacy_body.pop('response_format', None)
            legacy_request = request.Request(
                f'{base_url}{path}',
                data=json.dumps(legacy_body).encode('utf-8'),
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                method='POST',
            )
            try:
                with request.urlopen(legacy_request, timeout=90) as response:
                    response_data = json.loads(response.read().decode('utf-8'))
                return extract_json(response_data['choices'][0]['message']['content'])
            except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as retry_exception:
                logger.exception('KICOnnect mission generation failed after JSON-mode fallback')
                raise AiMissionGenerationError('AI service is currently unavailable') from retry_exception
        logger.exception('KICOnnect mission generation failed with HTTP %s', exception.code)
        raise AiMissionGenerationError('AI service is currently unavailable') from exception
    except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exception:
        logger.exception('KICOnnect mission generation failed')
        raise AiMissionGenerationError('AI service is currently unavailable') from exception

def generate_candidates(target_slots, requested_type=None, target_role='all', difficulty='beginner'):
    if not target_slots:
        return []
    try:
        payload = call_ai(
            target_slots,
            requested_type=requested_type,
            target_role=target_role,
            difficulty=difficulty,
        )
        candidates = validate_generated_payload(payload, target_slots)
        if requested_type and any(candidate['mission_type'] != requested_type for candidate in candidates):
            raise MissionValidationError(f'AI did not return the requested type {requested_type}')
        return candidates
    except MissionValidationError as exception:
        logger.warning('Rejected invalid AI mission response: %s', exception)
        raise AiMissionGenerationError(f'AI response failed validation: {exception}') from exception


def split_target_slots(target_slots, max_missions=MAX_MISSIONS_PER_REQUEST):
    batches = []
    current = {}
    current_count = 0
    for day, count in sorted(target_slots.items()):
        if current and current_count + count > max_missions:
            batches.append(current)
            current = {}
            current_count = 0
        current[day] = count
        current_count += count
    if current:
        batches.append(current)
    return batches


def generate_candidate_batch(target_slots, target_role='all', difficulty='beginner'):
    retries = max(0, int(os.environ.get('KICONNECT_GENERATION_RETRIES', DEFAULT_GENERATION_RETRIES)))
    last_error = None
    for attempt in range(retries + 1):
        try:
            return generate_candidates(target_slots, target_role=target_role, difficulty=difficulty,
            )
        except AiMissionGenerationError as exception:
            last_error = exception
            if attempt < retries:
                if isinstance(exception, AiMissionRateLimitError):
                    time.sleep(exception.retry_after * (attempt + 1))
                logger.warning('Retrying AI mission batch after generation error: %s', exception)
    raise last_error


def generate_candidates_parallel(target_slots, target_role='all', difficulty='beginner'):
    batches = split_target_slots(target_slots)
    if len(batches) <= 1:
        return generate_candidate_batch(
            target_slots,
            target_role=target_role,
            difficulty=difficulty,
        )
    workers = max(1, min(
        len(batches),
        int(os.environ.get('KICONNECT_GENERATION_WORKERS', DEFAULT_GENERATION_WORKERS)),
    ))
    candidates = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                generate_candidate_batch,
                batch,
                target_role,
                difficulty,
            ): batch
            for batch in batches
        }
        for future in as_completed(futures):
            candidates.extend(future.result())
    return sorted(candidates, key=lambda candidate: candidate['scheduled_date'])


def apply_candidate(mission, candidate):
    mission.mission_type = candidate['mission_type']
    mission.scheduled_date = candidate['scheduled_date']
    mission.title_de = candidate['title_de']
    mission.title_en = candidate['title_en']
    mission.description_de = candidate['description_de']
    mission.description_en = candidate['description_en']
    mission.content = candidate['content']
    mission.max_points = candidate['max_points']


def generate_next_week(
    created_by,
    force=False,
    reference_date=None,
    week_start=None,
    target_role=Mission.ROLE_ALL,
    difficulty=Mission.DIFFICULTY_BEGINNER,
):
    if week_start is None:
        week_start, week_end = next_calendar_week(reference_date)
    else:
        week_end = week_start + timedelta(days=6)
    target_slots = {}
    today = timezone.localdate()
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        if day < today or not is_business_day(day):
            continue
        occupied_missions = Mission.objects.filter(
            scheduled_date=day,
            status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
            target_role=target_role,
            difficulty=difficulty,
        )
        if force:
            occupied_missions = occupied_missions.exclude(status=Mission.STATUS_REVIEW, generated_by_ai=True)
        occupied = occupied_missions.count()
        if occupied < 2:
            target_slots[day] = 2 - occupied

    candidates = generate_candidates_parallel(
        target_slots,
        target_role=target_role,
        difficulty=difficulty,
    )
    with transaction.atomic():
        missions = Mission.objects.select_for_update().filter(
            scheduled_date__range=(week_start, week_end),
            target_role=target_role,
            difficulty=difficulty,
        )
        if force:
            missions.filter(status=Mission.STATUS_REVIEW, generated_by_ai=True).delete()
        for day, expected_count in target_slots.items():
            occupied = Mission.objects.filter(
                scheduled_date=day,
                status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
                target_role=target_role,
                difficulty=difficulty,
            ).count()
            if occupied + expected_count > 2:
                raise AiMissionGenerationError(
                    f'mission schedule changed during generation for {day.isoformat()}; please try again'
                )
        batch_id = uuid.uuid4()
        created = []
        for candidate in candidates:
            mission = Mission(
                created_by=created_by,
                status=Mission.STATUS_REVIEW,
                generated_by_ai=True,
                generation_batch_id=batch_id,
                target_role=target_role,
                difficulty=difficulty,
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


def generate_training_candidate(mission_type):
    if mission_type not in Mission.CHOICE_TYPES:
        raise AiMissionGenerationError('Unsupported training mission type')
    return generate_candidates({timezone.localdate(): 1}, requested_type=mission_type)[0]
