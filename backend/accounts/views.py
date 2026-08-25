import json
import math
import os
from datetime import date, datetime, time, timedelta

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import (
    AgentChat,
    GenerationRun,
    Mission,
    MissionAssignment,
    MissionAttempt,
    Profile,
    SkillProgressionSettings,
    WeeklyLeaderboardSnapshot,
)
from .services.ai_mission_generator import AiMissionGenerationError
from .services.ai_chat_challenge import chat_reply, evaluate_final_answers
from .services.ai_task_challenge import (
    TASK_CHALLENGE_TYPES,
    evaluate_task_answers,
    public_content as task_public_content,
)
from .services.email_notifications import send_published_mission_email, send_published_mission_emails
from .services.n8n_client import N8NClientError, N8NConfigurationError
from .services.n8n_mission_generation import (
    GenerationContractError,
    create_regeneration_run,
    create_scheduled_task_run,
    create_training_chat_run,
    create_training_choice_run,
    create_training_task_run,
    create_weekly_run,
    dispatch_generation_run,
    generation_run_payload,
)
from .services.personal_agent import personal_agent_reply
from .services.skill_progression import (
    difficulty_for_skill,
    evaluate_skill_progression,
    progression_snapshot,
    set_skill_level_manually,
)


User = get_user_model()
VALID_ROLES = {choice for choice, _ in Profile.ROLE_CHOICES}
SELF_REGISTRATION_ROLES = {Profile.ROLE_CONTROLLER, Profile.ROLE_ACCOUNTANT}
VALID_SKILL_LEVELS = {choice for choice, _ in Profile.SKILL_LEVEL_CHOICES}
VALID_DIFFICULTIES = {choice for choice, _ in Mission.DIFFICULTY_CHOICES}
MISSION_AVAILABILITY_DEADLINE_HOUR = 12


def mission_week_start(scheduled_date):
    return scheduled_date - timedelta(days=scheduled_date.weekday())


def is_business_day(scheduled_date):
    return scheduled_date.weekday() < 5


def mission_availability_deadline(scheduled_date):
    deadline_date = mission_week_start(scheduled_date) + timedelta(days=7)
    deadline_time = time(hour=MISSION_AVAILABILITY_DEADLINE_HOUR)
    return timezone.make_aware(datetime.combine(deadline_date, deadline_time), timezone.get_current_timezone())


def mission_is_available(mission, reference_time=None):
    now = timezone.localtime(reference_time or timezone.now())
    return (
        is_business_day(mission.scheduled_date)
        and mission.scheduled_date <= now.date()
        and now < mission_availability_deadline(mission.scheduled_date)
    )


def mission_availability_start(reference_time=None):
    now = timezone.localtime(reference_time or timezone.now())
    current_week_start = mission_week_start(now.date())
    if now.weekday() == 0 and now.time() < time(hour=MISSION_AVAILABILITY_DEADLINE_HOUR):
        return current_week_start - timedelta(days=7)
    return current_week_start


