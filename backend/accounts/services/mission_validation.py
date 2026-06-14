from datetime import date

from accounts.models import Mission


class MissionValidationError(ValueError):
    pass


ALLOWED_AI_TYPES = {
    Mission.TYPE_MULTIPLE_CHOICE,
    Mission.TYPE_COMPLIANCE_DECISION,
    Mission.TYPE_PROMPT_SELECTION,
}


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise MissionValidationError(f'{field} is required')
    return value.strip()


def validate_generated_payload(payload, target_slots):
    if not isinstance(payload, dict) or not isinstance(payload.get('missions'), list):
        raise MissionValidationError('response must contain a missions array')

    expected_count = sum(target_slots.values())
    if len(payload['missions']) != expected_count:
        raise MissionValidationError(f'expected {expected_count} missions')

    normalized = []
    counts = {target_date: 0 for target_date in target_slots}
    for index, item in enumerate(payload['missions']):
        if not isinstance(item, dict):
            raise MissionValidationError(f'mission {index + 1} must be an object')
        try:
            scheduled_date = date.fromisoformat(str(item.get('date', '')))
        except ValueError as error:
            raise MissionValidationError(f'mission {index + 1} has an invalid date') from error
        if scheduled_date not in target_slots:
            raise MissionValidationError(f'mission {index + 1} is outside the target week')

        mission_type = item.get('type')
        if mission_type not in ALLOWED_AI_TYPES:
            raise MissionValidationError(f'mission {index + 1} has an unsupported type')

        try:
            points = int(item.get('points'))
        except (TypeError, ValueError) as error:
            raise MissionValidationError(f'mission {index + 1} has invalid points') from error
        if points < 10 or points > 50:
            raise MissionValidationError(f'mission {index + 1} points must be between 10 and 50')

        content = item.get('content')
        if not isinstance(content, dict):
            raise MissionValidationError(f'mission {index + 1} content is required')
        options_de = content.get('options_de')
        options_en = content.get('options_en')
        if not isinstance(options_de, list) or not isinstance(options_en, list):
            raise MissionValidationError(f'mission {index + 1} options are required')
        if len(options_de) < 2 or len(options_de) > 6 or len(options_de) != len(options_en):
            raise MissionValidationError(f'mission {index + 1} must have 2 to 6 bilingual options')
        options = [
            {
                'de': required_text(option_de, f'mission {index + 1} option_de'),
                'en': required_text(option_en, f'mission {index + 1} option_en'),
            }
            for option_de, option_en in zip(options_de, options_en)
        ]
        raw_correct_indices = content.get('correct_option_indices')
        if raw_correct_indices is None and content.get('correct_option_index') is not None:
            raw_correct_indices = [content.get('correct_option_index')]
        try:
            correct_indices = sorted({int(value) for value in (raw_correct_indices or [])})
        except (TypeError, ValueError) as error:
            raise MissionValidationError(f'mission {index + 1} has an invalid correct answer') from error
        if not correct_indices or any(value < 0 or value >= len(options) for value in correct_indices):
            raise MissionValidationError(f'mission {index + 1} correct answer is outside the options')
        if mission_type != Mission.TYPE_MULTIPLE_CHOICE and len(correct_indices) != 1:
            raise MissionValidationError(f'mission {index + 1} requires exactly one correct answer')

        normalized.append({
            'scheduled_date': scheduled_date,
            'mission_type': mission_type,
            'title_de': required_text(item.get('title_de'), f'mission {index + 1} title_de'),
            'title_en': required_text(item.get('title_en'), f'mission {index + 1} title_en'),
            'description_de': required_text(item.get('description_de'), f'mission {index + 1} description_de'),
            'description_en': required_text(item.get('description_en'), f'mission {index + 1} description_en'),
            'max_points': points,
            'content': {
                'question': {
                    'de': required_text(content.get('question_de'), f'mission {index + 1} question_de'),
                    'en': required_text(content.get('question_en'), f'mission {index + 1} question_en'),
                },
                'options': options,
                'correct_indices': correct_indices,
                'feedback': {
                    'de': required_text(content.get('feedback_de'), f'mission {index + 1} feedback_de'),
                    'en': required_text(content.get('feedback_en'), f'mission {index + 1} feedback_en'),
                },
            },
        })
        counts[scheduled_date] += 1
        if counts[scheduled_date] > target_slots[scheduled_date]:
            raise MissionValidationError(f'too many missions for {scheduled_date.isoformat()}')

    if counts != target_slots:
        raise MissionValidationError('missions do not fill the requested daily slots')
    return normalized
