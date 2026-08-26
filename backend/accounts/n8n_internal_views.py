"""Service-only endpoints used by the n8n mission workflow."""

import hmac
import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import GenerationRun
from .services.n8n_mission_generation import (
    GenerationContractError,
    complete_generation_run,
    generation_run_payload,
    update_generation_run,
    validate_requirement_result,
)


def _json_body(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _authenticate_callback(request):
    expected = settings.N8N_CALLBACK_SECRET
    if not expected:
        if settings.DEBUG:
            return None
        return JsonResponse({'error': 'n8n callback authentication is not configured'}, status=503)
    supplied = request.headers.get('X-N8N-Callback-Secret', '')
    if not supplied or not hmac.compare_digest(supplied, expected):
        return JsonResponse({'error': 'invalid n8n callback credential'}, status=401)
    return None


def _run(run_id):
    try:
        return GenerationRun.objects.get(id=run_id)
    except (GenerationRun.DoesNotExist, ValueError, TypeError):
        return None


@require_http_methods(['POST'])
@csrf_exempt
def validate_mission_view(request):
    auth_error = _authenticate_callback(request)
    if auth_error:
        return auth_error
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'request body must be a JSON object'}, status=400)
    run = _run(data.get('generation_run_id'))
    if run is None:
        return JsonResponse({'error': 'generation run not found'}, status=404)
    requirement_id = data.get('requirement_id')
    if not isinstance(requirement_id, str) or not requirement_id:
        return JsonResponse({'error': 'requirement_id is required'}, status=400)
    try:
        candidate = validate_requirement_result(run, requirement_id, data.get('result'))
    except GenerationContractError as exception:
        return JsonResponse({'valid': False, 'error': str(exception)}, status=422)
    return JsonResponse({'valid': True, 'normalized_result': candidate})


@require_http_methods(['POST'])
@csrf_exempt
def generation_callback_view(request):
    auth_error = _authenticate_callback(request)
    if auth_error:
        return auth_error
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'request body must be a JSON object'}, status=400)
    run = _run(data.get('generation_run_id'))
    if run is None:
        return JsonResponse({'error': 'generation run not found'}, status=404)
    status = data.get('status')
    try:
        if status == GenerationRun.STATUS_COMPLETED:
            run, missions = complete_generation_run(
                run.id,
                results=data.get('results'),
                review_report=data.get('review_report'),
                n8n_execution_id=data.get('n8n_execution_id', ''),
                research_context=data.get('research_context'),
                failed_requirements=data.get('failed_requirements'),
                mission_metrics=data.get('mission_metrics'),
            )
            return JsonResponse({
                'generation_run': generation_run_payload(run),
                'mission_ids': [mission.id for mission in missions],
            })
        run = update_generation_run(
            run.id,
            status=status,
            n8n_execution_id=data.get('n8n_execution_id', ''),
            error_message=data.get('error_message', ''),
            metadata=data.get('metadata'),
        )
    except GenerationContractError as exception:
        return JsonResponse({'error': str(exception)}, status=422)
    return JsonResponse({'generation_run': generation_run_payload(run)})
