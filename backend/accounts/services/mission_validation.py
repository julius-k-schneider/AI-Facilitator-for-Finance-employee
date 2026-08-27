import re
from datetime import date
from difflib import SequenceMatcher

from accounts.models import Mission


class MissionValidationError(ValueError):
    pass


ALLOWED_AI_TYPES = {
    Mission.TYPE_SINGLE_CHOICE,
    Mission.TYPE_MULTIPLE_CHOICE,
    Mission.TYPE_PROMPT_SELECTION,
    Mission.TYPE_PROMPT_RANKING,
}


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise MissionValidationError(f'{field} is required')
    return value.strip()


def required_micro_learning(content, field_prefix):
    micro_learning = {
        'de': required_text(content.get('micro_learning_de'), f'{field_prefix} micro_learning_de'),
        'en': required_text(content.get('micro_learning_en'), f'{field_prefix} micro_learning_en'),
    }
    for language, text in micro_learning.items():
        if len(text) < 120:
            raise MissionValidationError(f'{field_prefix} micro_learning_{language} is too short')
        if len(text) > 900:
            raise MissionValidationError(f'{field_prefix} micro_learning_{language} is too long')
    return micro_learning


def normalized_text(value):
    return ' '.join(re.findall(r'\w+', value.lower()))


def ensure_distinct_explanations(feedback, micro_learning, field_prefix):
    for language in ('de', 'en'):
        normalized_feedback = normalized_text(feedback[language])
        normalized_learning = normalized_text(micro_learning[language])
        similarity = SequenceMatcher(None, normalized_feedback, normalized_learning).ratio()
        if normalized_feedback == normalized_learning or similarity >= 0.72:
            raise MissionValidationError(
                f'{field_prefix} feedback_{language} and micro_learning_{language} are too similar'
            )


def normalize_generated_variant(raw_variant, mission_type, field_prefix):
    if not isinstance(raw_variant, dict):
        raise MissionValidationError(f'{field_prefix} must be an object')
    try:
        points = int(raw_variant.get('points'))
    except (TypeError, ValueError) as error:
        raise MissionValidationError(f'{field_prefix} has invalid points') from error
    if points < 10 or points > 50:
        raise MissionValidationError(f'{field_prefix} points must be between 10 and 50')

    content = raw_variant.get('content')
    if not isinstance(content, dict):
        raise MissionValidationError(f'{field_prefix} content is required')
    options_de = content.get('options_de')
    options_en = content.get('options_en')
    if not isinstance(options_de, list) or not isinstance(options_en, list):
        raise MissionValidationError(f'{field_prefix} options are required')
    minimum_options = 3 if mission_type == Mission.TYPE_PROMPT_RANKING else 2
    maximum_options = 4 if mission_type == Mission.TYPE_PROMPT_RANKING else 6
    if len(options_de) < minimum_options or len(options_de) > maximum_options or len(options_de) != len(options_en):
        raise MissionValidationError(
            f'{field_prefix} must have {minimum_options} to {maximum_options} bilingual options'
        )
    options = [
        {
            'de': required_text(option_de, f'{field_prefix} option_de'),
            'en': required_text(option_en, f'{field_prefix} option_en'),
        }
        for option_de, option_en in zip(options_de, options_en)
    ]
    normalized_content = {
        'question': {
            'de': required_text(content.get('question_de'), f'{field_prefix} question_de'),
            'en': required_text(content.get('question_en'), f'{field_prefix} question_en'),
        },
        'options': options,
    }
    if mission_type == Mission.TYPE_PROMPT_RANKING:
        try:
            correct_order = [int(value) for value in content.get('correct_order', [])]
        except (TypeError, ValueError) as error:
            raise MissionValidationError(f'{field_prefix} has an invalid ranking') from error
        if sorted(correct_order) != list(range(len(options))):
            raise MissionValidationError(f'{field_prefix} ranking must contain every option exactly once')
        normalized_content['correct_order'] = correct_order
    else:
        raw_correct_indices = content.get('correct_option_indices')
        if raw_correct_indices is None and content.get('correct_option_index') is not None:
            raw_correct_indices = [content.get('correct_option_index')]
        try:
            correct_indices = sorted({int(value) for value in (raw_correct_indices or [])})
        except (TypeError, ValueError) as error:
            raise MissionValidationError(f'{field_prefix} has an invalid correct answer') from error
        if not correct_indices or any(value < 0 or value >= len(options) for value in correct_indices):
            raise MissionValidationError(f'{field_prefix} correct answer is outside the options')
        if mission_type != Mission.TYPE_MULTIPLE_CHOICE and len(correct_indices) != 1:
            raise MissionValidationError(f'{field_prefix} requires exactly one correct answer')
        normalized_content['correct_indices'] = correct_indices
    normalized_content['feedback'] = {
        'de': required_text(content.get('feedback_de'), f'{field_prefix} feedback_de'),
        'en': required_text(content.get('feedback_en'), f'{field_prefix} feedback_en'),
    }
    normalized_content['micro_learning'] = required_micro_learning(content, field_prefix)
    ensure_distinct_explanations(normalized_content['feedback'], normalized_content['micro_learning'], field_prefix)

    return {
        'title_de': required_text(raw_variant.get('title_de'), f'{field_prefix} title_de'),
        'title_en': required_text(raw_variant.get('title_en'), f'{field_prefix} title_en'),
        'description_de': required_text(raw_variant.get('description_de'), f'{field_prefix} description_de'),
        'description_en': required_text(raw_variant.get('description_en'), f'{field_prefix} description_en'),
        'max_points': points,
        'content': normalized_content,
    }


