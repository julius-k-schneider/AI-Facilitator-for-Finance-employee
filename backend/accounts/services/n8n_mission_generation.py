"""Versioned n8n contracts while Django remains the mission authority."""

import random
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import GenerationRun, Mission
from accounts.services.ai_chat_challenge import (
    SYSTEM_PROMPT as CHAT_SYSTEM_PROMPT,
    USER_PROMPT as CHAT_USER_PROMPT,
    validate_challenge,
)
from accounts.services.ai_mission_generator import (
    SYSTEM_PROMPT as QUIZ_SYSTEM_PROMPT,
    AiMissionGenerationError,
    apply_candidate,
    build_user_prompt,
    plan_next_week,
)
from accounts.services.ai_task_challenge import (
    DIFFICULTY_INSTRUCTIONS,
    SYSTEM_PROMPT as TASK_SYSTEM_PROMPT,
    TASK_CHALLENGE_PROMPTS,
    TASK_CHALLENGE_TYPES,
    TASK_TOPICS,
    validate_task_challenge,
)
from accounts.services.mission_validation import MissionValidationError, validate_generated_payload
from accounts.services.n8n_client import N8NClientError, start_mission_generation


CONTRACT_VERSION = '1'
OUTPUT_QUIZ_MISSION = 'quiz_mission'
OUTPUT_TASK_MISSION = 'task_mission'
OUTPUT_TRAINING_TASK = 'training_task'
OUTPUT_TRAINING_CHAT = 'training_chat'


class GenerationContractError(ValueError):
    pass


def generation_run_payload(run):
    metadata = run.result_metadata if isinstance(run.result_metadata, dict) else {}
    return {
        'id': str(run.id),
        'kind': run.kind,
        'status': run.status,
        'week_start': run.week_start.isoformat() if run.week_start else None,
        'week_end': run.week_end.isoformat() if run.week_end else None,
        'target_mission_id': run.target_mission_id,
        'workflow_version': run.workflow_version,
        'n8n_execution_id': run.n8n_execution_id,
        'error_message': run.error_message,
        'review_report': run.review_report,
        'created_count': metadata.get('created_count', 0),
        'mission_ids': list(run.missions.order_by('scheduled_date').values_list('id', flat=True)),
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'started_at': run.started_at.isoformat() if run.started_at else None,
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        'failed_at': run.failed_at.isoformat() if run.failed_at else None,
    }


def _generator_request(messages, *, temperature, max_tokens):
    return {
        'messages': messages,
        'response_format': 'json_object',
        'temperature': temperature,
        'max_tokens': max_tokens,
    }


def _quiz_requirement(requirement_id, scheduled_date, requested_type=None):
    return {
        'id': requirement_id,
        'output_type': OUTPUT_QUIZ_MISSION,
        'scheduled_date': scheduled_date.isoformat(),
        'requested_mission_type': requested_type,
        'generator_requests': [_generator_request([
            {'role': 'system', 'content': QUIZ_SYSTEM_PROMPT},
            {'role': 'user', 'content': build_user_prompt({scheduled_date: 1}, requested_type)},
        ], temperature=0.4, max_tokens=9000)],
    }


def _task_requirement(requirement_id, scheduled_date, mission_type, difficulties):
    return {
        'id': requirement_id,
        'output_type': OUTPUT_TASK_MISSION if len(difficulties) == 3 else OUTPUT_TRAINING_TASK,
        'scheduled_date': scheduled_date.isoformat(),
        'mission_type': mission_type,
        'difficulties': list(difficulties),
        'generator_requests': [
            {
                'difficulty': difficulty,
                **_generator_request([
                    {'role': 'system', 'content': TASK_SYSTEM_PROMPT},
                    {
                        'role': 'user',
                        'content': f'{TASK_CHALLENGE_PROMPTS[mission_type]}\n\n{DIFFICULTY_INSTRUCTIONS[difficulty]}',
                    },
                ], temperature=0.5, max_tokens=4500),
            }
            for difficulty in difficulties
        ],
    }


