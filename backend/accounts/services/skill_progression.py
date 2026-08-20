from django.db import transaction
from django.utils import timezone

from accounts.models import Mission, MissionAttempt, Profile, SkillProgressionSettings


SKILL_TO_DIFFICULTY = {
    Profile.SKILL_BEGINNER: Mission.DIFFICULTY_EASY,
    Profile.SKILL_ADVANCED: Mission.DIFFICULTY_MEDIUM,
    Profile.SKILL_PRO: Mission.DIFFICULTY_HARD,
}
DIFFICULTY_TO_SKILL = {difficulty: skill for skill, difficulty in SKILL_TO_DIFFICULTY.items()}

SKILL_ORDER = [
    Profile.SKILL_BEGINNER,
    Profile.SKILL_ADVANCED,
    Profile.SKILL_PRO,
]


def difficulty_for_skill(skill_level):
    return SKILL_TO_DIFFICULTY.get(skill_level, Mission.DIFFICULTY_EASY)


def skill_for_difficulty(difficulty):
    return DIFFICULTY_TO_SKILL.get(difficulty, Profile.SKILL_BEGINNER)


def _relevant_attempts(profile):
    return MissionAttempt.objects.filter(
        user=profile.user,
        difficulty=difficulty_for_skill(profile.skill_level),
        completed_at__gte=profile.skill_level_entered_at,
        max_points__gt=0,
    ).order_by('-completed_at', '-id')


def progression_snapshot(profile, settings_object=None):
    settings_object = settings_object or SkillProgressionSettings.load()
    attempts = _relevant_attempts(profile)
    relevant_count = attempts.count()
    recent = list(attempts.values_list('score', 'max_points')[:settings_object.evaluation_window])
    average = None
    if recent:
        average = round(sum(score * 100 / max_points for score, max_points in recent) / len(recent), 1)
    return {
        'skill_level': profile.skill_level,
        'difficulty': difficulty_for_skill(profile.skill_level),
        'level_entered_at': profile.skill_level_entered_at.isoformat(),
        'relevant_completed_missions': relevant_count,
        'evaluation_window': settings_object.evaluation_window,
        'minimum_missions': settings_object.minimum_missions,
        'current_average': average,
        'automatic_progression_enabled': settings_object.automatic_progression_enabled,
        'promotion_threshold': settings_object.promotion_threshold,
        'demotion_threshold': settings_object.demotion_threshold,
    }


def evaluate_skill_progression(profile):
    """Evaluate one transition after a persisted attempt.

    The caller should invoke this inside the same transaction as attempt creation.
    A level change moves the phase checkpoint beyond the triggering attempt, so
    historical results can never trigger a second immediate transition.
    """
    settings_object = SkillProgressionSettings.load()
    before = progression_snapshot(profile, settings_object)
    if not settings_object.automatic_progression_enabled:
        return None, before
    if before['relevant_completed_missions'] < settings_object.minimum_missions:
        return None, before
    average = before['current_average']
    current_index = SKILL_ORDER.index(profile.skill_level)
    next_level = profile.skill_level
    direction = None
    if average >= settings_object.promotion_threshold and current_index < len(SKILL_ORDER) - 1:
        next_level = SKILL_ORDER[current_index + 1]
        direction = 'promotion'
    elif average < settings_object.demotion_threshold and current_index > 0:
        next_level = SKILL_ORDER[current_index - 1]
        direction = 'demotion'
    if next_level == profile.skill_level:
        return None, before

    previous_level = profile.skill_level
    profile.skill_level = next_level
    profile.skill_level_entered_at = timezone.now()
    profile.save(update_fields=['skill_level', 'skill_level_entered_at'])
    change = {
        'direction': direction,
        'previous_level': previous_level,
        'new_level': next_level,
        'new_difficulty': difficulty_for_skill(next_level),
    }
    return change, progression_snapshot(profile, settings_object)


@transaction.atomic
def set_skill_level_manually(profile, skill_level):
    locked = Profile.objects.select_for_update().get(pk=profile.pk)
    changed = locked.skill_level != skill_level
    if changed:
        locked.skill_level = skill_level
        locked.skill_level_entered_at = timezone.now()
        locked.save(update_fields=['skill_level', 'skill_level_entered_at'])
    return locked, changed