def parse_json(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return {}


def dispatch_generation_response(run):
    if run.status == GenerationRun.STATUS_COMPLETED:
        return JsonResponse({'generation_run': generation_run_payload(run)}, status=200)
    if run.status not in {GenerationRun.STATUS_QUEUED, GenerationRun.STATUS_FAILED}:
        return JsonResponse({'generation_run': generation_run_payload(run)}, status=202)
    try:
        dispatch_generation_run(run)
    except N8NConfigurationError:
        return JsonResponse({
            'error': 'n8n mission generation is not configured',
            'generation_run': generation_run_payload(run),
        }, status=503)
    except N8NClientError:
        return JsonResponse({
            'error': 'n8n mission generation is currently unavailable',
            'generation_run': generation_run_payload(run),
        }, status=502)
    return JsonResponse({'generation_run': generation_run_payload(run)}, status=202)


def can_access_generation_run(user, run):
    return user.is_authenticated and (run.requested_by_id == user.id or can_create_missions(user))


def should_seed_admin(user):
    configured_email = os.environ.get('INITIAL_ADMIN_EMAIL', '').strip().lower()
    if configured_email:
        return user.email.lower() == configured_email

    has_admin = Profile.objects.filter(role=Profile.ROLE_ADMIN).exists()
    first_user = User.objects.order_by('id').first()
    return not has_admin and first_user is not None and first_user.id == user.id


def ensure_profile(user):
    profile, created = Profile.objects.get_or_create(user=user)
    if created and should_seed_admin(user):
        profile.role = Profile.ROLE_ADMIN
        profile.save(update_fields=['role'])
    return profile


def is_admin(user):
    return user.is_authenticated and ensure_profile(user).role == Profile.ROLE_ADMIN


def admin_count():
    return Profile.objects.filter(role=Profile.ROLE_ADMIN).count()


def level_for_points(points):
    if points >= 180:
        return 'Advanced'
    if points >= 90:
        return 'Practitioner'
    return 'Starter'


def streak_payload(user):
    today = timezone.localdate()
    missions_by_date = {}
    for mission_id, scheduled_date in Mission.objects.filter(
        status=Mission.STATUS_PUBLISHED,
        scheduled_date__lte=today,
    ).order_by('scheduled_date', 'created_at', 'id').values_list('id', 'scheduled_date'):
        missions_by_date.setdefault(scheduled_date, {mission_id})

    attempted_ids = {
        mission_id
        for mission_id, scheduled_date, completed_at in MissionAttempt.objects.filter(
            user=user,
            mission__status=Mission.STATUS_PUBLISHED,
            mission__scheduled_date__lte=today,
        ).values_list('mission_id', 'mission__scheduled_date', 'completed_at')
        if timezone.localtime(completed_at).date() == scheduled_date
    }
    completed_dates = {
        scheduled_date
        for scheduled_date, mission_ids in missions_by_date.items()
        if mission_ids and mission_ids.issubset(attempted_ids)
    }

    maximum = 0
    running = 0
    previous = None
    for completed_date in sorted(completed_dates):
        running = running + 1 if previous and completed_date == previous + timedelta(days=1) else 1
        maximum = max(maximum, running)
        previous = completed_date

    anchor = today if today in completed_dates else today - timedelta(days=1)
    current = 0
    while anchor in completed_dates:
        current += 1
        anchor -= timedelta(days=1)
    return {'current_streak': current, 'max_streak': maximum}


def week_bounds(reference_date=None):
    day = reference_date or timezone.localdate()
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def user_identity(user):
    return {
        'user_id': user.id,
        'name': f'{user.first_name} {user.last_name}'.strip() or user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def rank_entries(entries):
    entries.sort(key=lambda entry: (-entry['total_points'], -entry['completed_missions'], entry['name'].lower()))
    for index, entry in enumerate(entries, start=1):
        entry['rank'] = index
    return entries


def weekly_leaderboard_entries(week_start, week_end, difficulty):
    users = User.objects.order_by('first_name', 'last_name', 'username')
    entries = []
    for user in users:
        attempts = MissionAttempt.objects.filter(
            user=user,
            completed_at__date__range=(week_start, week_end),
            difficulty=difficulty,
        )
        points = sum(attempts.values_list('score', flat=True))
        completed = attempts.count()
        if points <= 0:
            continue
        entries.append({
            **user_identity(user),
            'total_points': points,
            'completed_missions': completed,
            'level': level_for_points(points),
        })
    return rank_entries(entries)


def archive_completed_weeks():
    current_week_start, _ = week_bounds()
    earliest_attempt = MissionAttempt.objects.order_by('completed_at').first()
    if earliest_attempt is None:
        return
    attempt_date = timezone.localtime(earliest_attempt.completed_at).date()
    candidate_start, _ = week_bounds(attempt_date)
    while candidate_start < current_week_start:
        candidate_end = candidate_start + timedelta(days=6)
        if MissionAttempt.objects.filter(completed_at__date__range=(candidate_start, candidate_end)).exists():
            for difficulty in Mission.DIFFICULTIES:
                WeeklyLeaderboardSnapshot.objects.get_or_create(
                    week_start=candidate_start,
                    difficulty=difficulty,
                    defaults={
                        'week_end': candidate_end,
                        'entries': weekly_leaderboard_entries(candidate_start, candidate_end, difficulty),
                    },
                )
        candidate_start += timedelta(days=7)


def progress_payload(profile):
    scores = profile.mission_scores or {}
    attempts = MissionAttempt.objects.filter(user=profile.user)
    attempt_points = sum(attempts.values_list('score', flat=True))
    completed_attempts = attempts.count()
    legacy_completed = sum(1 for score in scores.values() if int(score) > 0)
    total_points = profile.total_points + attempt_points
    streaks = streak_payload(profile.user)
    return {
        'mission_scores': scores,
        'completed_missions': [mission_id for mission_id, score in scores.items() if int(score) > 0],
        'completed_mission_count': legacy_completed + completed_attempts,
        'total_points': total_points,
        'level': level_for_points(total_points),
        'skill_level': profile.skill_level,
        'difficulty': difficulty_for_skill(profile.skill_level),
        'skill_progression': progression_snapshot(profile),
        **streaks,
        'updated_at': profile.progress_updated_at.isoformat() if profile.progress_updated_at else None,
    }


def can_create_missions(user):
    if not user.is_authenticated:
        return False
    return ensure_profile(user).role in {Profile.ROLE_CONTENT_CREATOR, Profile.ROLE_ADMIN}


def translated(value, language):
    return value.get(language) or value.get('de') or value.get('en') or ''


def correct_indices(content):
    indices = content.get('correct_indices')
    if isinstance(indices, list):
        return indices
    index = content.get('correct_index')
    return [index] if isinstance(index, int) else []


def translated_feedback(content, language):
    feedback = translated(content.get('feedback', {}), language)
    if feedback:
        return feedback
    options = content.get('options', [])
    correct_options = [
        translated(options[index], language)
        for index in correct_indices(content)
        if 0 <= index < len(options)
    ]
    if not correct_options:
        return ''
    prefix = 'Correct answer' if language == 'en' else 'Richtige Antwort'
    return f'{prefix}: {", ".join(correct_options)}.'


def traffic_light_feedback(statement, language):
    feedback = translated(statement.get('feedback', {}), language)
    if feedback:
        return feedback
    color = statement.get('correct_color', '')
    labels = {
        'de': {'green': 'erlaubt', 'yellow': 'nur eingeschraenkt erlaubt', 'red': 'nicht erlaubt'},
        'en': {'green': 'allowed', 'yellow': 'allowed with restrictions', 'red': 'not allowed'},
    }
    prefix = 'Richtige Bewertung' if language == 'de' else 'Correct assessment'
    return f'{prefix}: {labels[language].get(color, color)}.'


def user_mission_attempt(mission, user):
    if hasattr(mission, 'user_attempts'):
        return mission.user_attempts[0] if mission.user_attempts else None
    return mission.attempts.filter(user=user).first()


def assigned_mission_difficulty(mission, user, create=False):
    attempt = user_mission_attempt(mission, user)
    if attempt is not None and attempt.difficulty in VALID_DIFFICULTIES:
        return attempt.difficulty
    if not mission.has_difficulty_variants:
        return None
    assignment = MissionAssignment.objects.filter(user=user, mission=mission).first()
    if assignment is not None:
        return assignment.difficulty
    if not create:
        return difficulty_for_skill(ensure_profile(user).skill_level)
    assignment, _created = MissionAssignment.objects.get_or_create(
        user=user,
        mission=mission,
        defaults={'difficulty': difficulty_for_skill(ensure_profile(user).skill_level)},
    )
    return assignment.difficulty


def mission_variant(mission, user, create_assignment=False):
    difficulty = assigned_mission_difficulty(mission, user, create=create_assignment)
    if difficulty and mission.has_difficulty_variants:
        variant = mission.variants.get(difficulty)
        if isinstance(variant, dict):
            return difficulty, variant
    return None, {
        'title_de': mission.title_de,
        'title_en': mission.title_en,
        'description_de': mission.description_de,
        'description_en': mission.description_en,
        'content': mission.content or {},
        'max_points': mission.max_points,
    }


def mission_payload(mission, user, language='de', include_content=True, create_assignment=False):
    attempt = user_mission_attempt(mission, user)
    difficulty, variant = mission_variant(mission, user, create_assignment=create_assignment)
    content = variant.get('content') or {}
    payload = {
        'id': mission.id,
        'type': mission.mission_type,
        'scheduled_date': mission.scheduled_date.isoformat(),
        'title': variant.get('title_en') if language == 'en' else variant.get('title_de'),
        'description': variant.get('description_en') if language == 'en' else variant.get('description_de'),
        'max_points': variant.get('max_points', mission.max_points),
        'difficulty': difficulty,
        'topic': mission.topic_en if language == 'en' else mission.topic_de,
        'learning_objective': mission.learning_objective_en if language == 'en' else mission.learning_objective_de,
        'completed': attempt is not None,
        'score': attempt.score if attempt else None,
    }
    if include_content and mission.mission_type == Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT:
        payload['content'] = {
            'question': translated(content.get('question', {}), language),
            'statements': [translated(statement.get('text', {}), language) for statement in content.get('statements', [])],
        }
        if attempt is not None:
            payload['content']['feedback'] = [
                traffic_light_feedback(statement, language) for statement in content.get('statements', [])
            ]
    elif include_content and mission.mission_type == Mission.TYPE_PROMPT_RANKING:
        payload['content'] = {
            'question': translated(content.get('question', {}), language),
            'options': [translated(option, language) for option in content.get('options', [])],
        }
        if attempt is not None:
            payload['content']['feedback'] = translated_feedback(content, language)
    elif include_content and mission.mission_type in Mission.TASK_TYPES:
        payload['content'] = task_public_content(content, language)
        if attempt is not None:
            solutions = {field['id']: field for field in content.get('result_fields', [])}
            payload['content']['field_results'] = [
                {
                    'id': field['id'],
                    'solution': solutions[field['id']]['solution'],
                    'feedback': translated(solutions[field['id']].get('feedback', {}), language),
                }
                for field in content.get('result_fields', [])
            ]
    elif include_content and mission.mission_type in Mission.CHOICE_TYPES:
        payload['content'] = {
            'question': translated(content.get('question', {}), language),
            'options': [translated(option, language) for option in content.get('options', [])],
            'multiple': mission.mission_type == Mission.TYPE_MULTIPLE_CHOICE,
        }
        if attempt is not None:
            payload['content']['feedback'] = translated_feedback(content, language)
    if include_content and attempt is not None:
        micro_learning = translated(content.get('micro_learning', {}), language)
        if micro_learning:
            payload.setdefault('content', {})['micro_learning'] = micro_learning
    return payload


def mission_archive_payload(mission, user, language='de'):
    payload = mission_payload(mission, user, language)
    attempt = user_mission_attempt(mission, user)
    if attempt is not None:
        payload['attempt'] = {
            'answer': attempt.answer,
            'score': attempt.score,
            'completed_at': attempt.completed_at.isoformat(),
        }
        payload['result'] = {
            'score': attempt.score,
            'max_points': attempt.max_points,
            'correct': attempt.score == attempt.max_points,
        }
    return payload


def mission_schedule_payload(mission, user):
    content = mission.content or {}
    return {
        'id': mission.id,
        'type': mission.mission_type,
        'scheduled_date': mission.scheduled_date.isoformat(),
        'title_de': mission.title_de,
        'title_en': mission.title_en,
        'description_de': mission.description_de,
        'description_en': mission.description_en,
        'topic_de': mission.topic_de,
        'topic_en': mission.topic_en,
        'learning_objective_de': mission.learning_objective_de,
        'learning_objective_en': mission.learning_objective_en,
        'variants': mission.variants,
        'has_difficulty_variants': mission.has_difficulty_variants,
        'question_de': translated(content.get('question') or content.get('task') or {}, 'de'),
        'question_en': translated(content.get('question') or content.get('task') or {}, 'en'),
        'case_format': content.get('case_format', 'table'),
        'case_data_de': (content.get('case_data') or {}).get('de', []),
        'case_data_en': (content.get('case_data') or {}).get('en', []),
        'result_fields': [
            {
                'id': field.get('id'),
                'type': field.get('type'),
                'label_de': translated(field.get('label', {}), 'de'),
                'label_en': translated(field.get('label', {}), 'en'),
                'unit': field.get('unit', ''),
                'solution': field.get('solution'),
                'tolerance': field.get('tolerance', 0),
                'feedback_de': translated(field.get('feedback', {}), 'de'),
                'feedback_en': translated(field.get('feedback', {}), 'en'),
            }
            for field in content.get('result_fields', [])
        ],
        'options': [
            {'de': translated(option, 'de'), 'en': translated(option, 'en')}
            for option in content.get('options', [])
        ],
        'correct_indices': correct_indices(content),
        'correct_order': content.get('correct_order', []),
        'statements': [
            {
                'de': translated(statement.get('text', {}), 'de'),
                'en': translated(statement.get('text', {}), 'en'),
                'correct_color': statement.get('correct_color', ''),
                'feedback_de': translated(statement.get('feedback', {}), 'de'),
                'feedback_en': translated(statement.get('feedback', {}), 'en'),
            }
            for statement in content.get('statements', [])
        ],
        'max_points': mission.max_points,
        'status': mission.status,
        'generated_by_ai': mission.generated_by_ai,
        'feedback_de': translated(content.get('feedback', {}), 'de'),
        'feedback_en': translated(content.get('feedback', {}), 'en'),
        'micro_learning_de': translated(content.get('micro_learning', {}), 'de'),
        'micro_learning_en': translated(content.get('micro_learning', {}), 'en'),
        'created_by': mission.created_by_id,
        'can_delete': can_create_missions(user),
        'can_edit': can_create_missions(user),
        'has_attempts': mission.attempts.exists(),
    }


def parse_iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


MANUAL_MISSION_TYPES = Mission.CHOICE_TYPES | Mission.TASK_TYPES


def validate_mission_identity(data, allow_past_date=False):
    scheduled_date = parse_iso_date(data.get('scheduled_date'))
    mission_type = data.get('type')
    if not scheduled_date or (not allow_past_date and scheduled_date < timezone.localdate()):
        return None, 'scheduled date must be today or later'
    if not is_business_day(scheduled_date):
        return None, 'scheduled date must be a weekday'
    if mission_type not in MANUAL_MISSION_TYPES:
        return None, 'unsupported mission type'
    return (mission_type, scheduled_date), None


def validate_choice_mission_data(data, allow_past_date=False):
    identity, identity_error = validate_mission_identity(data, allow_past_date)
    if identity_error:
        return None, identity_error
    mission_type, scheduled_date = identity
    if mission_type not in Mission.CHOICE_TYPES:
        return None, 'unsupported choice mission type'

    required_text = (
        'title_de', 'title_en', 'description_de', 'description_en', 'question_de', 'question_en',
    )
    if any(not str(data.get(field, '')).strip() for field in required_text):
        return None, 'all bilingual text fields are required'
    if mission_type == Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT:
        statements = data.get('statements') or []
        colors = {'green', 'yellow', 'red'}
        if len(statements) != 3 or any(
            not statement.get('de', '').strip()
            or not statement.get('en', '').strip()
            or statement.get('correct_color') not in colors
            or not statement.get('feedback_de', '').strip()
            or not statement.get('feedback_en', '').strip()
            for statement in statements
        ):
            return None, 'exactly three bilingual traffic-light statements with feedback are required'
        try:
            max_points = int(data.get('max_points', 100))
        except (TypeError, ValueError):
            return None, 'invalid points'
        if max_points < 1 or max_points > 1000:
            return None, 'invalid points'
        return {
            'mission_type': mission_type,
            'scheduled_date': scheduled_date,
            'title_de': data['title_de'].strip(),
            'title_en': data['title_en'].strip(),
            'description_de': data['description_de'].strip(),
            'description_en': data['description_en'].strip(),
            'content': {
                'question': {'de': data['question_de'].strip(), 'en': data['question_en'].strip()},
                'statements': [
                    {
                        'text': {'de': statement['de'].strip(), 'en': statement['en'].strip()},
                        'correct_color': statement['correct_color'],
                        'feedback': {
                            'de': statement['feedback_de'].strip(),
                            'en': statement['feedback_en'].strip(),
                        },
                    }
                    for statement in statements
                ],
                'micro_learning': {
                    'de': str(data.get('micro_learning_de', '')).strip(),
                    'en': str(data.get('micro_learning_en', '')).strip(),
                },
            },
            'max_points': max_points,
        }, None

    options = data.get('options') or []
    minimum_options = 3 if mission_type == Mission.TYPE_PROMPT_RANKING else 2
    maximum_options = 4 if mission_type == Mission.TYPE_PROMPT_RANKING else 6
    if len(options) < minimum_options or len(options) > maximum_options or any(
        not option.get('de', '').strip() or not option.get('en', '').strip() for option in options
    ):
        return None, f'{minimum_options} to {maximum_options} bilingual options are required'
    if mission_type == Mission.TYPE_PROMPT_RANKING:
        try:
            selected_correct_order = [int(index) for index in data.get('correct_order', [])]
            max_points = int(data.get('max_points', 100))
        except (TypeError, ValueError):
            return None, 'invalid ranking or points'
        if sorted(selected_correct_order) != list(range(len(options))) or max_points < 1 or max_points > 1000:
            return None, 'ranking must contain every option exactly once'
        return {
            'mission_type': mission_type,
            'scheduled_date': scheduled_date,
            'title_de': data['title_de'].strip(),
            'title_en': data['title_en'].strip(),
            'description_de': data['description_de'].strip(),
            'description_en': data['description_en'].strip(),
            'content': {
                'question': {'de': data['question_de'].strip(), 'en': data['question_en'].strip()},
                'options': [{'de': option['de'].strip(), 'en': option['en'].strip()} for option in options],
                'correct_order': selected_correct_order,
                'feedback': {
                    'de': str(data.get('feedback_de', '')).strip(),
                    'en': str(data.get('feedback_en', '')).strip(),
                },
                'micro_learning': {
                    'de': str(data.get('micro_learning_de', '')).strip(),
                    'en': str(data.get('micro_learning_en', '')).strip(),
                },
            },
            'max_points': max_points,
        }, None
    raw_correct_indices = data.get('correct_indices')
    if raw_correct_indices is None and data.get('correct_index') is not None:
        raw_correct_indices = [data.get('correct_index')]
    try:
        selected_correct_indices = sorted({int(index) for index in (raw_correct_indices or [])})
        max_points = int(data.get('max_points', 100))
    except (TypeError, ValueError):
        return None, 'invalid correct answer or points'
    if (
        not selected_correct_indices
        or any(index < 0 or index >= len(options) for index in selected_correct_indices)
        or max_points < 1
        or max_points > 1000
    ):
        return None, 'invalid correct answer or points'
    if mission_type != Mission.TYPE_MULTIPLE_CHOICE and len(selected_correct_indices) != 1:
        return None, 'this mission type requires exactly one correct answer'
    return {
        'mission_type': mission_type,
        'scheduled_date': scheduled_date,
        'title_de': data['title_de'].strip(),
        'title_en': data['title_en'].strip(),
        'description_de': data['description_de'].strip(),
        'description_en': data['description_en'].strip(),
        'content': {
            'question': {'de': data['question_de'].strip(), 'en': data['question_en'].strip()},
            'options': [{'de': option['de'].strip(), 'en': option['en'].strip()} for option in options],
            'correct_indices': selected_correct_indices,
            'feedback': {
                'de': str(data.get('feedback_de', '')).strip(),
                'en': str(data.get('feedback_en', '')).strip(),
            },
            'micro_learning': {
                'de': str(data.get('micro_learning_de', '')).strip(),
                'en': str(data.get('micro_learning_en', '')).strip(),
            },
        },
        'max_points': max_points,
    }, None


def validate_task_mission_data(data, allow_past_date=False):
    identity, identity_error = validate_mission_identity(data, allow_past_date)
    if identity_error:
        return None, identity_error
    mission_type, scheduled_date = identity
    if mission_type not in Mission.TASK_TYPES:
        return None, 'unsupported task mission type'

    required_text = (
        'title_de', 'title_en', 'description_de', 'description_en', 'question_de', 'question_en',
    )
    if any(not str(data.get(field, '')).strip() for field in required_text):
        return None, 'all bilingual task text fields are required'

    case_format = str(data.get('case_format', 'table')).strip()
    case_data_de = data.get('case_data_de')
    case_data_en = data.get('case_data_en')
    if case_format not in {'table', 'prose'}:
        return None, 'task case format must be table or prose'
    if (
        not isinstance(case_data_de, list)
        or not isinstance(case_data_en, list)
        or not 1 <= len(case_data_de) <= 100
        or len(case_data_de) != len(case_data_en)
        or any(not str(value).strip() for value in [*case_data_de, *case_data_en])
    ):
        return None, 'task case data must contain 1 to 100 aligned bilingual rows'

    raw_fields = data.get('result_fields')
    if not isinstance(raw_fields, list) or not 1 <= len(raw_fields) <= 12:
        return None, 'task missions require 1 to 12 result fields'
    result_fields = []
    field_ids = set()
    for position, raw_field in enumerate(raw_fields, start=1):
        if not isinstance(raw_field, dict):
            return None, f'task result field {position} is invalid'
        field_id = str(raw_field.get('id', '')).strip()
        field_type = str(raw_field.get('type', '')).strip()
        label_de = str(raw_field.get('label_de', '')).strip()
        label_en = str(raw_field.get('label_en', '')).strip()
        feedback_de = str(raw_field.get('feedback_de', '')).strip()
        feedback_en = str(raw_field.get('feedback_en', '')).strip()
        if (
            not field_id
            or len(field_id) > 80
            or field_id in field_ids
            or field_type not in {'number', 'text'}
            or not label_de
            or not label_en
            or not feedback_de
            or not feedback_en
        ):
            return None, f'task result field {position} needs a unique id, type, bilingual label, and feedback'
        field_ids.add(field_id)

        if field_type == 'number':
            try:
                solution = float(raw_field.get('solution'))
                tolerance = float(raw_field.get('tolerance', 0))
            except (TypeError, ValueError):
                return None, f'task result field {position} needs a numeric solution and tolerance'
            if not math.isfinite(solution) or not math.isfinite(tolerance) or tolerance < 0:
                return None, f'task result field {position} needs a finite solution and non-negative tolerance'
        else:
            raw_solution = raw_field.get('solution')
            solution_de = str(
                raw_solution.get('de', '') if isinstance(raw_solution, dict) else raw_field.get('solution_de', '')
            ).strip()
            solution_en = str(
                raw_solution.get('en', '') if isinstance(raw_solution, dict) else raw_field.get('solution_en', '')
            ).strip()
            if not solution_de or not solution_en:
                return None, f'task result field {position} needs a bilingual text solution'
            solution = {'de': solution_de, 'en': solution_en}
            tolerance = 0

        result_fields.append({
            'id': field_id,
            'type': field_type,
            'label': {'de': label_de, 'en': label_en},
            'unit': str(raw_field.get('unit', '')).strip(),
            'solution': solution,
            'tolerance': tolerance,
            'feedback': {'de': feedback_de, 'en': feedback_en},
        })

    try:
        max_points = int(data.get('max_points', 100))
    except (TypeError, ValueError):
        return None, 'invalid points'
    if not 1 <= max_points <= 1000:
        return None, 'invalid points'

    return {
        'mission_type': mission_type,
        'scheduled_date': scheduled_date,
        'title_de': str(data['title_de']).strip(),
        'title_en': str(data['title_en']).strip(),
        'description_de': str(data['description_de']).strip(),
        'description_en': str(data['description_en']).strip(),
        'content': {
            'task': {'de': str(data['question_de']).strip(), 'en': str(data['question_en']).strip()},
            'case_data': {
                'de': [str(value).strip() for value in case_data_de],
                'en': [str(value).strip() for value in case_data_en],
            },
            'case_format': case_format,
            'result_fields': result_fields,
            'micro_learning': {
                'de': str(data.get('micro_learning_de', '')).strip(),
                'en': str(data.get('micro_learning_en', '')).strip(),
            },
        },
        'max_points': max_points,
    }, None


def validate_manual_mission_data(data, allow_past_date=False):
    identity, identity_error = validate_mission_identity(data, allow_past_date)
    if identity_error:
        return None, identity_error
    mission_type, scheduled_date = identity

    shared_fields = ('topic_de', 'topic_en', 'learning_objective_de', 'learning_objective_en')
    if any(not str(data.get(field, '')).strip() for field in shared_fields):
        return None, 'all bilingual topic and learning objective fields are required'

    raw_variants = data.get('variants')
    if not isinstance(raw_variants, dict) or set(raw_variants) != set(Mission.DIFFICULTIES):
        return None, 'exactly easy, medium, and hard variants are required'

    variants = {}
    for difficulty in Mission.DIFFICULTIES:
        raw_variant = raw_variants[difficulty]
        if not isinstance(raw_variant, dict):
            return None, f'{difficulty} variant must be an object'
        variant_validator = (
            validate_task_mission_data if mission_type in Mission.TASK_TYPES else validate_choice_mission_data
        )
        variant_values, variant_error = variant_validator({
            **raw_variant,
            'type': mission_type,
            'scheduled_date': scheduled_date.isoformat(),
        }, allow_past_date=allow_past_date)
        if variant_error:
            return None, f'{difficulty} variant: {variant_error}'
        variants[difficulty] = {
            'title_de': variant_values['title_de'],
            'title_en': variant_values['title_en'],
            'description_de': variant_values['description_de'],
            'description_en': variant_values['description_en'],
            'content': variant_values['content'],
            'max_points': variant_values['max_points'],
        }

    easy = variants[Mission.DIFFICULTY_EASY]
    return {
        'mission_type': mission_type,
        'scheduled_date': scheduled_date,
        'topic_de': str(data['topic_de']).strip(),
        'topic_en': str(data['topic_en']).strip(),
        'learning_objective_de': str(data['learning_objective_de']).strip(),
        'learning_objective_en': str(data['learning_objective_en']).strip(),
        'variants': variants,
        # Keep the easy variant as the legacy schedule/review fallback. Learner
        # delivery always resolves the persisted assignment from ``variants``.
        **easy,
    }, None


def user_payload(user):
    profile = ensure_profile(user)
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': profile.role,
        'role_display': profile.get_role_display(),
        'skill_level': profile.skill_level,
        'skill_level_display': profile.get_skill_level_display(),
        'skill_progression': progression_snapshot(profile),
        'onboarding_completed': profile.onboarding_completed,
        'onboarding_completed_at': profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None,
        'onboarding_progress': profile.onboarding_progress or [],
        'progress': progress_payload(profile),
    }


@require_http_methods(['POST'])
@csrf_exempt
def login_view(request):
    data = parse_json(request)
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')
    if not identifier or not password:
        return JsonResponse({'error': 'email and password required'}, status=400)

    if '@' in identifier:
        match = User.objects.filter(email__iexact=identifier).first()
        if match is not None:
            identifier = match.username

    user = authenticate(request, username=identifier, password=password)
    if user is None:
        return JsonResponse({'error': 'invalid credentials'}, status=401)

    login(request, user)
    return JsonResponse({'authenticated': True, 'user': user_payload(user)})


@require_http_methods(['POST'])
@csrf_exempt
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
@ensure_csrf_cookie
def user_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'user': user_payload(request.user)})


