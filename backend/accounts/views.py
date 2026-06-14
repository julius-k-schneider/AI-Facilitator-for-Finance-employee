import json
import os
from datetime import date

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Mission, MissionAttempt, Profile


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


def progress_payload(profile):
    scores = profile.mission_scores or {}
    attempts = MissionAttempt.objects.filter(user=profile.user)
    attempt_points = sum(attempts.values_list('score', flat=True))
    completed_attempts = attempts.count()
    legacy_completed = sum(1 for score in scores.values() if int(score) > 0)
    total_points = profile.total_points + attempt_points
    return {
        'mission_scores': scores,
        'completed_missions': [mission_id for mission_id, score in scores.items() if int(score) > 0],
        'completed_mission_count': legacy_completed + completed_attempts,
        'total_points': total_points,
        'level': level_for_points(total_points),
        'updated_at': profile.progress_updated_at.isoformat() if profile.progress_updated_at else None,
    }


def can_create_missions(user):
    if not user.is_authenticated:
        return False
    return ensure_profile(user).role in {Profile.ROLE_CONTENT_CREATOR, Profile.ROLE_ADMIN}


def translated(value, language):
    return value.get(language) or value.get('de') or value.get('en') or ''


def mission_payload(mission, user, language='de', include_content=True):
    attempt = mission.attempts.filter(user=user).first()
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
    if include_content and mission.mission_type == Mission.TYPE_SINGLE_CHOICE:
        payload['content'] = {
            'question': translated(content.get('question', {}), language),
            'options': [translated(option, language) for option in content.get('options', [])],
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
        'correct_index': content.get('correct_index'),
        'max_points': mission.max_points,
        'created_by': mission.created_by_id,
        'can_delete': is_admin(user) or mission.created_by_id == user.id,
        'has_attempts': mission.attempts.exists(),
    }


def parse_iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


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
    mission = Mission.objects.filter(id=data.get('mission_id'), scheduled_date=timezone.localdate()).first()
    if mission is None:
        return JsonResponse({'error': 'mission not available today'}, status=404)
    if MissionAttempt.objects.filter(user=request.user, mission=mission).exists():
        return JsonResponse({'error': 'mission already completed'}, status=409)

    if mission.mission_type != Mission.TYPE_SINGLE_CHOICE:
        return JsonResponse({'error': 'unsupported mission type'}, status=400)

    try:
        selected_index = int(data.get('answer'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'answer required'}, status=400)

    content = mission.content or {}
    options = content.get('options', [])
    if selected_index < 0 or selected_index >= len(options):
        return JsonResponse({'error': 'invalid answer'}, status=400)

    score = mission.max_points if selected_index == content.get('correct_index') else 0
    try:
        attempt = MissionAttempt.objects.create(
            user=request.user,
            mission=mission,
            answer={'selected_index': selected_index},
            score=score,
        )
    except IntegrityError:
        return JsonResponse({'error': 'mission already completed'}, status=409)

    profile = ensure_profile(request.user)
    profile.progress_updated_at = attempt.completed_at
    profile.save(update_fields=['progress_updated_at'])
    return JsonResponse({
        'result': {'correct': score > 0, 'score': score, 'max_points': mission.max_points},
        'mission': mission_payload(mission, request.user),
        'progress': progress_payload(profile),
    })


@require_http_methods(['GET'])
def daily_missions_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    language = request.GET.get('lang', 'de')
    today = timezone.localdate()
    missions = Mission.objects.filter(scheduled_date=today).prefetch_related('attempts')[:2]
    return JsonResponse({
        'date': today.isoformat(),
        'missions': [mission_payload(mission, request.user, language) for mission in missions],
        'can_create': can_create_missions(request.user),
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
        missions = Mission.objects.filter(scheduled_date__range=(date_from, date_to)).prefetch_related('attempts')
        dates = {}
        scheduled_missions = {}
        for mission in missions:
            key = mission.scheduled_date.isoformat()
            dates[key] = dates.get(key, 0) + 1
            scheduled_missions.setdefault(key, []).append(mission_schedule_payload(mission, request.user))
        return JsonResponse({'dates': dates, 'missions': scheduled_missions})

    data = parse_json(request)
    scheduled_date = parse_iso_date(data.get('scheduled_date'))
    mission_type = data.get('type')
    if not scheduled_date or scheduled_date < timezone.localdate():
        return JsonResponse({'error': 'scheduled date must be today or later'}, status=400)
    if mission_type != Mission.TYPE_SINGLE_CHOICE:
        return JsonResponse({'error': 'unsupported mission type'}, status=400)

    required_text = ('title_de', 'title_en', 'question_de', 'question_en')
    if any(not str(data.get(field, '')).strip() for field in required_text):
        return JsonResponse({'error': 'all bilingual text fields are required'}, status=400)

    options = data.get('options') or []
    if len(options) < 2 or any(not option.get('de', '').strip() or not option.get('en', '').strip() for option in options):
        return JsonResponse({'error': 'at least two bilingual options are required'}, status=400)
    try:
        correct_index = int(data.get('correct_index'))
        max_points = int(data.get('max_points', 100))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid correct answer or points'}, status=400)
    if correct_index < 0 or correct_index >= len(options) or max_points < 1 or max_points > 1000:
        return JsonResponse({'error': 'invalid correct answer or points'}, status=400)

    with transaction.atomic():
        existing = Mission.objects.select_for_update().filter(scheduled_date=scheduled_date)
        if existing.count() >= 2:
            return JsonResponse({'error': 'this date already has two missions'}, status=409)
        mission = Mission.objects.create(
            mission_type=mission_type,
            scheduled_date=scheduled_date,
            title_de=data['title_de'].strip(),
            title_en=data['title_en'].strip(),
            description_de=str(data.get('description_de', '')).strip(),
            description_en=str(data.get('description_en', '')).strip(),
            content={
                'question': {'de': data['question_de'].strip(), 'en': data['question_en'].strip()},
                'options': [{'de': option['de'].strip(), 'en': option['en'].strip()} for option in options],
                'correct_index': correct_index,
            },
            max_points=max_points,
            created_by=request.user,
        )
    return JsonResponse({'mission': mission_payload(mission, request.user)}, status=201)


@require_http_methods(['DELETE'])
@csrf_exempt
def mission_detail_view(request, mission_id):
    if not can_create_missions(request.user):
        return JsonResponse({'error': 'permission denied'}, status=403)

    mission = Mission.objects.filter(id=mission_id).first()
    if mission is None:
        return JsonResponse({'error': 'mission not found'}, status=404)
    if not is_admin(request.user) and mission.created_by_id != request.user.id:
        return JsonResponse({'error': 'permission denied'}, status=403)
    if mission.attempts.exists():
        return JsonResponse({'error': 'completed missions cannot be deleted'}, status=409)

    mission.delete()
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def leaderboard_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    entries = []
    users = User.objects.select_related('profile').order_by('first_name', 'last_name', 'username')
    for user in users:
        profile = ensure_profile(user)
        name = f'{user.first_name} {user.last_name}'.strip() or user.username
        progress = progress_payload(profile)
        entries.append({
            'user_id': user.id,
            'name': name,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'total_points': progress['total_points'],
            'completed_missions': progress['completed_mission_count'],
            'level': progress['level'],
        })

    entries.sort(key=lambda entry: (-entry['total_points'], -entry['completed_missions'], entry['name'].lower()))
    for index, entry in enumerate(entries, start=1):
        entry['rank'] = index
    return JsonResponse({'entries': entries})
