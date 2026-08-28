"""Deterministic helpers shared by the mission generation paths.

Mission generation itself runs in n8n; Django only plans the week, normalizes
model output and writes the results. This module holds the pieces both the n8n
orchestration and the task/chat services rely on: the shared error type, JSON
extraction from model responses, week planning, and applying a validated
candidate onto a Mission instance.
"""

import json
import logging
import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import Mission


logger = logging.getLogger(__name__)

WEEKDAYS_PER_WEEK = 5


class AiMissionGenerationError(RuntimeError):
    pass


def is_business_day(day):
    return day.weekday() < 5


def next_calendar_week(reference_date=None):
    today = reference_date or timezone.localdate()
    start = today + timedelta(days=7 - today.weekday())
    return start, start + timedelta(days=6)


def extract_json(content):
    if not isinstance(content, str) or not content.strip():
        raise AiMissionGenerationError('AI returned an empty response')
    text = content.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        text = '\n'.join(lines[1:-1]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error_value:
        start = text.find('{')
        if start >= 0:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(text[start:])
                return parsed
            except json.JSONDecodeError:
                pass
        logger.warning(
            'AI returned invalid JSON (%s chars, error at %s). Response tail: %r',
            len(text), error_value.pos, text[-300:],
        )
        raise AiMissionGenerationError('AI returned invalid JSON, likely due to a truncated response') from error_value


def apply_candidate(mission, candidate):
    mission.mission_type = candidate['mission_type']
    mission.scheduled_date = candidate['scheduled_date']
    mission.title_de = candidate['title_de']
    mission.title_en = candidate['title_en']
    mission.description_de = candidate['description_de']
    mission.description_en = candidate['description_en']
    mission.content = candidate['content']
    mission.max_points = candidate['max_points']
    mission.topic_de = candidate.get('topic_de', '')
    mission.topic_en = candidate.get('topic_en', '')
    mission.learning_objective_de = candidate.get('learning_objective_de', '')
    mission.learning_objective_en = candidate.get('learning_objective_en', '')
    mission.variants = candidate.get('variants', {})


def task_days_per_week():
    return settings.MISSION_TASK_DAYS_PER_WEEK


def plan_next_week(force=False, reference_date=None, week_start=None):
    """Return the date and mission-kind plan without calling an AI service."""
    if week_start is None:
        week_start, week_end = next_calendar_week(reference_date)
    else:
        week_end = week_start + timedelta(days=6)
    today = timezone.localdate()

    open_weekdays = []
    for offset in range(WEEKDAYS_PER_WEEK):
        day = week_start + timedelta(days=offset)
        if day < today or not is_business_day(day):
            continue
        occupied_missions = Mission.objects.filter(
            scheduled_date=day,
            status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
        )
        if force:
            occupied_missions = occupied_missions.exclude(status=Mission.STATUS_REVIEW, generated_by_ai=True)
        if occupied_missions.exists():
            continue
        open_weekdays.append(day)

    wanted_task_days = min(task_days_per_week(), len(open_weekdays))
    task_days = set(random.sample(open_weekdays, wanted_task_days)) if wanted_task_days else set()
    quiz_days = [day for day in open_weekdays if day not in task_days]
    return week_start, week_end, task_days, quiz_days
