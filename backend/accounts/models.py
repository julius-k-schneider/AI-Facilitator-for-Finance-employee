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
    TYPE_CHOICES = [
        (TYPE_SINGLE_CHOICE, 'Single Choice'),
    ]

    mission_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    scheduled_date = models.DateField(db_index=True)
    title_de = models.CharField(max_length=160)
    title_en = models.CharField(max_length=160)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    content = models.JSONField(default=dict)
    max_points = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_missions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
