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
    GENERATION_MAX_TOKENS as TASK_GENERATION_MAX_TOKENS,
    SYSTEM_PROMPT as TASK_SYSTEM_PROMPT,
    TASK_CHALLENGE_PROMPTS,
    TASK_CHALLENGE_TYPES,
    TASK_TOPICS,
    build_difficulty_instruction,
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
    failed_requirements = metadata.get('failed_requirements', [])
    if not isinstance(failed_requirements, list):
        failed_requirements = []
    requirements = run.request_payload.get('requirements', []) if isinstance(run.request_payload, dict) else []
    requirements_by_id = {
        item.get('id'): item for item in requirements
        if isinstance(item, dict) and isinstance(item.get('id'), str)
    }
    failed_requirements = [
        {
            **failure,
            'scheduled_date': failure.get('scheduled_date') or requirements_by_id.get(
                failure.get('requirement_id'), {},
            ).get('scheduled_date'),
            'output_type': failure.get('output_type') or requirements_by_id.get(
                failure.get('requirement_id'), {},
            ).get('output_type'),
            'mission_type': failure.get('mission_type') or requirements_by_id.get(
                failure.get('requirement_id'), {},
            ).get('mission_type') or requirements_by_id.get(
                failure.get('requirement_id'), {},
            ).get('requested_mission_type'),
        }
        for failure in failed_requirements
        if isinstance(failure, dict)
    ]
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
        'mission_metrics': metadata.get('mission_metrics', []),
        'failed_count': len(failed_requirements),
        'failed_requirements': failed_requirements,
        'partial_success': run.status == GenerationRun.STATUS_COMPLETED and bool(failed_requirements),
        'mission_ids': list(run.missions.order_by('scheduled_date').values_list('id', flat=True)),
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'updated_at': run.updated_at.isoformat() if run.updated_at else None,
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
                        'content': (
                            f'{TASK_CHALLENGE_PROMPTS[mission_type]}\n\n'
                            f'{build_difficulty_instruction(mission_type, difficulty)}'
                        ),
                    },
                ], temperature=0.5, max_tokens=TASK_GENERATION_MAX_TOKENS),
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


def _normalize_task_item_count(payload, mission_type, difficulty):
    """Trim surplus LLM rows while preserving the task's grading constraints.

    Models frequently overshoot long exact-count arrays even when they finish
    normally. The deterministic validator remains strict; only the n8n contract
    normalizes a surplus. Missing items are never invented and still fail.
    """
    if not isinstance(payload, dict):
        return payload
    expected = (
        {'easy': 12, 'medium': 16, 'hard': 20}
        if mission_type == Mission.TYPE_INVOICE_EXTRACTION
        else {'easy': 24, 'medium': 36, 'hard': 48}
    ).get(difficulty)
    collection_name = 'invoices' if mission_type == Mission.TYPE_INVOICE_EXTRACTION else 'rows'
    items = payload.get(collection_name)
    if expected is None or not isinstance(items, list) or len(items) <= expected:
        return payload

    selected = set()
    excluded = set()

    def select_matching(predicate, limit):
        for index, item in enumerate(items):
            if len(selected) >= expected or limit <= 0:
                break
            if index not in selected and isinstance(item, dict) and predicate(item):
                selected.add(index)
                limit -= 1

    if mission_type == Mission.TYPE_BULK_CATEGORIZATION:
        categories = payload.get('categories_de')
        if isinstance(categories, list):
            for category_index in range(len(categories)):
                select_matching(
                    lambda item, category_index=category_index: (
                        item.get('category_index') == category_index
                        or str(item.get('category_index')) == str(category_index)
                    ),
                    3,
                )
    elif mission_type == Mission.TYPE_PLAN_ACTUAL_DEVIATION:
        if difficulty == Mission.DIFFICULTY_HARD:
            select_matching(
                lambda item: isinstance(item.get('plan'), (int, float))
                and isinstance(item.get('actual'), (int, float))
                and item['actual'] < item['plan'],
                6,
            )
        select_matching(
            lambda item: isinstance(item.get('plan'), (int, float))
            and isinstance(item.get('actual'), (int, float))
            and item['plan'] > 0
            and (item['actual'] - item['plan']) / item['plan'] > 0.10,
            4,
        )
    elif mission_type == Mission.TYPE_DUPLICATE_PAYMENT_HUNT:
        groups = {}
        for index, item in enumerate(items):
            if isinstance(item, dict):
                groups.setdefault(item.get('invoice_number'), []).append(index)
        expected_pairs = {'easy': 3, 'medium': 4, 'hard': 6}[difficulty]
        pair_groups = [indices for indices in groups.values() if len(indices) == 2]
        for indices in pair_groups[:expected_pairs]:
            selected.update(indices)
        # Extra generated pairs become ordinary unique rows by retaining at
        # most one member. This keeps the exact duplicate-pair contract.
        for indices in pair_groups[expected_pairs:]:
            excluded.update(indices[1:])
        for indices in (indices for indices in groups.values() if len(indices) > 2):
            excluded.update(indices[1:])
    elif mission_type == Mission.TYPE_INVOICE_EXTRACTION:
        groups = {}
        for index, item in enumerate(items):
            if isinstance(item, dict):
                groups.setdefault(item.get('vendor_de'), []).append(index)
        repeated_groups = [indices for indices in groups.values() if len(indices) > 1]
        for indices in repeated_groups[:3]:
            selected.update(indices[:2])

    for index in range(len(items)):
        if len(selected) >= expected:
            break
        if index not in excluded:
            selected.add(index)

    normalized = dict(payload)
    normalized[collection_name] = [items[index] for index in sorted(selected)[:expected]]
    return normalized


