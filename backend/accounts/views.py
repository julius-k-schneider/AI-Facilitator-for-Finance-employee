import json
import os

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import UserProfile


User = get_user_model()
VALID_ROLES = {choice[0] for choice in UserProfile.ROLE_CHOICES}


def parse_json(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return {}


def should_seed_admin(user):
    configured_email = os.environ.get('INITIAL_ADMIN_EMAIL', '').strip().lower()
    if configured_email:
        return user.email.lower() == configured_email

    # MVP bootstrap: if no admin exists yet, the lowest-id existing account becomes admin.
    # Later deployments can set INITIAL_ADMIN_EMAIL to make this explicit.
    has_admin = UserProfile.objects.filter(role=UserProfile.ROLE_ADMIN).exists()
    first_user = User.objects.order_by('id').first()
    return not has_admin and first_user is not None and first_user.id == user.id


def ensure_profile(user):
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created and should_seed_admin(user):
        profile.role = UserProfile.ROLE_ADMIN
        profile.save(update_fields=['role'])
    return profile


def is_admin(user):
    if not user.is_authenticated:
        return False
    return ensure_profile(user).role == UserProfile.ROLE_ADMIN


def admin_count():
    return UserProfile.objects.filter(role=UserProfile.ROLE_ADMIN).count()


def user_payload(user):
    profile = ensure_profile(user)
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': profile.role,
    }


@require_http_methods(['POST'])
@csrf_exempt
def login_view(request):
    data = parse_json(request)
    # Die Kennung kann eine E-Mail (bevorzugt) oder ein Username sein.
    identifier = (data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return JsonResponse({'error': 'email and password required'}, status=400)

    # Falls eine E-Mail angegeben wurde, den zugehörigen Username auflösen.
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

    data = parse_json(request)
    role = data.get('role')
    if role not in VALID_ROLES:
        return JsonResponse({'error': 'invalid role'}, status=400)

    target = User.objects.filter(id=user_id).first()
    if target is None:
        return JsonResponse({'error': 'user not found'}, status=404)

    profile = ensure_profile(target)
    if profile.role == UserProfile.ROLE_ADMIN and role != UserProfile.ROLE_ADMIN and admin_count() <= 1:
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
    if profile.role == UserProfile.ROLE_ADMIN and admin_count() <= 1:
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
    # Der Username wird aus der E-Mail abgeleitet (E-Mail ist die Login-Kennung).
    username = (data.get('username') or email).strip()

    if not all([username, password, email, first_name, last_name]):
        return JsonResponse({'error': 'all fields required'}, status=400)

    if User.objects.filter(username=username).exists() or User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'account already exists'}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
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