def _chat_requirement():
    return {
        'id': 'training-chat',
        'output_type': OUTPUT_TRAINING_CHAT,
        'generator_requests': [_generator_request([
            {'role': 'system', 'content': CHAT_SYSTEM_PROMPT},
            {'role': 'user', 'content': CHAT_USER_PROMPT},
        ], temperature=0.4, max_tokens=3000)],
    }


def _create_run(requested_by, kind, requirements, **fields):
    run = GenerationRun(
        requested_by=requested_by,
        kind=kind,
        workflow_version=settings.N8N_WORKFLOW_VERSION,
        **fields,
    )
    run.request_payload = {
        'contract_version': CONTRACT_VERSION,
        'workflow_version': run.workflow_version,
        'generation_run_id': str(run.id),
        'generation_kind': kind,
        'requirements': requirements,
        'research_context': run.research_context,
        'review_policy': {
            'separate_reviewer_required': True,
            'required_verdict': 'pass',
            'repair_supported': True,
        },
        'django_endpoints': {
            'validate_mission': '/internal/n8n/validate-mission/',
            'generation_callback': '/internal/n8n/generation-callback/',
        },
    }
    if not requirements:
        run.status = GenerationRun.STATUS_COMPLETED
        run.completed_at = timezone.now()
        run.result_metadata = {'created_count': 0, 'reason': 'no_generation_required'}
    run.save()
    return run


def create_weekly_run(requested_by, *, force=False, week_start=None):
    planned_start, week_end, task_days, quiz_days = plan_next_week(force=force, week_start=week_start)
    active = GenerationRun.objects.filter(
        requested_by=requested_by,
        kind=GenerationRun.KIND_WEEKLY_MISSIONS,
        week_start=planned_start,
        force=force,
        status__in=GenerationRun.ACTIVE_STATUSES,
    ).first()
    if active:
        return active
    requirements = []
    for day in sorted(quiz_days):
        requirements.append(_quiz_requirement(day.isoformat(), day))
    for day in sorted(task_days):
        requirements.append(_task_requirement(
            day.isoformat(), day, random.choice(TASK_CHALLENGE_TYPES), Mission.DIFFICULTIES,
        ))
    return _create_run(
        requested_by,
        GenerationRun.KIND_WEEKLY_MISSIONS,
        sorted(requirements, key=lambda item: item['scheduled_date']),
        week_start=planned_start,
        week_end=week_end,
        force=force,
    )


def create_regeneration_run(requested_by, mission):
    if mission.status != Mission.STATUS_REVIEW or not mission.generated_by_ai:
        raise GenerationContractError('Only AI review missions can be regenerated')
    active = GenerationRun.objects.filter(
        kind=GenerationRun.KIND_REGENERATE_MISSION,
        target_mission=mission,
        status__in=GenerationRun.ACTIVE_STATUSES,
    ).first()
    if active:
        return active
    if mission.mission_type in Mission.TASK_TYPES:
        requirement = _task_requirement(
            'replacement', mission.scheduled_date, mission.mission_type, Mission.DIFFICULTIES,
        )
    else:
        requirement = _quiz_requirement('replacement', mission.scheduled_date)
    return _create_run(
        requested_by,
        GenerationRun.KIND_REGENERATE_MISSION,
        [requirement],
        target_mission=mission,
    )


def create_scheduled_task_run(requested_by, scheduled_date, mission_type=None):
    mission_type = mission_type or random.choice(TASK_CHALLENGE_TYPES)
    if mission_type not in TASK_CHALLENGE_TYPES:
        raise GenerationContractError('unsupported task challenge type')
    return _create_run(
        requested_by,
        GenerationRun.KIND_SCHEDULED_TASK,
        [_task_requirement('scheduled-task', scheduled_date, mission_type, Mission.DIFFICULTIES)],
    )


