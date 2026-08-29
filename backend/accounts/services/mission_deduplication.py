"""Conservative duplicate protection for AI-generated missions."""

import re
import unicodedata
from difflib import SequenceMatcher

from accounts.models import Mission


HISTORY_LIMIT = 40
HISTORY_TEXT_LIMIT = 180
SIMILARITY_THRESHOLD = 0.9
TOKEN_OVERLAP_THRESHOLD = 0.82
LEARNING_OBJECTIVE_THRESHOLD = 0.86
CONTENT_THRESHOLD = 0.9


def recent_mission_history(*, exclude_mission_id=None, limit=HISTORY_LIMIT):
    """Return compact, non-sensitive context for the mission generator."""
    missions = Mission.objects.filter(
        status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
    ).order_by('-scheduled_date', '-created_at')
    if exclude_mission_id:
        missions = missions.exclude(id=exclude_mission_id)
    return [
        {
            'date': mission.scheduled_date.isoformat(),
            'mission_type': mission.mission_type,
            'topic_de': _short(mission.topic_de or mission.title_de),
            'learning_objective_de': _short(
                mission.learning_objective_de or mission.description_de,
            ),
        }
        for mission in missions[:limit]
    ]


def history_instruction(history):
    if not history:
        return ''
    lines = [
        'Avoid duplicating the following existing missions. A broad learning area may recur, but create a genuinely '
        'different learning objective, scenario, question, and solution approach:',
    ]
    lines.extend(
        f"- {item['date']} | {item['mission_type']} | {item['topic_de']} | "
        f"{item['learning_objective_de']}"
        for item in history
    )
    lines.append('Reject your draft and create another one if it substantially repeats one of these missions.')
    return '\n'.join(lines)


def candidate_duplicate(candidate, *, exclude_mission_id=None, additional_candidates=()):
    """Return the duplicate mission/candidate and score, or ``None``.

    The threshold is deliberately high: recurring subject areas are allowed, while
    near-identical titles, scenarios and questions are blocked.
    """
    candidate_text = _candidate_text(candidate)
    if not candidate_text:
        return None

    missions = Mission.objects.filter(
        status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
    )
    if exclude_mission_id:
        missions = missions.exclude(id=exclude_mission_id)
    for mission in missions.iterator():
        mission_candidate = _mission_candidate(mission)
        score = _candidate_similarity(candidate, mission_candidate)
        if score >= SIMILARITY_THRESHOLD:
            return mission, score

    for other in additional_candidates:
        score = _candidate_similarity(candidate, other)
        if score >= SIMILARITY_THRESHOLD:
            return other, score
    return None


def deduplication_snapshot(candidate):
    """Keep only the text needed to compare parallel results in one run."""
    return {
        'mission_type': candidate.get('mission_type'),
        'topic_de': candidate.get('topic_de'),
        'topic_en': candidate.get('topic_en'),
        'learning_objective_de': candidate.get('learning_objective_de'),
        'learning_objective_en': candidate.get('learning_objective_en'),
        'title_de': candidate.get('title_de'),
        'title_en': candidate.get('title_en'),
        'description_de': candidate.get('description_de'),
        'description_en': candidate.get('description_en'),
        'task_de': candidate.get('task_de'),
        'task_en': candidate.get('task_en'),
        'content': _relevant_content(candidate.get('content')),
        'variants': {
            difficulty: {
                'title_de': variant.get('title_de'),
                'title_en': variant.get('title_en'),
                'description_de': variant.get('description_de'),
                'description_en': variant.get('description_en'),
                'content': _relevant_content(variant.get('content')),
            }
            for difficulty, variant in (candidate.get('variants') or {}).items()
            if isinstance(variant, dict)
        },
    }


def _short(value):
    return ' '.join(str(value or '').split())[:HISTORY_TEXT_LIMIT]


def _candidate_text(candidate):
    values = [
        candidate.get('topic_de'), candidate.get('topic_en'),
        candidate.get('learning_objective_de'), candidate.get('learning_objective_en'),
        candidate.get('title_de'), candidate.get('title_en'),
        candidate.get('description_de'), candidate.get('description_en'),
    ]
    for variant in (candidate.get('variants') or {}).values():
        if isinstance(variant, dict):
            values.extend([
                variant.get('title_de'), variant.get('title_en'),
                variant.get('description_de'), variant.get('description_en'),
            ])
    values.append(_content_text(candidate))
    return _normalize(' '.join(str(value) for value in values if value))