def _validated_task_mission(requirement, result):
    mission_type = requirement.get('mission_type')
    raw_variants = result.get('variants')
    if not isinstance(raw_variants, dict) or set(raw_variants) != set(Mission.DIFFICULTIES):
        raise GenerationContractError('task result must contain exactly easy, medium, and hard variants')
    variants = {}
    for difficulty in Mission.DIFFICULTIES:
        try:
            normalized_payload = _normalize_task_item_count(
                raw_variants[difficulty], mission_type, difficulty,
            )
            variants[difficulty] = validate_task_challenge(
                normalized_payload, mission_type, difficulty=difficulty,
            )
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
        raw_payload = _normalize_task_item_count(
            raw_payload, requirement.get('mission_type'), difficulty,
        )
        try:
            return validate_task_challenge(
                raw_payload, requirement.get('mission_type'), difficulty=difficulty,
            )
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


def _normalize_mission_metrics(run, mission_metrics):
    """Bound and normalize untrusted per-requirement LLM timing metadata."""
    if mission_metrics is None:
        return []
    if not isinstance(mission_metrics, list):
        raise GenerationContractError('mission_metrics must be an array')

    requirements = run.request_payload.get('requirements', []) if isinstance(run.request_payload, dict) else []
    requirements_by_id = {
        item.get('id'): item for item in requirements
        if isinstance(item, dict) and isinstance(item.get('id'), str)
    }
    normalized = []
    seen = set()

    def optional_int(value, maximum):
        if value is None:
            return None
        try:
            return max(0, min(maximum, int(value)))
        except (TypeError, ValueError):
            return None

    for item in mission_metrics[:100]:
        if not isinstance(item, dict):
            continue
        requirement_id = item.get('requirement_id')
        if requirement_id not in requirements_by_id or requirement_id in seen:
            continue
        seen.add(requirement_id)
        requirement = requirements_by_id[requirement_id]
        phases = {}
        for phase in ('generator', 'reviewer', 'repair'):
            calls = item.get(phase, [])
            if not isinstance(calls, list):
                calls = []
            normalized_calls = []
            for call in calls[:20]:
                if not isinstance(call, dict):
                    continue
                normalized_calls.append({
                    'duration_ms': optional_int(call.get('duration_ms'), 3_600_000),
                    'prompt_tokens': optional_int(call.get('prompt_tokens'), 10_000_000),
                    'completion_tokens': optional_int(call.get('completion_tokens'), 10_000_000),
                    'total_tokens': optional_int(call.get('total_tokens'), 20_000_000),
                    'finish_reason': (
                        str(call.get('finish_reason'))[:64]
                        if call.get('finish_reason') is not None else None
                    ),
                    'call_index': optional_int(call.get('call_index'), 1000),
                    'difficulty': (
                        str(call.get('difficulty'))[:32]
                        if call.get('difficulty') is not None else None
                    ),
                    'repair_attempt': optional_int(call.get('repair_attempt'), 100),
                })
            phases[phase] = normalized_calls
        normalized.append({
            'requirement_id': requirement_id,
            'scheduled_date': requirement.get('scheduled_date'),
            'output_type': requirement.get('output_type'),
            'mission_type': requirement.get('mission_type') or requirement.get('requested_mission_type'),
            'failed': item.get('failed') is True,
            **phases,
        })
    return normalized