def validate_generated_payload(payload, target_slots):
    if not isinstance(payload, dict) or not isinstance(payload.get('missions'), list):
        raise MissionValidationError('response must contain a missions array')
    expected_count = sum(target_slots.values())
    if len(payload['missions']) != expected_count:
        raise MissionValidationError(f'expected {expected_count} missions')

    normalized = []
    counts = {target_date: 0 for target_date in target_slots}
    required_difficulties = set(Mission.DIFFICULTIES)
    for index, item in enumerate(payload['missions']):
        prefix = f'mission {index + 1}'
        if not isinstance(item, dict):
            raise MissionValidationError(f'{prefix} must be an object')
        try:
            scheduled_date = date.fromisoformat(str(item.get('date', '')))
        except ValueError as error:
            raise MissionValidationError(f'{prefix} has an invalid date') from error
        if scheduled_date not in target_slots:
            raise MissionValidationError(f'{prefix} is outside the target week')
        mission_type = item.get('type')
        if mission_type not in ALLOWED_AI_TYPES:
            raise MissionValidationError(f'{prefix} has an unsupported type')
        raw_variants = item.get('variants')
        if not isinstance(raw_variants, dict) or set(raw_variants) != required_difficulties:
            raise MissionValidationError(f'{prefix} must contain exactly easy, medium, and hard variants')
        variants = {
            difficulty: normalize_generated_variant(raw_variants[difficulty], mission_type, f'{prefix} {difficulty}')
            for difficulty in Mission.DIFFICULTIES
        }
        easy = variants[Mission.DIFFICULTY_EASY]
        normalized.append({
            'scheduled_date': scheduled_date,
            'mission_type': mission_type,
            'topic_de': required_text(item.get('topic_de'), f'{prefix} topic_de'),
            'topic_en': required_text(item.get('topic_en'), f'{prefix} topic_en'),
            'learning_objective_de': required_text(
                item.get('learning_objective_de'), f'{prefix} learning_objective_de'
            ),
            'learning_objective_en': required_text(
                item.get('learning_objective_en'), f'{prefix} learning_objective_en'
            ),
            'variants': variants,
            # Existing schedule/review code keeps using these fields as a safe
            # preview fallback; learner delivery resolves the assigned variant.
            **easy,
        })
        counts[scheduled_date] += 1
        if counts[scheduled_date] > target_slots[scheduled_date]:
            raise MissionValidationError(f'too many missions for {scheduled_date.isoformat()}')
    if counts != target_slots:
        raise MissionValidationError('missions do not fill the requested daily slots')
    return normalized