def _mission_candidate(mission):
    return {
        'mission_type': mission.mission_type,
        'topic_de': mission.topic_de,
        'topic_en': mission.topic_en,
        'learning_objective_de': mission.learning_objective_de,
        'learning_objective_en': mission.learning_objective_en,
        'title_de': mission.title_de,
        'title_en': mission.title_en,
        'description_de': mission.description_de,
        'description_en': mission.description_en,
        'content': mission.content,
        'variants': mission.variants,
    }


# Keys of the *normalized* candidate content, not of the raw model payload: the
# validators collapse ``question_de``/``question_en`` into one bilingual dict per
# key, so the comparable text sits one level deeper.
_RELEVANT_CONTENT_KEYS = {'question', 'task', 'scenario', 'instructions'}

# Chat challenges carry their task text on the candidate itself, without a
# ``content`` wrapper.
_RELEVANT_TOP_LEVEL_KEYS = ('task_de', 'task_en')


def _relevant_content(content):
    """Return the comparable text fields of a normalized content dict."""
    if not isinstance(content, dict):
        return {}
    relevant = {}
    for key in _RELEVANT_CONTENT_KEYS:
        value = content.get(key)
        if isinstance(value, str):
            relevant[key] = value
        elif isinstance(value, dict):
            texts = {
                language: text for language, text in value.items()
                if isinstance(text, str)
            }
            if texts:
                relevant[key] = texts
    return relevant


def _relevant_content_text(content):
    values = []
    for _, value in sorted(_relevant_content(content).items()):
        if isinstance(value, str):
            values.append(value)
        else:
            values.extend(text for _, text in sorted(value.items()))
    return values


def _content_text(candidate):
    """Return the question and scenario text of a candidate and all its variants."""
    values = list(_relevant_content_text(candidate.get('content')))
    values.extend(candidate.get(key) for key in _RELEVANT_TOP_LEVEL_KEYS)
    for variant in (candidate.get('variants') or {}).values():
        if isinstance(variant, dict):
            values.extend(_relevant_content_text(variant.get('content')))
    return _normalize(' '.join(str(value) for value in values if value))


def _candidate_similarity(left_candidate, right_candidate):
    left_type = left_candidate.get('mission_type')
    right_type = right_candidate.get('mission_type')
    task_types = Mission.TASK_TYPES
    if left_type not in task_types and right_type not in task_types:
        for language in ('de', 'en'):
            left_topic = _normalize(left_candidate.get(f'topic_{language}') or '')
            right_topic = _normalize(right_candidate.get(f'topic_{language}') or '')
            if left_topic and left_topic == right_topic:
                return 1.0
            left_objective = _normalize(left_candidate.get(f'learning_objective_{language}') or '')
            right_objective = _normalize(right_candidate.get(f'learning_objective_{language}') or '')
            if _similarity(left_objective, right_objective) >= LEARNING_OBJECTIVE_THRESHOLD:
                return 1.0
        # A reworded topic around the same question is still the same mission. Task
        # missions are excluded because their instruction text is boilerplate per
        # type - there the case data, which is never compared, carries the variance.
        if _similarity(_content_text(left_candidate), _content_text(right_candidate)) >= CONTENT_THRESHOLD:
            return 1.0
    return _similarity(_candidate_text(left_candidate), _candidate_text(right_candidate))


def _normalize(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def _similarity(left, right):
    if not left or not right:
        return 0.0
    # ``autojunk`` treats any character occurring in more than 1% of a sequence as
    # noise once it is longer than 200 elements. On mission-sized texts that is
    # every common letter, which collapsed the ratio to near zero for identical input.
    sequence_score = SequenceMatcher(None, left, right, autojunk=False).ratio()
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    token_score = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    if token_score >= TOKEN_OVERLAP_THRESHOLD:
        return max(sequence_score, token_score)
    return sequence_score