def _validated_results(run, results, failed_requirements=None):
    if not isinstance(results, list):
        raise GenerationContractError('completed callback requires a results array')
    if failed_requirements is None:
        failed_requirements = []
    if not isinstance(failed_requirements, list):
        raise GenerationContractError('failed_requirements must be an array')
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

    failure_by_id = {}
    for item in failed_requirements:
        if not isinstance(item, dict) or not isinstance(item.get('requirement_id'), str):
            raise GenerationContractError('every failed requirement needs a requirement_id')
        requirement_id = item['requirement_id']
        requirement = _requirement(run, requirement_id)
        if requirement_id in failure_by_id:
            raise GenerationContractError('failed requirements contain a duplicate requirement_id')
        try:
            repair_attempts = max(0, int(item.get('repair_attempts', 0)))
        except (TypeError, ValueError):
            repair_attempts = 0
        failure_by_id[requirement_id] = {
            'requirement_id': requirement_id,
            'scheduled_date': requirement.get('scheduled_date'),
            'output_type': requirement.get('output_type'),
            'mission_type': requirement.get('mission_type') or requirement.get('requested_mission_type'),
            'error_message': str(item.get('error_message') or 'Mission requirement failed')[:2000],
            'repair_attempts': repair_attempts,
        }

    if set(result_by_id) & set(failure_by_id):
        raise GenerationContractError('a generation requirement cannot both pass and fail')
    if failure_by_id and run.kind != GenerationRun.KIND_WEEKLY_MISSIONS:
        raise GenerationContractError('partial completion is only supported for weekly mission generation')
    if set(result_by_id) | set(failure_by_id) != expected_ids:
        raise GenerationContractError('completed results do not fill every generation requirement')
    if failure_by_id and not result_by_id:
        raise GenerationContractError('partial completion requires at least one successful result')
    return result_by_id, list(failure_by_id.values())


def _store_new_missions(run, candidates):
    if run.kind == GenerationRun.KIND_WEEKLY_MISSIONS and run.force:
        candidate_dates = [candidate['scheduled_date'] for candidate in candidates]
        Mission.objects.filter(
            scheduled_date__in=candidate_dates,
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


def complete_generation_run(
    run_id, *, results, review_report, n8n_execution_id='', research_context=None, failed_requirements=None,
    mission_metrics=None,
):
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
        validated, normalized_failures = _validated_results(run, results, failed_requirements)
        normalized_metrics = _normalize_mission_metrics(run, mission_metrics)
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
            'failed_requirements': normalized_failures,
            'mission_metrics': normalized_metrics,
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
            metadata = dict(metadata)
            if 'mission_metrics' in metadata:
                metadata['mission_metrics'] = _normalize_mission_metrics(run, metadata['mission_metrics'])
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
