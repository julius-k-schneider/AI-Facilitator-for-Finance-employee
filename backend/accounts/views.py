import json
import os

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Profile


User = get_user_model()
VALID_ROLES = {choice for choice, _ in Profile.ROLE_CHOICES}
MISSION_MAX_POINTS = {
    'prompt-quality-quiz': 90,
    'compliance-check-challenge': 120,
}


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
    return {
        'mission_scores': scores,
        'completed_missions': [mission_id for mission_id, score in scores.items() if int(score) > 0],
        'completed_mission_count': profile.completed_mission_count,
        'total_points': profile.total_points,
        'level': level_for_points(profile.total_points),
        'updated_at': profile.progress_updated_at.isoformat() if profile.progress_updated_at else None,
    }


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
    mission_id = (data.get('mission_id') or '').strip()
    if mission_id not in MISSION_MAX_POINTS:
        return JsonResponse({'error': 'unknown mission'}, status=400)
    try:
        score = int(data.get('score', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid score'}, status=400)

    profile = ensure_profile(request.user)
    scores = dict(profile.mission_scores or {})
    safe_score = max(0, min(score, MISSION_MAX_POINTS[mission_id]))
    scores[mission_id] = max(int(scores.get(mission_id, 0)), safe_score)
    profile.mission_scores = scores
    profile.progress_updated_at = timezone.now()
    profile.save(update_fields=['mission_scores', 'progress_updated_at'])
    return JsonResponse({'progress': progress_payload(profile)})


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