@require_http_methods(['GET'])
def users_view(request):
    if not is_admin(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    users = User.objects.order_by('first_name', 'last_name', 'email', 'username')
    return JsonResponse({'users': [user_payload(user) for user in users]})


@require_http_methods(['PATCH'])
@csrf_exempt
def update_user_role_view(request, user_id):
    if not is_admin(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)

    role = parse_json(request).get('role')
    if role not in VALID_ROLES:
        return JsonResponse({'error': 'invalid role'}, status=400)

    target = User.objects.filter(id=user_id).first()
    if target is None:
        return JsonResponse({'error': 'user not found'}, status=404)

    profile = ensure_profile(target)
    if profile.role == Profile.ROLE_ADMIN and role != Profile.ROLE_ADMIN and admin_count() <= 1:
        return JsonResponse({'error': 'last admin cannot be downgraded'}, status=400)

    profile.role = role
    profile.save(update_fields=['role'])
    return JsonResponse({'user': user_payload(target)})


@require_http_methods(['PATCH'])
@csrf_exempt
def update_user_skill_level_view(request, user_id):
    if not is_admin(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    skill_level = parse_json(request).get('skill_level')
    if skill_level not in VALID_SKILL_LEVELS:
        return JsonResponse({'error': 'invalid skill level'}, status=400)
    target = User.objects.filter(id=user_id).first()
    if target is None:
        return JsonResponse({'error': 'user not found'}, status=404)
    profile, _changed = set_skill_level_manually(ensure_profile(target), skill_level)
    return JsonResponse({'user': user_payload(profile.user)})


def progression_settings_payload(settings_object):
    return {
        'automatic_progression_enabled': settings_object.automatic_progression_enabled,
        'evaluation_window': settings_object.evaluation_window,
        'minimum_missions': settings_object.minimum_missions,
        'promotion_threshold': settings_object.promotion_threshold,
        'demotion_threshold': settings_object.demotion_threshold,
        'updated_at': settings_object.updated_at.isoformat() if settings_object.updated_at else None,
    }


@require_http_methods(['GET', 'PATCH'])
@csrf_exempt
def progression_settings_view(request):
    if not is_admin(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    settings_object = SkillProgressionSettings.load()
    if request.method == 'GET':
        return JsonResponse({'settings': progression_settings_payload(settings_object)})
    data = parse_json(request)
    enabled = data.get('automatic_progression_enabled')
    if not isinstance(enabled, bool):
        return JsonResponse({'error': 'automatic progression must be true or false'}, status=400)
    try:
        evaluation_window = int(data.get('evaluation_window'))
        minimum_missions = int(data.get('minimum_missions'))
        promotion_threshold = int(data.get('promotion_threshold'))
        demotion_threshold = int(data.get('demotion_threshold'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'progression values must be integers'}, status=400)
    if evaluation_window < 1 or minimum_missions < 1:
        return JsonResponse({'error': 'mission counts must be positive'}, status=400)
    if not 0 <= demotion_threshold < promotion_threshold <= 100:
        return JsonResponse({'error': 'thresholds must satisfy 0 <= demotion < promotion <= 100'}, status=400)
    settings_object.automatic_progression_enabled = enabled
    settings_object.evaluation_window = evaluation_window
    settings_object.minimum_missions = minimum_missions
    settings_object.promotion_threshold = promotion_threshold
    settings_object.demotion_threshold = demotion_threshold
    settings_object.save()
    return JsonResponse({'settings': progression_settings_payload(settings_object)})


@require_http_methods(['DELETE'])
@csrf_exempt
def delete_user_view(request, user_id):
    if not is_admin(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)

    target = User.objects.filter(id=user_id).first()
    if target is None:
        return JsonResponse({'error': 'user not found'}, status=404)
    if target.id == request.user.id:
        return JsonResponse({'error': 'current user cannot be deleted'}, status=400)

    profile = ensure_profile(target)
    if profile.role == Profile.ROLE_ADMIN and admin_count() <= 1:
        return JsonResponse({'error': 'last admin cannot be deleted'}, status=400)

    target.delete()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@csrf_exempt
def register_view(request):
    data = parse_json(request)
    password = data.get('password', '')
    email = data.get('email', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    username = (data.get('username') or email).strip()
    role = (data.get('role') or '').strip()

    if not all([username, password, email, first_name, last_name]):
        return JsonResponse({'error': 'all fields required'}, status=400)
    if role and role not in SELF_REGISTRATION_ROLES:
        return JsonResponse({'error': 'invalid role'}, status=400)
    if User.objects.filter(username=username).exists() or User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'account already exists'}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    profile = Profile.objects.create(user=user, **({'role': role} if role else {}))
    if should_seed_admin(user):
        profile.role = Profile.ROLE_ADMIN
        profile.save(update_fields=['role'])
    login(request, user)
    return JsonResponse({'authenticated': True, 'user': user_payload(user)}, status=201)


@require_http_methods(['POST'])
@csrf_exempt
def change_password_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    data = parse_json(request)
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not old_password or not new_password:
        return JsonResponse({'error': 'both passwords required'}, status=400)
    if not request.user.check_password(old_password):
        return JsonResponse({'error': 'current password is incorrect'}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@csrf_exempt
def onboarding_progress_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    chapter = (parse_json(request).get('chapter') or '').strip()
    if not chapter:
        return JsonResponse({'error': 'chapter required'}, status=400)

    profile = ensure_profile(request.user)
    progress = list(profile.onboarding_progress or [])
    if chapter not in progress:
        progress.append(chapter)
        profile.onboarding_progress = progress
        profile.save(update_fields=['onboarding_progress'])
    return JsonResponse({'user': user_payload(request.user)})


@require_http_methods(['POST'])
@csrf_exempt
def onboarding_complete_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    profile = ensure_profile(request.user)
    if not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.onboarding_completed_at = timezone.now()
        profile.save(update_fields=['onboarding_completed', 'onboarding_completed_at'])
    return JsonResponse({'user': user_payload(request.user)})


@require_http_methods(['GET'])
def progress_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    return JsonResponse({'progress': progress_payload(ensure_profile(request.user))})


@require_http_methods(['POST'])
@csrf_exempt
def complete_mission_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    data = parse_json(request)
    language = 'en' if data.get('language') == 'en' else 'de'
    mission = Mission.objects.filter(
        id=data.get('mission_id'),
        status=Mission.STATUS_PUBLISHED,
    ).first()
    if mission is None or not mission_is_available(mission):
        return JsonResponse({'error': 'mission not available'}, status=404)
    canonical_mission_id = Mission.objects.filter(
        scheduled_date=mission.scheduled_date,
        status=Mission.STATUS_PUBLISHED,
    ).order_by('created_at', 'id').values_list('id', flat=True).first()
    if canonical_mission_id != mission.id:
        return JsonResponse({'error': 'mission not available'}, status=404)
    if MissionAttempt.objects.filter(user=request.user, mission=mission).exists():
        return JsonResponse({'error': 'mission already completed'}, status=409)

    if mission.mission_type not in Mission.CHOICE_TYPES and mission.mission_type not in Mission.TASK_TYPES:
        return JsonResponse({'error': 'unsupported mission type'}, status=400)

    difficulty, variant = mission_variant(mission, request.user, create_assignment=True)
    content = variant.get('content') or {}
    max_points = int(variant.get('max_points', mission.max_points))
    if mission.mission_type in Mission.TASK_TYPES:
        answer = data.get('answer')
        if not isinstance(answer, dict):
            return JsonResponse({'error': 'result values required'}, status=400)
        values = answer.get('values')
        if not isinstance(values, dict):
            return JsonResponse({'error': 'result values required'}, status=400)
        prompt_evidence = str(answer.get('prompt', ''))[:4000]
        evaluation = evaluate_task_answers(content, values, language)
        total = evaluation['total_count'] or 1
        score = max_points * evaluation['correct_count'] // total
        stored_answer = {'values': values, 'prompt': prompt_evidence}
        result_details = {
            'correct_count': evaluation['correct_count'],
            'total_count': evaluation['total_count'],
            'field_results': evaluation['field_results'],
        }
    elif mission.mission_type == Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT:
        statements = content.get('statements', [])
        if len(statements) != 3:
            return JsonResponse({'error': 'invalid traffic-light mission'}, status=400)
        answers = data.get('answer')
        if not isinstance(answers, list) or len(answers) != len(statements):
            return JsonResponse({'error': 'all traffic-light answers are required'}, status=400)
        allowed_colors = {'green', 'yellow', 'red'}
        if any(answer not in allowed_colors for answer in answers):
            return JsonResponse({'error': 'invalid traffic-light answer'}, status=400)
        expected_colors = [statement.get('correct_color') for statement in statements]
        correct_count = sum(answer == expected for answer, expected in zip(answers, expected_colors))
        score = max_points * correct_count // len(statements)
        stored_answer = {'selected_colors': answers}
        result_details = {
            'correct_count': correct_count,
            'total_count': len(statements),
            'correct_colors': expected_colors,
            'item_correct': [answer == expected for answer, expected in zip(answers, expected_colors)],
        }
    elif mission.mission_type == Mission.TYPE_PROMPT_RANKING:
        options = content.get('options', [])
        raw_order = data.get('answer')
        try:
            selected_order = [int(index) for index in raw_order]
        except (TypeError, ValueError):
            return JsonResponse({'error': 'ranking required'}, status=400)
        if sorted(selected_order) != list(range(len(options))):
            return JsonResponse({'error': 'ranking must contain every prompt exactly once'}, status=400)
        score = max_points if selected_order == content.get('correct_order', []) else 0
        stored_answer = {'selected_order': selected_order}
        result_details = {'correct_order': content.get('correct_order', [])}
    else:
        options = content.get('options', [])
        try:
            if mission.mission_type == Mission.TYPE_MULTIPLE_CHOICE:
                raw_answers = data.get('answer')
                if not isinstance(raw_answers, list):
                    raise ValueError
                selected_indices = sorted({int(index) for index in raw_answers})
            else:
                selected_indices = [int(data.get('answer'))]
        except (TypeError, ValueError):
            return JsonResponse({'error': 'answer required'}, status=400)
        if not selected_indices or any(index < 0 or index >= len(options) for index in selected_indices):
            return JsonResponse({'error': 'invalid answer'}, status=400)

        expected_indices = sorted(correct_indices(content))
        score = max_points if selected_indices == expected_indices else 0
        stored_answer = {'selected_indices': selected_indices}
        result_details = {'correct_indices': expected_indices}
    ensure_profile(request.user)
    try:
        with transaction.atomic():
            profile = Profile.objects.select_for_update().get(user=request.user)
            attempt = MissionAttempt.objects.create(
                user=request.user,
                mission=mission,
                answer=stored_answer,
                score=score,
                max_points=max_points,
                difficulty=difficulty,
            )
            profile.progress_updated_at = attempt.completed_at
            profile.save(update_fields=['progress_updated_at'])
            if difficulty is not None:
                skill_change, skill_progression = evaluate_skill_progression(profile)
            else:
                skill_change = None
                skill_progression = progression_snapshot(profile)
    except IntegrityError:
        return JsonResponse({'error': 'mission already completed'}, status=409)
    return JsonResponse({
        'result': {
            'correct': score == max_points,
            'score': score,
            'max_points': max_points,
            **result_details,
        },
        'mission': mission_payload(mission, request.user, language),
        'progress': progress_payload(profile),
        'skill_change': skill_change,
        'skill_progression': skill_progression,
    })


@require_http_methods(['GET'])
def daily_missions_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = request.GET.get('lang', 'de')
    today = timezone.localdate()
    if is_business_day(today):
        mission = Mission.objects.filter(
            scheduled_date=today,
            status=Mission.STATUS_PUBLISHED,
        ).prefetch_related('attempts').order_by('created_at', 'id').first()
        missions = [mission] if mission is not None else []
    else:
        missions = []
    return JsonResponse({
        'date': today.isoformat(),
        'missions': [
            mission_payload(mission, request.user, language, create_assignment=True)
            for mission in missions
        ],
        'can_create': can_create_missions(request.user),
    })


@require_http_methods(['GET'])
def available_missions_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = request.GET.get('lang', 'de')
    today = timezone.localdate()
    available_from = mission_availability_start()
    attempted_ids = set(MissionAttempt.objects.filter(user=request.user).values_list('mission_id', flat=True))
    candidates = Mission.objects.filter(
        scheduled_date__gte=available_from,
        scheduled_date__lt=today,
        status=Mission.STATUS_PUBLISHED,
    ).prefetch_related('attempts').order_by('-scheduled_date', 'created_at', 'id')
    missions = []
    seen_dates = set()
    for mission in candidates:
        if mission.scheduled_date in seen_dates:
            continue
        seen_dates.add(mission.scheduled_date)
        if mission.id not in attempted_ids and mission_is_available(mission):
            missions.append(mission)
    return JsonResponse({
        'from': available_from.isoformat(),
        'to': (today - timedelta(days=1)).isoformat(),
        'missions': [
            mission_payload(mission, request.user, language, create_assignment=True)
            for mission in missions
        ],
        'can_create': can_create_missions(request.user),
    })


@require_http_methods(['GET'])
def mission_archive_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = 'en' if request.GET.get('lang') == 'en' else 'de'
    date_from = parse_iso_date(request.GET.get('from')) if request.GET.get('from') else None
    date_to = parse_iso_date(request.GET.get('to')) if request.GET.get('to') else None
    mission_type = request.GET.get('type')

    if request.GET.get('from') and date_from is None:
        return JsonResponse({'error': 'from must be a valid ISO date'}, status=400)
    if request.GET.get('to') and date_to is None:
        return JsonResponse({'error': 'to must be a valid ISO date'}, status=400)
    if date_from and date_to and date_to < date_from:
        return JsonResponse({'error': 'to must be on or after from'}, status=400)
    if mission_type and mission_type not in {choice for choice, _ in Mission.TYPE_CHOICES}:
        return JsonResponse({'error': 'unsupported mission type'}, status=400)

    attempted_ids = MissionAttempt.objects.filter(user=request.user).values_list('mission_id', flat=True)
    missions = Mission.objects.filter(
        id__in=attempted_ids,
        status=Mission.STATUS_PUBLISHED,
    ).prefetch_related(Prefetch(
        'attempts',
        queryset=MissionAttempt.objects.filter(user=request.user),
        to_attr='user_attempts',
    ))
    if date_from:
        missions = missions.filter(scheduled_date__gte=date_from)
    if date_to:
        missions = missions.filter(scheduled_date__lte=date_to)
    if mission_type:
        missions = missions.filter(mission_type=mission_type)

    return JsonResponse({
        'missions': [mission_archive_payload(mission, request.user, language) for mission in missions],
    })


@require_http_methods(['GET', 'POST'])
@csrf_exempt
def mission_schedule_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)

    if request.method == 'GET':
        date_from = parse_iso_date(request.GET.get('from'))
        date_to = parse_iso_date(request.GET.get('to'))
        if not date_from or not date_to or date_to < date_from:
            return JsonResponse({'error': 'valid date range required'}, status=400)
        missions = Mission.objects.filter(
            scheduled_date__range=(date_from, date_to),
        ).exclude(status=Mission.STATUS_REJECTED).prefetch_related('attempts')
        dates = {}
        scheduled_missions = {}
        for mission in missions:
            key = mission.scheduled_date.isoformat()
            dates[key] = dates.get(key, 0) + 1
            scheduled_missions.setdefault(key, []).append(mission_schedule_payload(mission, request.user))
        return JsonResponse({'dates': dates, 'missions': scheduled_missions})

    values, validation_error = validate_manual_mission_data(parse_json(request))
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    with transaction.atomic():
        existing = Mission.objects.select_for_update().filter(
            scheduled_date=values['scheduled_date'],
        ).exclude(status=Mission.STATUS_REJECTED)
        if existing.exists():
            return JsonResponse({'error': 'this date already has a mission'}, status=409)
        mission = Mission.objects.create(
            status=Mission.STATUS_PUBLISHED,
            created_by=request.user,
            **values,
        )
        transaction.on_commit(lambda: send_published_mission_email(mission))
    return JsonResponse({'mission': mission_payload(mission, request.user)}, status=201)


@require_http_methods(['PATCH', 'DELETE'])
@csrf_exempt
def mission_detail_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)

    mission = Mission.objects.filter(id=mission_id).first()
    if mission is None:
        return JsonResponse({'error': 'mission not found'}, status=404)
    if request.method == 'PATCH':
        if mission.attempts.exists():
            return JsonResponse({'error': 'completed missions cannot be edited'}, status=409)
        data = parse_json(request)
        validator = validate_manual_mission_data if 'variants' in data else validate_choice_mission_data
        values, validation_error = validator(data, allow_past_date=True)
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)
        with transaction.atomic():
            date_missions = Mission.objects.select_for_update().filter(
                scheduled_date=values['scheduled_date'],
            ).exclude(id=mission.id).exclude(status=Mission.STATUS_REJECTED)
            if date_missions.exists():
                return JsonResponse({'error': 'this date already has a mission'}, status=409)
            for field, value in values.items():
                setattr(mission, field, value)
            mission.save()
        return JsonResponse({'mission': mission_schedule_payload(mission, request.user)})
    if mission.attempts.exists():
        return JsonResponse({'error': 'completed missions cannot be deleted'}, status=409)

    mission.delete()
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def mission_review_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    missions = Mission.objects.filter(status=Mission.STATUS_REVIEW).prefetch_related('attempts')
    week_start = parse_iso_date(request.GET.get('week_start'))
    if request.GET.get('week_start') and week_start is None:
        return JsonResponse({'error': 'week_start must be a valid ISO date'}, status=400)
    if week_start is not None:
        missions = missions.filter(scheduled_date__range=(week_start, week_start + timedelta(days=6)))
    return JsonResponse({'missions': [mission_schedule_payload(mission, request.user) for mission in missions]})


@require_http_methods(['POST'])
@csrf_exempt
def approve_all_review_missions_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    data = parse_json(request)
    week_start = parse_iso_date(data.get('week_start'))
    if data.get('week_start') and week_start is None:
        return JsonResponse({'error': 'week_start must be a valid ISO date'}, status=400)
    with transaction.atomic():
        review_query = Mission.objects.select_for_update().filter(status=Mission.STATUS_REVIEW)
        if week_start is not None:
            review_query = review_query.filter(scheduled_date__range=(week_start, week_start + timedelta(days=6)))
        review_missions = list(
            review_query
        )
        review_counts = {}
        for mission in review_missions:
            review_counts[mission.scheduled_date] = review_counts.get(mission.scheduled_date, 0) + 1
        for scheduled_date, review_count in review_counts.items():
            published_count = Mission.objects.filter(
                scheduled_date=scheduled_date,
                status=Mission.STATUS_PUBLISHED,
            ).count()
            if published_count + review_count > 1:
                return JsonResponse({
                    'error': f'{scheduled_date.isoformat()} would have more than one published mission',
                }, status=409)
        reviewed_at = timezone.now()
        mission_ids = [mission.id for mission in review_missions]
        Mission.objects.filter(id__in=mission_ids).update(
            status=Mission.STATUS_PUBLISHED,
            reviewed_by=request.user,
            reviewed_at=reviewed_at,
        )
        for mission in review_missions:
            mission.status = Mission.STATUS_PUBLISHED
            mission.reviewed_by = request.user
            mission.reviewed_at = reviewed_at
        transaction.on_commit(lambda: send_published_mission_emails(review_missions))
    return JsonResponse({'approved_count': len(review_missions)})


@require_http_methods(['POST'])
@csrf_exempt
def reject_all_review_missions_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    data = parse_json(request)
    week_start = parse_iso_date(data.get('week_start'))
    if data.get('week_start') and week_start is None:
        return JsonResponse({'error': 'week_start must be a valid ISO date'}, status=400)
    with transaction.atomic():
        review_missions = Mission.objects.select_for_update().filter(status=Mission.STATUS_REVIEW)
        if week_start is not None:
            review_missions = review_missions.filter(scheduled_date__range=(week_start, week_start + timedelta(days=6)))
        rejected_count = review_missions.count()
        review_missions.update(
            status=Mission.STATUS_REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
    return JsonResponse({'rejected_count': rejected_count})


@require_http_methods(['POST'])
def generate_next_week_missions_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    data = parse_json(request)
    force = data.get('force', False)
    if not isinstance(force, bool):
        return JsonResponse({'error': 'force must be true or false'}, status=400)
    raw_week_start = data.get('week_start')
    week_start = parse_iso_date(raw_week_start) if raw_week_start else None
    if raw_week_start and week_start is None:
        return JsonResponse({'error': 'week_start must be a valid ISO date'}, status=400)
    today = timezone.localdate()
    current_week_start = today - timedelta(days=today.weekday())
    if week_start is not None and (week_start.weekday() != 0 or week_start < current_week_start):
        return JsonResponse({'error': 'week_start must be the current or a future Monday'}, status=400)
    run = create_weekly_run(request.user, force=force, week_start=week_start)
    return dispatch_generation_response(run)


@require_http_methods(['POST'])
def generate_task_challenge_view(request):
    """Content creators generate a single task challenge of a chosen type.

    The mission is created in review status so it flows through the normal
    approval pipeline before it becomes visible to learners.
    """
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    data = parse_json(request)
    mission_type = data.get('mission_type') or None
    if mission_type is not None and mission_type not in TASK_CHALLENGE_TYPES:
        return JsonResponse({'error': 'unsupported task challenge type'}, status=400)
    scheduled_date = parse_iso_date(data.get('scheduled_date')) if data.get('scheduled_date') else timezone.localdate()
    if data.get('scheduled_date') and scheduled_date is None:
        return JsonResponse({'error': 'scheduled_date must be a valid ISO date'}, status=400)
    if Mission.objects.filter(
        scheduled_date=scheduled_date,
        status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
    ).exists():
        return JsonResponse({'error': 'this date already has a mission'}, status=409)
    run = create_scheduled_task_run(request.user, scheduled_date, mission_type)
    return dispatch_generation_response(run)


@require_http_methods(['GET'])
def current_weekly_generation_run_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    run = GenerationRun.objects.prefetch_related('missions').filter(
        requested_by=request.user,
        kind=GenerationRun.KIND_WEEKLY_MISSIONS,
        status__in=GenerationRun.ACTIVE_STATUSES,
    ).order_by('-created_at').first()
    return JsonResponse({
        'generation_run': generation_run_payload(run) if run is not None else None,
    })


@require_http_methods(['GET'])
def generation_run_detail_view(request, run_id):
    run = GenerationRun.objects.prefetch_related('missions').filter(id=run_id).first()
    if run is None:
        return JsonResponse({'error': 'generation run not found'}, status=404)
    if not can_access_generation_run(request.user, run):
        return JsonResponse({'error': 'permission denied'}, status=403)
    return JsonResponse({'generation_run': generation_run_payload(run)})


@require_http_methods(['POST'])
def retry_generation_run_view(request, run_id):
    run = GenerationRun.objects.filter(id=run_id).first()
    if run is None:
        return JsonResponse({'error': 'generation run not found'}, status=404)
    if not can_access_generation_run(request.user, run):
        return JsonResponse({'error': 'permission denied'}, status=403)
    if run.status != GenerationRun.STATUS_FAILED:
        return JsonResponse({'error': 'only failed generation runs can be retried'}, status=409)
    return dispatch_generation_response(run)


@require_http_methods(['POST'])
def generate_training_mission_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    mission_type = parse_json(request).get('type')
    try:
        run = create_training_choice_run(request.user, mission_type)
    except GenerationContractError as error_value:
        return JsonResponse({'error': str(error_value)}, status=400)
    return dispatch_generation_response(run)


def public_training_choice(candidate, user):
    difficulty = difficulty_for_skill(ensure_profile(user).skill_level)
    variant = candidate.get('variants', {}).get(difficulty, candidate)
    content = variant['content']
    return {
        'type': candidate['mission_type'],
        'difficulty': difficulty,
        'title_de': variant['title_de'],
        'title_en': variant['title_en'],
        'description_de': variant['description_de'],
        'description_en': variant['description_en'],
        'question_de': translated(content.get('question', {}), 'de'),
        'question_en': translated(content.get('question', {}), 'en'),
        'options': content.get('options', []),
        'statements': content.get('statements', []),
        'feedback_de': translated(content.get('feedback', {}), 'de'),
        'feedback_en': translated(content.get('feedback', {}), 'en'),
        'micro_learning_de': translated(content.get('micro_learning', {}), 'de'),
        'micro_learning_en': translated(content.get('micro_learning', {}), 'en'),
        'test_solution': {
            'correct_indices': correct_indices(content),
            'correct_order': content.get('correct_order', []),
            'correct_colors': [statement.get('correct_color') for statement in content.get('statements', [])],
            'feedback_de': [translated(statement.get('feedback', {}), 'de') for statement in content.get('statements', [])],
            'feedback_en': [translated(statement.get('feedback', {}), 'en') for statement in content.get('statements', [])],
        },
    }


def training_challenges(request):
    return dict(request.session.get('training_chat_challenges', {}))


def public_chat_challenge(challenge, challenge_id):
    return {
        'id': challenge_id,
        'type': challenge['type'],
        'title_de': challenge['title_de'],
        'title_en': challenge['title_en'],
        'description_de': challenge['description_de'],
        'description_en': challenge['description_en'],
        'task_de': challenge['task_de'],
        'task_en': challenge['task_en'],
        'case_data_de': challenge['case_data_de'],
        'case_data_en': challenge['case_data_en'],
        'final_questions': [
            {
                key: value for key, value in question.items()
                if key not in {'solution', 'tolerance', 'feedback_de', 'feedback_en'}
            }
            for question in challenge['final_questions']
        ],
    }


@require_http_methods(['POST'])
def generate_training_chat_challenge_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    return dispatch_generation_response(create_training_chat_run(request.user))

@require_http_methods(['POST'])
@csrf_exempt
def training_chat_message_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    data = parse_json(request)
    challenge_id = str(data.get('challenge_id', ''))
    message = str(data.get('message', '')).strip()
    challenges = training_challenges(request)
    challenge = challenges.get(challenge_id)
    if challenge is None:
        return JsonResponse({'error': 'training challenge not found'}, status=404)
    if not message:
        return JsonResponse({'error': 'message required'}, status=400)
    if challenge.get('prompt_count', 0) >= 3:
        return JsonResponse({'error': 'maximum of three chat prompts reached'}, status=409)
    language = 'en' if data.get('language') == 'en' else 'de'
    try:
        reply = chat_reply(challenge, challenge.get('history', []), message, language)
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=503)
    challenge['history'] = [
        *challenge.get('history', []),
        {'role': 'user', 'content': message},
        {'role': 'assistant', 'content': reply},
    ]
    challenge['prompt_count'] = challenge.get('prompt_count', 0) + 1
    challenges[challenge_id] = challenge
    request.session['training_chat_challenges'] = challenges
    request.session.modified = True
    return JsonResponse({'reply': reply, 'remaining_prompts': 3 - challenge['prompt_count']})


@require_http_methods(['POST'])
@csrf_exempt
def submit_training_chat_challenge_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    data = parse_json(request)
    challenge_id = str(data.get('challenge_id', ''))
    challenges = training_challenges(request)
    challenge = challenges.get(challenge_id)
    if challenge is None:
        return JsonResponse({'error': 'training challenge not found'}, status=404)
    answers = data.get('answers')
    if not isinstance(answers, dict):
        return JsonResponse({'error': 'final answers required'}, status=400)
    result = evaluate_final_answers(challenge, answers, data.get('language'))
    challenges.pop(challenge_id, None)
    request.session['training_chat_challenges'] = challenges
    request.session.modified = True
    return JsonResponse({'result': result})


def training_task_challenges(request):
    return dict(request.session.get('training_task_challenges', {}))


def public_task_challenge(candidate, challenge_id):
    content = candidate['content']
    return {
        'id': challenge_id,
        'type': candidate['mission_type'],
        'title_de': candidate['title_de'],
        'title_en': candidate['title_en'],
        'description_de': candidate['description_de'],
        'description_en': candidate['description_en'],
        'task_de': content['task']['de'],
        'task_en': content['task']['en'],
        'case_data_de': content['case_data']['de'],
        'case_data_en': content['case_data']['en'],
        'case_format': content.get('case_format', 'table'),
        'result_fields': [
            {
                'id': field['id'],
                'type': field['type'],
                'label_de': field['label']['de'],
                'label_en': field['label']['en'],
                'unit': field.get('unit', ''),
            }
            for field in content['result_fields']
        ],
        'micro_learning_de': content['micro_learning']['de'],
        'micro_learning_en': content['micro_learning']['en'],
    }


@require_http_methods(['POST'])
def consume_training_generation_view(request, run_id):
    run = GenerationRun.objects.filter(id=run_id).first()
    if run is None:
        return JsonResponse({'error': 'generation run not found'}, status=404)
    if not request.user.is_authenticated or run.requested_by_id != request.user.id:
        return JsonResponse({'error': 'permission denied'}, status=403)
    if run.status != GenerationRun.STATUS_COMPLETED:
        return JsonResponse({'error': 'generation run is not completed'}, status=409)
    if run.kind not in {
        GenerationRun.KIND_TRAINING_CHOICE,
        GenerationRun.KIND_TRAINING_TASK,
        GenerationRun.KIND_TRAINING_CHAT,
    }:
        return JsonResponse({'error': 'generation run is not a training run'}, status=400)
    if not isinstance(run.result_payload, dict) or not run.result_payload:
        return JsonResponse({'error': 'generation result is unavailable'}, status=409)
    candidate = next(iter(run.result_payload.values()))

    if run.kind == GenerationRun.KIND_TRAINING_CHOICE:
        mission = public_training_choice(candidate, request.user)
    elif run.kind == GenerationRun.KIND_TRAINING_TASK:
        challenge_id = run.id.hex
        challenges = training_task_challenges(request)
        challenges.setdefault(challenge_id, candidate)
        request.session['training_task_challenges'] = challenges
        request.session.modified = True
        mission = public_task_challenge(challenges[challenge_id], challenge_id)
    else:
        challenge_id = run.id.hex
        challenges = training_challenges(request)
        if challenge_id not in challenges:
            candidate['history'] = []
            candidate['prompt_count'] = 0
            challenges[challenge_id] = candidate
        request.session['training_chat_challenges'] = challenges
        request.session.modified = True
        mission = public_chat_challenge(challenges[challenge_id], challenge_id)
    return JsonResponse({'mission': mission})


@require_http_methods(['POST'])
def generate_training_task_challenge_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    mission_type = parse_json(request).get('mission_type') or None
    if mission_type is not None and mission_type not in TASK_CHALLENGE_TYPES:
        return JsonResponse({'error': 'unsupported task challenge type'}, status=400)
    difficulty = difficulty_for_skill(ensure_profile(request.user).skill_level)
    try:
        run = create_training_task_run(request.user, mission_type, difficulty)
    except GenerationContractError as error_value:
        return JsonResponse({'error': str(error_value)}, status=400)
    return dispatch_generation_response(run)


@require_http_methods(['POST'])
@csrf_exempt
def submit_training_task_challenge_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    data = parse_json(request)
    challenge_id = str(data.get('challenge_id', ''))
    challenges = training_task_challenges(request)
    candidate = challenges.get(challenge_id)
    if candidate is None:
        return JsonResponse({'error': 'training challenge not found'}, status=404)
    values = data.get('values')
    if not isinstance(values, dict):
        return JsonResponse({'error': 'result values required'}, status=400)
    evaluation = evaluate_task_answers(candidate['content'], values, data.get('language'))
    challenges.pop(challenge_id, None)
    request.session['training_task_challenges'] = challenges
    request.session.modified = True
    return JsonResponse({'result': {
        'correct': evaluation['all_correct'],
        'correct_count': evaluation['correct_count'],
        'total_count': evaluation['total_count'],
        'field_results': evaluation['field_results'],
    }})


def agent_chat_summary(chat):
    return {
        'id': chat.id,
        'title': chat.title,
        'updated_at': chat.updated_at.isoformat(),
        'created_at': chat.created_at.isoformat(),
    }


def agent_chat_payload(chat):
    return {
        **agent_chat_summary(chat),
        'messages': chat.messages if isinstance(chat.messages, list) else [],
    }


def agent_chat_title(message):
    title = ' '.join(str(message).strip().split())
    if not title:
        return ''
    return title[:80]


@require_http_methods(['GET', 'POST'])
@csrf_exempt
def personal_agent_chats_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    if request.method == 'GET':
        chats = AgentChat.objects.filter(user=request.user)[:50]
        return JsonResponse({'chats': [agent_chat_summary(chat) for chat in chats]})
    data = parse_json(request)
    title = agent_chat_title(data.get('title') or '')
    chat = AgentChat.objects.create(user=request.user, title=title, messages=[])
    return JsonResponse({'chat': agent_chat_payload(chat)}, status=201)


@require_http_methods(['GET', 'DELETE'])
@csrf_exempt
def personal_agent_chat_detail_view(request, chat_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    chat = AgentChat.objects.filter(id=chat_id, user=request.user).first()
    if chat is None:
        return JsonResponse({'error': 'chat not found'}, status=404)
    if request.method == 'DELETE':
        chat.delete()
        return JsonResponse({'deleted': True})
    return JsonResponse({'chat': agent_chat_payload(chat)})


@require_http_methods(['POST'])
@csrf_exempt
def personal_agent_chat_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    data = parse_json(request)
    language = 'en' if data.get('language') == 'en' else 'de'
    try:
        reply = personal_agent_reply(data.get('messages'), language)
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=400)
    return JsonResponse({'reply': reply})


@require_http_methods(['POST'])
@csrf_exempt
def personal_agent_chat_message_view(request, chat_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    chat = AgentChat.objects.filter(id=chat_id, user=request.user).first()
    if chat is None:
        return JsonResponse({'error': 'chat not found'}, status=404)
    data = parse_json(request)
    message = str(data.get('message', '')).strip()
    if not message:
        return JsonResponse({'error': 'message required'}, status=400)
    messages = chat.messages if isinstance(chat.messages, list) else []
    next_messages = [*messages, {'role': 'user', 'content': message}]
    language = 'en' if data.get('language') == 'en' else 'de'
    try:
        reply = personal_agent_reply(next_messages, language)
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=400)
    next_messages.append({'role': 'assistant', 'content': reply})
    chat.messages = next_messages
    if not chat.title:
        chat.title = agent_chat_title(message)
    chat.save(update_fields=['messages', 'title', 'updated_at'])
    return JsonResponse({'chat': agent_chat_payload(chat), 'reply': reply})


@require_http_methods(['POST'])
@csrf_exempt
def approve_mission_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    with transaction.atomic():
        mission = Mission.objects.select_for_update().filter(id=mission_id, status=Mission.STATUS_REVIEW).first()
        if mission is None:
            return JsonResponse({'error': 'review mission not found'}, status=404)
        published_count = Mission.objects.filter(
            scheduled_date=mission.scheduled_date,
            status=Mission.STATUS_PUBLISHED,
        ).count()
        if published_count >= 1:
            return JsonResponse({'error': 'this date already has a published mission'}, status=409)
        mission.status = Mission.STATUS_PUBLISHED
        mission.reviewed_by = request.user
        mission.reviewed_at = timezone.now()
        mission.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        transaction.on_commit(lambda: send_published_mission_email(mission))
    return JsonResponse({'mission': mission_schedule_payload(mission, request.user)})


@require_http_methods(['POST'])
def regenerate_mission_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    mission = Mission.objects.filter(id=mission_id).first()
    if mission is None:
        return JsonResponse({'error': 'mission not found'}, status=404)
    try:
        run = create_regeneration_run(request.user, mission)
    except GenerationContractError as error_value:
        return JsonResponse({'error': str(error_value)}, status=400)
    return dispatch_generation_response(run)


@require_http_methods(['POST'])
@csrf_exempt
def reject_mission_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    mission = Mission.objects.filter(id=mission_id, status=Mission.STATUS_REVIEW).first()
    if mission is None:
        return JsonResponse({'error': 'review mission not found'}, status=404)
    mission.status = Mission.STATUS_REJECTED
    mission.reviewed_by = request.user
    mission.reviewed_at = timezone.now()
    mission.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def leaderboard_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    archive_completed_weeks()
    requested_difficulty = request.GET.get('difficulty')
    difficulty = requested_difficulty or difficulty_for_skill(ensure_profile(request.user).skill_level)
    if difficulty not in VALID_DIFFICULTIES:
        return JsonResponse({'error': 'invalid difficulty'}, status=400)
    entries = []
    users = User.objects.select_related('profile').order_by('first_name', 'last_name', 'username')
    for user in users:
        profile = ensure_profile(user)
        attempts = MissionAttempt.objects.filter(user=user, difficulty=difficulty)
        points = sum(attempts.values_list('score', flat=True))
        completed = attempts.count()
        if points <= 0:
            continue
        streaks = streak_payload(user)
        entries.append({
            **user_identity(user),
            'total_points': points,
            'completed_missions': completed,
            'level': level_for_points(points),
            'skill_level': profile.skill_level,
            'current_streak': streaks['current_streak'],
            'max_streak': streaks['max_streak'],
        })

    current_week_start, current_week_end = week_bounds()
    history = list(WeeklyLeaderboardSnapshot.objects.filter(difficulty=difficulty).values('week_start', 'week_end'))
    return JsonResponse({
        'difficulty': difficulty,
        'entries': rank_entries(entries),
        'weekly_entries': weekly_leaderboard_entries(current_week_start, current_week_end, difficulty),
        'week_start': current_week_start.isoformat(),
        'week_end': current_week_end.isoformat(),
        'history': [
            {'week_start': item['week_start'].isoformat(), 'week_end': item['week_end'].isoformat()}
            for item in history
        ],
    })


@require_http_methods(['GET'])
def leaderboard_history_view(request, week_start):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    parsed_start = parse_iso_date(week_start)
    difficulty = request.GET.get('difficulty') or difficulty_for_skill(ensure_profile(request.user).skill_level)
    if difficulty not in VALID_DIFFICULTIES:
        return JsonResponse({'error': 'invalid difficulty'}, status=400)
    snapshot = WeeklyLeaderboardSnapshot.objects.filter(
        week_start=parsed_start,
        difficulty=difficulty,
    ).first()
    if snapshot is None:
        return JsonResponse({'error': 'leaderboard snapshot not found'}, status=404)
    entries = [
        entry.copy()
        for entry in snapshot.entries
        if entry.get('total_points', 0) > 0
    ]
    return JsonResponse({
        'week_start': snapshot.week_start.isoformat(),
        'week_end': snapshot.week_end.isoformat(),
        'difficulty': difficulty,
        'entries': rank_entries(entries),
    })
