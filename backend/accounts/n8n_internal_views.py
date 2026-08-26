"""Service-only endpoints used by the n8n mission workflow."""

import hmac
import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import GenerationRun, ResearchItem, ResearchRun
from .services.n8n_mission_generation import (
    GenerationContractError,
    complete_generation_run,
    generation_run_payload,
    update_generation_run,
    validate_requirement_result,
)
from .services.research import (
    research_item_payload,
    research_run_payload,
    sync_research_items,
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


@require_http_methods(['POST'])
@csrf_exempt
def research_sync_view(request):
    auth_error = _authenticate_callback(request)
    if auth_error:
        return auth_error
    data = _json_body(request)
    if data is None or not isinstance(data.get('items'), list):
        return JsonResponse({'error': 'items must be a list'}, status=400)
    items = sync_research_items(data['items'])
    run_id = data.get('research_run_id')
    if run_id:
        ResearchRun.objects.filter(id=run_id, status=ResearchRun.STATUS_QUEUED).update(
            status=ResearchRun.STATUS_RUNNING,
            started_at=timezone.now(),
        )
    return JsonResponse({
        'synced_count': len(items),
        # The collector restores these original rows before updating its own
        # deduplication table.
        'items': data['items'],
    })


@require_http_methods(['GET'])
@csrf_exempt
def current_research_view(request):
    auth_error = _authenticate_callback(request)
    if auth_error:
        return auth_error
    as_of = parse_datetime(request.GET.get('as_of', '')) or timezone.now()
    if timezone.is_naive(as_of):
        as_of = timezone.make_aware(as_of, timezone.get_current_timezone())
    items = ResearchItem.objects.filter(eligible=True, valid_until__gte=as_of)
    return JsonResponse({
        'items': [research_item_payload(item, n8n_shape=True) for item in items[:250]],
        'as_of': as_of.isoformat(),
    })


@require_http_methods(['POST'])
@csrf_exempt
def research_callback_view(request):
    auth_error = _authenticate_callback(request)
    if auth_error:
        return auth_error
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'request body must be a JSON object'}, status=400)
    run_id = data.get('research_run_id')
    if not run_id:
        # Editor-only manual executions intentionally have no Django run.
        return JsonResponse({'research_run': None})
    try:
        run = ResearchRun.objects.get(id=run_id)
    except (ResearchRun.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'error': 'research run not found'}, status=404)
    requested_status = data.get('status')
    run.result = data.get('result') if isinstance(data.get('result'), dict) else {
        key: value for key, value in data.items()
        if key not in {'research_run_id', 'status', 'error_message'}
    }
    if requested_status == ResearchRun.STATUS_FAILED:
        run.status = ResearchRun.STATUS_FAILED
        run.error_message = str(data.get('error_message') or 'Research collection failed.')
    else:
        run.status = ResearchRun.STATUS_COMPLETED
        run.error_message = ''
    run.completed_at = timezone.now()
    if run.started_at is None:
        run.started_at = run.created_at
    run.save(update_fields=[
        'status', 'result', 'error_message', 'started_at', 'completed_at', 'updated_at',
    ])
    return JsonResponse({'research_run': research_run_payload(run)})