def create_training_choice_run(requested_by, mission_type):
    if mission_type not in Mission.CHOICE_TYPES:
        raise GenerationContractError('unsupported training mission type')
    return _create_run(
        requested_by,
        GenerationRun.KIND_TRAINING_CHOICE,
        [_quiz_requirement('training-choice', timezone.localdate(), mission_type)],
    )


def create_training_task_run(requested_by, mission_type, difficulty):
    mission_type = mission_type or random.choice(TASK_CHALLENGE_TYPES)
    if mission_type not in TASK_CHALLENGE_TYPES:
        raise GenerationContractError('unsupported task challenge type')
    if difficulty not in Mission.DIFFICULTIES:
        raise GenerationContractError('unsupported task challenge difficulty')
    return _create_run(
        requested_by,
        GenerationRun.KIND_TRAINING_TASK,
        [_task_requirement('training-task', timezone.localdate(), mission_type, (difficulty,))],
    )


def create_training_chat_run(requested_by):
    return _create_run(requested_by, GenerationRun.KIND_TRAINING_CHAT, [_chat_requirement()])


def dispatch_generation_run(run):
    if run.status == GenerationRun.STATUS_COMPLETED:
        return {}
    if run.status not in {GenerationRun.STATUS_QUEUED, GenerationRun.STATUS_FAILED}:
        raise GenerationContractError('generation run cannot be dispatched from its current status')
    try:
        response = start_mission_generation(run.request_payload, idempotency_key=run.id)
    except N8NClientError as exception:
        run.status = GenerationRun.STATUS_FAILED
        run.failed_at = timezone.now()
        run.error_message = str(exception)
        run.save(update_fields=['status', 'failed_at', 'error_message', 'updated_at'])
        raise
    run.status = GenerationRun.STATUS_DISPATCHED
    run.started_at = run.started_at or timezone.now()
    run.failed_at = None
    run.error_message = ''
    execution_id = response.get('n8n_execution_id') or response.get('execution_id') or ''
    run.n8n_execution_id = str(execution_id)[:160]
    run.result_metadata = {**(run.result_metadata or {}), 'dispatch_status': response.get('status', 'accepted')}
    run.save(update_fields=[
        'status', 'started_at', 'failed_at', 'error_message', 'n8n_execution_id', 'result_metadata', 'updated_at',
    ])
    return response


def _requirement(run, requirement_id):
    requirements = run.request_payload.get('requirements') if isinstance(run.request_payload, dict) else None
    if not isinstance(requirements, list):
        raise GenerationContractError('generation run has no valid requirements')
    requirement = next((item for item in requirements if item.get('id') == requirement_id), None)
    if not isinstance(requirement, dict):
        raise GenerationContractError('result does not match a generation requirement')
    return requirement


def _parse_date(value):
    try:
        return date.fromisoformat(str(value))
    except ValueError as exception:
        raise GenerationContractError('requirement has an invalid scheduled date') from exception


def _validated_task_mission(requirement, result):
    mission_type = requirement.get('mission_type')
    raw_variants = result.get('variants')
    if not isinstance(raw_variants, dict) or set(raw_variants) != set(Mission.DIFFICULTIES):
        raise GenerationContractError('task result must contain exactly easy, medium, and hard variants')
    variants = {}
    for difficulty in Mission.DIFFICULTIES:
        try:
            variants[difficulty] = validate_task_challenge(raw_variants[difficulty], mission_type)
        except AiMissionGenerationError as exception:
            raise GenerationContractError(str(exception)) from exception
    easy = variants[Mission.DIFFICULTY_EASY]
    return {
        **easy,
        **TASK_TOPICS[mission_type],
        'scheduled_date': _parse_date(requirement['scheduled_date']),
        'variants': {
            difficulty: {
                'title_de': candidate['title_de'],
                'title_en': candidate['title_en'],
                'description_de': candidate['description_de'],
                'description_en': candidate['description_en'],
                'max_points': candidate['max_points'],
                'content': candidate['content'],
            }
            for difficulty, candidate in variants.items()
        },
    }


