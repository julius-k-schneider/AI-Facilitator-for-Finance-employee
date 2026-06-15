from django.conf import settings
from django.db import models


class Profile(models.Model):
    ROLE_USER = 'user'
    ROLE_CONTROLLER = 'controller'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_CONTENT_CREATOR = 'content_creator'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_CONTROLLER, 'Controller'),
        (ROLE_ACCOUNTANT, 'Accountant'),
        (ROLE_CONTENT_CREATOR, 'Content Creator'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_ACCOUNTANT)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    onboarding_progress = models.JSONField(default=list, blank=True)
    mission_scores = models.JSONField(default=dict, blank=True)
    progress_updated_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_points(self):
        return sum(max(0, int(score)) for score in (self.mission_scores or {}).values())

    @property
    def completed_mission_count(self):
        return sum(1 for score in (self.mission_scores or {}).values() if int(score) > 0)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class Mission(models.Model):
    TYPE_SINGLE_CHOICE = 'single_choice'
    TYPE_MULTIPLE_CHOICE = 'multiple_choice'
    TYPE_COMPLIANCE_DECISION = 'compliance_decision'
    TYPE_PROMPT_SELECTION = 'prompt_selection'
    TYPE_PROMPT_RANKING = 'prompt_ranking'
    TYPE_COMPLIANCE_TRAFFIC_LIGHT = 'compliance_traffic_light'
    TYPE_CHOICES = [
        (TYPE_SINGLE_CHOICE, 'Single Choice'),
        (TYPE_MULTIPLE_CHOICE, 'Multiple Choice'),
        (TYPE_COMPLIANCE_DECISION, 'Compliance Decision'),
        (TYPE_PROMPT_SELECTION, 'Prompt Selection'),
        (TYPE_PROMPT_RANKING, 'Prompt Ranking'),
        (TYPE_COMPLIANCE_TRAFFIC_LIGHT, 'Compliance Traffic Light'),
    ]
    CHOICE_TYPES = {
        TYPE_SINGLE_CHOICE,
        TYPE_MULTIPLE_CHOICE,
        TYPE_COMPLIANCE_DECISION,
        TYPE_PROMPT_SELECTION,
        TYPE_PROMPT_RANKING,
        TYPE_COMPLIANCE_TRAFFIC_LIGHT,
    }

    STATUS_REVIEW = 'review'
    STATUS_PUBLISHED = 'published'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_REVIEW, 'Review'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    mission_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    scheduled_date = models.DateField(db_index=True)
    title_de = models.CharField(max_length=160)
    title_en = models.CharField(max_length=160)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    content = models.JSONField(default=dict)
    max_points = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PUBLISHED, db_index=True)
    generated_by_ai = models.BooleanField(default=False)
    generation_batch_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_missions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_missions',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('scheduled_date', 'created_at', 'id')

    def __str__(self):
        return f'{self.scheduled_date}: {self.title_de}'


class MissionAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_attempts',
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='attempts')
    answer = models.JSONField(default=dict)
    score = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'mission'), name='unique_user_mission_attempt'),
        ]
        ordering = ('-completed_at',)

    def __str__(self):
        return f'{self.user} - {self.mission} ({self.score})'


class WeeklyLeaderboardSnapshot(models.Model):
    week_start = models.DateField(unique=True)
    week_end = models.DateField()
    entries = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-week_start',)

    def __str__(self):
        return f'{self.week_start} - {self.week_end}'
