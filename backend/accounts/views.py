import json
import os
import uuid
from datetime import date, timedelta

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import AgentChat, Mission, MissionAttempt, Profile, WeeklyLeaderboardSnapshot
from .services.ai_mission_generator import (
    AiMissionGenerationError,
    generate_training_candidate,
    generate_next_week,
    regenerate_review_mission,
)
from .services.ai_chat_challenge import chat_reply, evaluate_final_answers, generate_chat_challenge
from .services.email_notifications import send_published_mission_email, send_published_mission_emails
from .services.personal_agent import personal_agent_reply


User = get_user_model()
VALID_ROLES = {choice for choice, _ in Profile.ROLE_CHOICES}


def parse_json(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return {}


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
    ).values_list('id', 'scheduled_date'):
        missions_by_date.setdefault(scheduled_date, set()).add(mission_id)

    attempted_ids = set(
        MissionAttempt.objects.filter(user=user).values_list('mission_id', flat=True)
    )
    completed_dates = {
        scheduled_date
        for scheduled_date, mission_ids in missions_by_date.items()
        if len(mission_ids) >= 2 and mission_ids.issubset(attempted_ids)
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


def weekly_leaderboard_entries(week_start, week_end):
    users = User.objects.order_by('first_name', 'last_name', 'username')
    entries = []
    for user in users:
        attempts = MissionAttempt.objects.filter(
            user=user,
            completed_at__date__range=(week_start, week_end),
        )
        points = sum(attempts.values_list('score', flat=True))
        completed = attempts.count()
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
            WeeklyLeaderboardSnapshot.objects.get_or_create(
                week_start=candidate_start,
                defaults={
                    'week_end': candidate_end,
                    'entries': weekly_leaderboard_entries(candidate_start, candidate_end),
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


def mission_payload(mission, user, language='de', include_content=True):
    attempt = user_mission_attempt(mission, user)
    content = mission.content or {}
    payload = {
        'id': mission.id,
        'type': mission.mission_type,
        'scheduled_date': mission.scheduled_date.isoformat(),
        'title': mission.title_en if language == 'en' else mission.title_de,
        'description': mission.description_en if language == 'en' else mission.description_de,
        'max_points': mission.max_points,
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
            'max_points': mission.max_points,
            'correct': attempt.score == mission.max_points,
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
        'question_de': translated(content.get('question', {}), 'de'),
        'question_en': translated(content.get('question', {}), 'en'),
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


def validate_choice_mission_data(data, allow_past_date=False):
    scheduled_date = parse_iso_date(data.get('scheduled_date'))
    mission_type = data.get('type')
    allowed_types = {
        Mission.TYPE_SINGLE_CHOICE,
        Mission.TYPE_MULTIPLE_CHOICE,
        Mission.TYPE_PROMPT_SELECTION,
        Mission.TYPE_PROMPT_RANKING,
        Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT,
    }
    if not scheduled_date or (not allow_past_date and scheduled_date < timezone.localdate()):
        return None, 'scheduled date must be today or later'
    if mission_type not in allowed_types:
        return None, 'unsupported mission type'

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
def user_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'user': user_payload(request.user)})


@require_http_methods(['GET'])
def users_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
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
    if role and role not in VALID_ROLES:
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
        scheduled_date=timezone.localdate(),
        status=Mission.STATUS_PUBLISHED,
    ).first()
    if mission is None:
        return JsonResponse({'error': 'mission not available today'}, status=404)
    if MissionAttempt.objects.filter(user=request.user, mission=mission).exists():
        return JsonResponse({'error': 'mission already completed'}, status=409)

    if mission.mission_type not in Mission.CHOICE_TYPES:
        return JsonResponse({'error': 'unsupported mission type'}, status=400)

    content = mission.content or {}
    if mission.mission_type == Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT:
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
        score = mission.max_points * correct_count // len(statements)
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
        score = mission.max_points if selected_order == content.get('correct_order', []) else 0
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
        score = mission.max_points if selected_indices == expected_indices else 0
        stored_answer = {'selected_indices': selected_indices}
        result_details = {'correct_indices': expected_indices}
    try:
        attempt = MissionAttempt.objects.create(
            user=request.user,
            mission=mission,
            answer=stored_answer,
            score=score,
        )
    except IntegrityError:
        return JsonResponse({'error': 'mission already completed'}, status=409)

    profile = ensure_profile(request.user)
    profile.progress_updated_at = attempt.completed_at
    profile.save(update_fields=['progress_updated_at'])
    return JsonResponse({
        'result': {
            'correct': score == mission.max_points,
            'score': score,
            'max_points': mission.max_points,
            **result_details,
        },
        'mission': mission_payload(mission, request.user, language),
        'progress': progress_payload(profile),
    })


@require_http_methods(['GET'])
def daily_missions_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = request.GET.get('lang', 'de')
    today = timezone.localdate()
    missions = Mission.objects.filter(
        scheduled_date=today,
        status=Mission.STATUS_PUBLISHED,
    ).prefetch_related('attempts')[:2]
    return JsonResponse({
        'date': today.isoformat(),
        'missions': [mission_payload(mission, request.user, language) for mission in missions],
        'can_create': can_create_missions(request.user),
    })


@require_http_methods(['GET'])
def mission_archive_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = 'en' if request.GET.get('lang') == 'en' else 'de'
    today = timezone.localdate()
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
        scheduled_date__lt=today,
        status=Mission.STATUS_PUBLISHED,
    ).prefetch_related(Prefetch(
        'attempts',
        queryset=MissionAttempt.objects.filter(user=request.user),
        to_attr='user_attempts',
    ))
    if date_from:
        missions = missions.filter(scheduled_date__gte=date_from)
    if date_to:
        missions = missions.filter(scheduled_date__lte=min(date_to, today - timedelta(days=1)))
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

    values, validation_error = validate_choice_mission_data(parse_json(request))
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    with transaction.atomic():
        existing = Mission.objects.select_for_update().filter(
            scheduled_date=values['scheduled_date'],
        ).exclude(status=Mission.STATUS_REJECTED)
        if existing.count() >= 2:
            return JsonResponse({'error': 'this date already has two missions'}, status=409)
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
        values, validation_error = validate_choice_mission_data(parse_json(request), allow_past_date=True)
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)
        with transaction.atomic():
            date_missions = Mission.objects.select_for_update().filter(
                scheduled_date=values['scheduled_date'],
            ).exclude(id=mission.id).exclude(status=Mission.STATUS_REJECTED)
            if date_missions.count() >= 2:
                return JsonResponse({'error': 'this date already has two missions'}, status=409)
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
            if published_count + review_count > 2:
                return JsonResponse({
                    'error': f'{scheduled_date.isoformat()} would have more than two published missions',
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
@csrf_exempt
def generate_next_week_missions_view(request):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    data = parse_json(request)
    force = bool(data.get('force', False))
    raw_week_start = data.get('week_start')
    week_start = parse_iso_date(raw_week_start) if raw_week_start else None
    if raw_week_start and week_start is None:
        return JsonResponse({'error': 'week_start must be a valid ISO date'}, status=400)
    today = timezone.localdate()
    current_week_start = today - timedelta(days=today.weekday())
    if week_start is not None and (week_start.weekday() != 0 or week_start < current_week_start):
        return JsonResponse({'error': 'week_start must be the current or a future Monday'}, status=400)
    try:
        missions, week_start, week_end = generate_next_week(
            request.user,
            force=force,
            week_start=week_start,
        )
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=503)
    return JsonResponse({
        'created_count': len(missions),
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'missions': [mission_schedule_payload(mission, request.user) for mission in missions],
    })


@require_http_methods(['POST'])
@csrf_exempt
def generate_training_mission_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    mission_type = parse_json(request).get('type')
    try:
        candidate = generate_training_candidate(mission_type)
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=503)

    content = candidate['content']
    payload = {
        'type': candidate['mission_type'],
        'title_de': candidate['title_de'],
        'title_en': candidate['title_en'],
        'description_de': candidate['description_de'],
        'description_en': candidate['description_en'],
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
    return JsonResponse({'mission': payload})


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
@csrf_exempt
def generate_training_chat_challenge_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)
    try:
        challenge = generate_chat_challenge()
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=503)
    challenge_id = uuid.uuid4().hex
    challenge['history'] = []
    challenge['prompt_count'] = 0
    challenges = training_challenges(request)
    challenges[challenge_id] = challenge
    request.session['training_chat_challenges'] = challenges
    request.session.modified = True
    return JsonResponse({'mission': public_chat_challenge(challenge, challenge_id)})

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
        if published_count >= 2:
            return JsonResponse({'error': 'this date already has two published missions'}, status=409)
        mission.status = Mission.STATUS_PUBLISHED
        mission.reviewed_by = request.user
        mission.reviewed_at = timezone.now()
        mission.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        transaction.on_commit(lambda: send_published_mission_email(mission))
    return JsonResponse({'mission': mission_schedule_payload(mission, request.user)})