def validate_requirement_result(run, requirement_id, result):
    """Apply the existing deterministic validator to one n8n result."""
    if not isinstance(result, dict):
        raise GenerationContractError('result must be an object')
    requirement = _requirement(run, requirement_id)
    output_type = requirement.get('output_type')
    if output_type == OUTPUT_QUIZ_MISSION:
        scheduled_date = _parse_date(requirement['scheduled_date'])
        try:
            candidate = validate_generated_payload(result.get('payload'), {scheduled_date: 1})[0]
        except MissionValidationError as exception:
            raise GenerationContractError(str(exception)) from exception
        requested_type = requirement.get('requested_mission_type')
        if requested_type and candidate['mission_type'] != requested_type:
            raise GenerationContractError('result does not use the requested mission type')
        return candidate
    if output_type == OUTPUT_TASK_MISSION:
        return _validated_task_mission(requirement, result)
    if output_type == OUTPUT_TRAINING_TASK:
        difficulty = requirement['difficulties'][0]
        raw_payload = result.get('payload')
        if raw_payload is None and isinstance(result.get('variants'), dict):
            raw_payload = result['variants'].get(difficulty)
        try:
            return validate_task_challenge(raw_payload, requirement.get('mission_type'))
        except AiMissionGenerationError as exception:
            raise GenerationContractError(str(exception)) from exception
    if output_type == OUTPUT_TRAINING_CHAT:
        try:
            return validate_challenge(result.get('payload'))
        except AiMissionGenerationError as exception:
            raise GenerationContractError(str(exception)) from exception
    raise GenerationContractError('requirement has an unsupported output type')


