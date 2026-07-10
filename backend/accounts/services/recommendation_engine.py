from collections import defaultdict

from accounts.models import Mission

from accounts.services.learning_level import get_learning_level


MISSION_SKILLS = {
    Mission.TYPE_PROMPT_SELECTION: "Prompt Engineering",
    Mission.TYPE_PROMPT_RANKING: "Prompt Engineering",

    Mission.TYPE_COMPLIANCE_DECISION: "AI Compliance",
    Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT: "AI Compliance",

    Mission.TYPE_SINGLE_CHOICE: "AI Fundamentals",
    Mission.TYPE_MULTIPLE_CHOICE: "AI Fundamentals",
}


SKILL_RECOMMENDATIONS = {
    "Prompt Engineering":
        "Practice writing clearer and more specific prompts.",

    "AI Compliance":
        "Review confidentiality and responsible AI usage before using AI tools.",

    "AI Fundamentals":
        "Strengthen your understanding of AI capabilities and limitations.",
}



def get_skill_name(mission):
    return MISSION_SKILLS.get(
        mission.mission_type,
        "General AI"
    )

def get_user_skill_scores(user):
    attempts = (
        user.mission_attempts
        .select_related('mission')
        .order_by('-completed_at')
    )

    skill_scores = defaultdict(list)

    for attempt in attempts:
        skill_name = get_skill_name(attempt.mission)

        if attempt.mission.max_points > 0:
            percentage_score = (attempt.score / attempt.mission.max_points) * 100
        else:
            percentage_score = 0

        skill_scores[skill_name].append(percentage_score)

    return {
        skill: round(sum(scores) / len(scores), 1)
        for skill, scores in skill_scores.items()
        if scores
    }

def get_user_strengths(user):
    skill_scores = get_user_skill_scores(user)

    return [
        skill
        for skill, score in skill_scores.items()
        if score >= 80
    ]

def get_user_weaknesses(user):
    skill_scores = get_user_skill_scores(user)

    return [
        skill
        for skill, score in skill_scores.items()
        if score < 60
    ]

def get_learning_insights(user):
    strengths = get_user_strengths(user)
    weaknesses = get_user_weaknesses(user)
    skill_scores = get_user_skill_scores(user)

    recommended_skill = None

    if weaknesses:
        recommended_skill = min(
            weaknesses,
            key=lambda skill: skill_scores.get(skill, 100)
        )

    recommendation = None

    if recommended_skill:
        recommendation = SKILL_RECOMMENDATIONS.get(recommended_skill)

    return {
        "level": get_learning_level(user),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommended_next_step": {
            "skill": recommended_skill,
            "reason": "Average score below 60%",
            "recommendation": recommendation,
        } if recommended_skill else None,
    }