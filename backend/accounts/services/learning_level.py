from statistics import mean

from accounts.models import Mission, MissionAttempt


RECENT_ATTEMPTS_LIMIT = 10


def get_learning_level(user):
    attempts = (
        MissionAttempt.objects
        .filter(user=user)
        .order_by('-completed_at')[:RECENT_ATTEMPTS_LIMIT]
    )

    scores = [attempt.score for attempt in attempts]

    if len(scores) < 3:
        return Mission.DIFFICULTY_BEGINNER

    average_score = mean(scores)

    if average_score >= 85:
        return Mission.DIFFICULTY_ADVANCED

    if average_score >= 60:
        return Mission.DIFFICULTY_INTERMEDIATE

    return Mission.DIFFICULTY_BEGINNER


def get_user_learning_profile(user):
    return {
        "role": user.profile.role,
        "difficulty": get_learning_level(user),
    }