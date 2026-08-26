import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import ResearchItem, ResearchRun, ResearchSchedule
from accounts.services.n8n_client import N8NClientError, start_research_collection


def _datetime(value, fallback=None):
    parsed = parse_datetime(str(value or ''))
    if parsed is None:
        parsed = fallback or timezone.now()
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def research_item_payload(item, *, n8n_shape=False):
    payload = {
        'id': str(item.id),
        'item_key': item.item_key,
        'title': item.title,
        'source_name': item.source_name,
        'source_url': item.source_url,
        'source_feed': item.source_feed,
        'source_tier': item.source_tier,
        'published_at': item.published_at.isoformat(),
        'retrieved_at': item.retrieved_at.isoformat(),
        'last_seen_at': item.last_seen_at.isoformat(),
        'language': item.language,
        'tags': item.tags,
        'summary_de': item.summary_de,
        'summary_en': item.summary_en,
        'safe_facts': item.safe_facts,
        'mission_hooks': item.mission_hooks,
        'relevance_score': item.relevance_score,
        'confidence': item.confidence,
        'valid_until': item.valid_until.isoformat(),
        'risk_flags': item.risk_flags,
        'eligible': item.eligible,
        'content_hash': item.content_hash,
        'analysis_method': item.analysis_method,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }
    if n8n_shape:
        payload.update({
            'tags_json': json.dumps(item.tags, ensure_ascii=False),
            'safe_facts_json': json.dumps(item.safe_facts, ensure_ascii=False),
            'mission_hooks_json': json.dumps(item.mission_hooks, ensure_ascii=False),
            'risk_flags_json': json.dumps(item.risk_flags, ensure_ascii=False),
        })
    return payload


def research_schedule_payload(schedule):
    return {
        'enabled': schedule.enabled,
        'weekday': schedule.weekday,
        'run_time': schedule.run_time.strftime('%H:%M'),
        'timezone': schedule.timezone_name,
        'last_triggered_at': (
            schedule.last_triggered_at.isoformat() if schedule.last_triggered_at else None
        ),
        'updated_at': schedule.updated_at.isoformat(),
    }


def research_run_payload(run):
    return {
        'id': str(run.id),
        'trigger': run.trigger,
        'status': run.status,
        'force_refresh': run.force_refresh,
        'result': run.result,
        'error_message': run.error_message,
        'created_at': run.created_at.isoformat(),
        'updated_at': run.updated_at.isoformat(),
        'started_at': run.started_at.isoformat() if run.started_at else None,
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
    }


def sync_research_items(items):
    synced = []
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            continue
        item_key = str(raw.get('item_key') or '').strip()[:80]
        title = str(raw.get('title') or '').strip()[:500]
        source_url = str(raw.get('source_url') or '').strip()[:1200]
        if not item_key or not title or not source_url:
            continue
        now = timezone.now()
        defaults = {
            'title': title,
            'source_name': str(raw.get('source_name') or 'Official source').strip()[:240],
            'source_url': source_url,
            'source_feed': str(raw.get('source_feed') or '').strip()[:1200],
            'source_tier': max(1, min(9, int(raw.get('source_tier') or 1))),
            'published_at': _datetime(raw.get('published_at'), now),
            'retrieved_at': _datetime(raw.get('retrieved_at'), now),
            'last_seen_at': _datetime(raw.get('last_seen_at'), now),
            'language': 'de' if raw.get('language') == 'de' else 'en',
            'tags': _list(raw.get('tags', raw.get('tags_json'))),
            'summary_de': str(raw.get('summary_de') or '').strip(),
            'summary_en': str(raw.get('summary_en') or '').strip(),
            'safe_facts': _list(raw.get('safe_facts', raw.get('safe_facts_json'))),
            'mission_hooks': _list(raw.get('mission_hooks', raw.get('mission_hooks_json'))),
            'relevance_score': max(0, min(100, int(raw.get('relevance_score') or 0))),
            'confidence': raw.get('confidence') if raw.get('confidence') in {
                ResearchItem.CONFIDENCE_LOW,
                ResearchItem.CONFIDENCE_MEDIUM,
                ResearchItem.CONFIDENCE_HIGH,
            } else ResearchItem.CONFIDENCE_LOW,
            'valid_until': _datetime(raw.get('valid_until'), now),
            'risk_flags': _list(raw.get('risk_flags', raw.get('risk_flags_json'))),
            'eligible': raw.get('eligible') is True,
            'content_hash': str(raw.get('content_hash') or '').strip()[:120],
            'analysis_method': str(raw.get('analysis_method') or '').strip()[:80],
            'updated_by': None,
        }
        item, _created = ResearchItem.objects.update_or_create(item_key=item_key, defaults=defaults)
        synced.append(item)
    return synced


@transaction.atomic
def claim_scheduled_research(now=None):
    schedule = ResearchSchedule.objects.select_for_update().filter(pk=1).first()
    if schedule is None:
        schedule = ResearchSchedule.load()
    if not schedule.enabled:
        return None
    try:
        local_now = (now or timezone.now()).astimezone(ZoneInfo(schedule.timezone_name))
    except ZoneInfoNotFoundError:
        local_now = timezone.localtime(now or timezone.now())
    if local_now.weekday() != schedule.weekday:
        return None
    if (local_now.hour, local_now.minute) != (schedule.run_time.hour, schedule.run_time.minute):
        return None
    if schedule.last_triggered_at:
        last_local = schedule.last_triggered_at.astimezone(local_now.tzinfo)
        if last_local.date() == local_now.date():
            return None
    run = ResearchRun.objects.create(trigger=ResearchRun.TRIGGER_SCHEDULED)
    schedule.last_triggered_at = now or timezone.now()
    schedule.save(update_fields=['last_triggered_at', 'updated_at'])
    return run


def dispatch_due_research(now=None):
    """Start n8n only when the stored weekly schedule is actually due."""
    run = claim_scheduled_research(now=now)
    if run is None:
        return None
    try:
        start_research_collection({
            'research_run_id': str(run.id),
            'trigger': ResearchRun.TRIGGER_SCHEDULED,
            'force_refresh': False,
        }, idempotency_key=run.id)
    except N8NClientError as exception:
        run.status = ResearchRun.STATUS_FAILED
        run.error_message = str(exception)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
        return run
    ResearchRun.objects.filter(id=run.id, status=ResearchRun.STATUS_QUEUED).update(
        status=ResearchRun.STATUS_RUNNING,
        started_at=timezone.now(),
    )
    run.refresh_from_db()
    return run