def _json_safe(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _validated_results(run, results):
    if not isinstance(results, list):
        raise GenerationContractError('completed callback requires a results array')
    requirements = run.request_payload.get('requirements', [])
    expected_ids = {item['id'] for item in requirements}
    result_by_id = {}
    for item in results:
        if not isinstance(item, dict) or not isinstance(item.get('requirement_id'), str):
            raise GenerationContractError('every result needs a requirement_id')
        requirement_id = item['requirement_id']
        if requirement_id in result_by_id:
            raise GenerationContractError('completed results contain a duplicate requirement_id')
        result_by_id[requirement_id] = validate_requirement_result(run, requirement_id, item)
    if set(result_by_id) != expected_ids:
        raise GenerationContractError('completed results do not fill every generation requirement')
    return result_by_id


def _store_new_missions(run, candidates):
    if run.kind == GenerationRun.KIND_WEEKLY_MISSIONS and run.force:
        Mission.objects.filter(
            scheduled_date__range=(run.week_start, run.week_end),
            status=Mission.STATUS_REVIEW,
            generated_by_ai=True,
        ).delete()
    for candidate in candidates:
        if Mission.objects.filter(
            scheduled_date=candidate['scheduled_date'],
            status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
        ).exists():
            raise GenerationContractError(
                f'mission schedule changed for {candidate["scheduled_date"].isoformat()}'
            )
    missions = []
    for candidate in candidates:
        mission = Mission(
            created_by=run.requested_by,
            status=Mission.STATUS_REVIEW,
            generated_by_ai=True,
            generation_batch_id=run.id,
            generation_run=run,
        )
        apply_candidate(mission, candidate)
        mission.save()
        missions.append(mission)
    return missions


def complete_generation_run(run_id, *, results, review_report, n8n_execution_id='', research_context=None):
    if not isinstance(review_report, dict) or review_report.get('verdict') != 'pass':
        raise GenerationContractError('completed callback requires a passed AI review')
    with transaction.atomic():
        # Lock only the generation run. ``target_mission`` is nullable, so joining
        # it here creates a LEFT OUTER JOIN; PostgreSQL rejects FOR UPDATE on the
        # nullable side of that join. Regeneration locks the target mission with a
        # separate query below, and the other run kinds do not need the relation.
        run = GenerationRun.objects.select_for_update().get(id=run_id)
        if run.status == GenerationRun.STATUS_COMPLETED:
            return run, list(run.missions.order_by('scheduled_date'))
        validated = _validated_results(run, results)
        missions = []
        if run.kind in {GenerationRun.KIND_WEEKLY_MISSIONS, GenerationRun.KIND_SCHEDULED_TASK}:
            missions = _store_new_missions(run, list(validated.values()))
        elif run.kind == GenerationRun.KIND_REGENERATE_MISSION:
            mission = Mission.objects.select_for_update().filter(
                id=run.target_mission_id,
                status=Mission.STATUS_REVIEW,
                generated_by_ai=True,
            ).first()
            if mission is None:
                raise GenerationContractError('review mission is no longer available for regeneration')
            candidate = next(iter(validated.values()))
            apply_candidate(mission, candidate)
            mission.created_by = run.requested_by
            mission.generation_batch_id = run.id
            mission.generation_run = run
            mission.reviewed_by = None
            mission.reviewed_at = None
            mission.save()
            missions = [mission]
        elif run.kind in {
            GenerationRun.KIND_TRAINING_CHOICE,
            GenerationRun.KIND_TRAINING_TASK,
            GenerationRun.KIND_TRAINING_CHAT,
        }:
            run.result_payload = _json_safe(validated)
        else:
            raise GenerationContractError('generation run kind is unsupported')

        run.status = GenerationRun.STATUS_COMPLETED
        run.completed_at = timezone.now()
        run.failed_at = None
        run.error_message = ''
        run.review_report = review_report
        if isinstance(research_context, list):
            run.research_context = research_context
        if n8n_execution_id:
            run.n8n_execution_id = str(n8n_execution_id)[:160]
        run.result_metadata = {
            **(run.result_metadata or {}),
            'created_count': len(missions),
            'mission_ids': [mission.id for mission in missions],
        }
        run.save(update_fields=[
            'status', 'completed_at', 'failed_at', 'error_message', 'review_report', 'research_context',
            'result_payload', 'n8n_execution_id', 'result_metadata', 'updated_at',
        ])
    return run, missions


def update_generation_run(run_id, *, status, n8n_execution_id='', error_message='', metadata=None):
    allowed_statuses = {
        GenerationRun.STATUS_RUNNING,
        GenerationRun.STATUS_VALIDATING,
        GenerationRun.STATUS_REVIEWING,
        GenerationRun.STATUS_REPAIRING,
        GenerationRun.STATUS_FAILED,
    }
    if status not in allowed_statuses:
        raise GenerationContractError('callback status is unsupported')
    with transaction.atomic():
        run = GenerationRun.objects.select_for_update().get(id=run_id)
        if run.status == GenerationRun.STATUS_COMPLETED:
            return run
        if run.status == GenerationRun.STATUS_FAILED and status == GenerationRun.STATUS_FAILED:
            return run
        run.status = status
        run.started_at = run.started_at or timezone.now()
        if n8n_execution_id:
            run.n8n_execution_id = str(n8n_execution_id)[:160]
        if isinstance(metadata, dict):
            run.result_metadata = {**(run.result_metadata or {}), **metadata}
        update_fields = ['status', 'started_at', 'n8n_execution_id', 'result_metadata', 'updated_at']
        if status == GenerationRun.STATUS_FAILED:
            run.failed_at = timezone.now()
            run.error_message = str(error_message or 'n8n workflow failed')[:2000]
            update_fields.extend(['failed_at', 'error_message'])
        else:
            run.failed_at = None
            run.error_message = ''
            update_fields.extend(['failed_at', 'error_message'])
        run.save(update_fields=update_fields)
    return run