@require_http_methods(['POST'])
@csrf_exempt
def regenerate_mission_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)
    mission = Mission.objects.filter(id=mission_id).first()
    if mission is None:
        return JsonResponse({'error': 'mission not found'}, status=404)
    try:
        mission = regenerate_review_mission(mission, request.user)
    except AiMissionGenerationError as error_value:
        return JsonResponse({'error': str(error_value)}, status=503)
    return JsonResponse({'mission': mission_schedule_payload(mission, request.user)})


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
    entries = []
    users = User.objects.select_related('profile').order_by('first_name', 'last_name', 'username')
    for user in users:
        profile = ensure_profile(user)
        progress = progress_payload(profile)
        entries.append({
            **user_identity(user),
            'total_points': progress['total_points'],
            'completed_missions': progress['completed_mission_count'],
            'level': progress['level'],
            'current_streak': progress['current_streak'],
            'max_streak': progress['max_streak'],
        })

    current_week_start, current_week_end = week_bounds()
    history = list(WeeklyLeaderboardSnapshot.objects.values('week_start', 'week_end'))
    return JsonResponse({
        'entries': rank_entries(entries),
        'weekly_entries': weekly_leaderboard_entries(current_week_start, current_week_end),
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
    snapshot = WeeklyLeaderboardSnapshot.objects.filter(week_start=parsed_start).first()
    if snapshot is None:
        return JsonResponse({'error': 'leaderboard snapshot not found'}, status=404)
    return JsonResponse({
        'week_start': snapshot.week_start.isoformat(),
        'week_end': snapshot.week_end.isoformat(),
        'entries': snapshot.entries,
    })
