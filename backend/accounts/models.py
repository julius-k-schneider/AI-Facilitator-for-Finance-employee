from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


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

    SKILL_BEGINNER = 'beginner'
    SKILL_ADVANCED = 'advanced'
    SKILL_PRO = 'pro'
    SKILL_LEVEL_CHOICES = [
        (SKILL_BEGINNER, 'Beginner'),
        (SKILL_ADVANCED, 'Advanced'),
        (SKILL_PRO, 'Pro'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_ACCOUNTANT)
    skill_level = models.CharField(max_length=16, choices=SKILL_LEVEL_CHOICES, default=SKILL_BEGINNER)
    skill_level_entered_at = models.DateTimeField(default=timezone.now)
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
    TARGET_ALL = 'all'
    TARGET_ACCOUNTANT = Profile.ROLE_ACCOUNTANT
    TARGET_CONTROLLER = Profile.ROLE_CONTROLLER
    TARGET_ROLE_CHOICES = [
        (TARGET_ALL, 'All finance roles'),
        (TARGET_ACCOUNTANT, 'Accountant'),
        (TARGET_CONTROLLER, 'Controller'),
    ]
    DIFFICULTY_EASY = 'easy'
    DIFFICULTY_MEDIUM = 'medium'
    DIFFICULTY_HARD = 'hard'
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_EASY, 'Easy'),
        (DIFFICULTY_MEDIUM, 'Medium'),
        (DIFFICULTY_HARD, 'Hard'),
    ]
    DIFFICULTIES = tuple(value for value, _label in DIFFICULTY_CHOICES)

    TYPE_SINGLE_CHOICE = 'single_choice'
    TYPE_MULTIPLE_CHOICE = 'multiple_choice'
    TYPE_COMPLIANCE_DECISION = 'compliance_decision'
    TYPE_PROMPT_SELECTION = 'prompt_selection'
    TYPE_PROMPT_RANKING = 'prompt_ranking'
    TYPE_COMPLIANCE_TRAFFIC_LIGHT = 'compliance_traffic_light'
    TYPE_BULK_CATEGORIZATION = 'bulk_categorization'
    TYPE_PLAN_ACTUAL_DEVIATION = 'plan_actual_deviation'
    TYPE_DUPLICATE_PAYMENT_HUNT = 'duplicate_payment_hunt'
    TYPE_INVOICE_EXTRACTION = 'invoice_extraction'
    TYPE_CHOICES = [
        (TYPE_SINGLE_CHOICE, 'Single Choice'),
        (TYPE_MULTIPLE_CHOICE, 'Multiple Choice'),
        (TYPE_COMPLIANCE_DECISION, 'Compliance Decision'),
        (TYPE_PROMPT_SELECTION, 'Prompt Selection'),
        (TYPE_PROMPT_RANKING, 'Prompt Ranking'),
        (TYPE_COMPLIANCE_TRAFFIC_LIGHT, 'Compliance Traffic Light'),
        (TYPE_BULK_CATEGORIZATION, 'Bulk Categorization'),
        (TYPE_PLAN_ACTUAL_DEVIATION, 'Plan vs. Actual Deviation'),
        (TYPE_DUPLICATE_PAYMENT_HUNT, 'Duplicate Payment Hunt'),
        (TYPE_INVOICE_EXTRACTION, 'Invoice Extraction'),
    ]
    # Quiz-style types share a common choice/index scoring model.
    CHOICE_TYPES = {
        TYPE_SINGLE_CHOICE,
        TYPE_MULTIPLE_CHOICE,
        TYPE_COMPLIANCE_DECISION,
        TYPE_PROMPT_SELECTION,
        TYPE_PROMPT_RANKING,
        TYPE_COMPLIANCE_TRAFFIC_LIGHT,
    }
    # Task-style types carry a case plus typed result fields scored deterministically.
    TASK_TYPES = {
        TYPE_BULK_CATEGORIZATION,
        TYPE_PLAN_ACTUAL_DEVIATION,
        TYPE_DUPLICATE_PAYMENT_HUNT,
        TYPE_INVOICE_EXTRACTION,
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
    target_role = models.CharField(max_length=16, choices=TARGET_ROLE_CHOICES, default=TARGET_ALL, db_index=True)
    scheduled_date = models.DateField(db_index=True)
    title_de = models.CharField(max_length=160)
    title_en = models.CharField(max_length=160)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    content = models.JSONField(default=dict)
    max_points = models.PositiveIntegerField(default=100)
    topic_de = models.CharField(max_length=200, blank=True, default='')
    topic_en = models.CharField(max_length=200, blank=True, default='')
    learning_objective_de = models.TextField(blank=True, default='')
    learning_objective_en = models.TextField(blank=True, default='')
    variants = models.JSONField(default=dict, blank=True)
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

    @property
    def has_difficulty_variants(self):
        return isinstance(self.variants, dict) and set(self.variants) == set(self.DIFFICULTIES)


class MissionAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_attempts',
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='attempts')
    answer = models.JSONField(default=dict)
    score = models.PositiveIntegerField(default=0)
    max_points = models.PositiveIntegerField(default=100)
    difficulty = models.CharField(
        max_length=16,
        choices=Mission.DIFFICULTY_CHOICES,
        null=True,
        blank=True,
        db_index=True,
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'mission'), name='unique_user_mission_attempt'),
        ]
        ordering = ('-completed_at',)

    def __str__(self):
        return f'{self.user} - {self.mission} ({self.score})'


class MissionAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_assignments',
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='assignments')
    difficulty = models.CharField(max_length=16, choices=Mission.DIFFICULTY_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'mission'), name='unique_user_mission_assignment'),
        ]
        ordering = ('assigned_at',)

    def __str__(self):
        return f'{self.user} - {self.mission} ({self.difficulty})'


class SkillProgressionSettings(models.Model):
    automatic_progression_enabled = models.BooleanField(default=True)
    evaluation_window = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    minimum_missions = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    promotion_threshold = models.PositiveSmallIntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    demotion_threshold = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'skill progression settings'
        verbose_name_plural = 'skill progression settings'

    def clean(self):
        if self.demotion_threshold >= self.promotion_threshold:
            raise ValidationError({'demotion_threshold': 'Must be lower than the promotion threshold.'})

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        settings_object, _created = cls.objects.get_or_create(pk=1)
        return settings_object

    def __str__(self):
        return 'Global skill progression settings'


class DailyMissionReminder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_mission_reminders',
    )
    reminder_date = models.DateField(db_index=True)
    mission_count = models.PositiveIntegerField(default=0)
    missing_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'reminder_date'), name='unique_daily_mission_reminder'),
        ]
        ordering = ('-sent_at',)

    def __str__(self):
        return f'{self.user} - {self.reminder_date}'


class WeeklyLeaderboardSnapshot(models.Model):
    week_start = models.DateField()
    week_end = models.DateField()
    difficulty = models.CharField(max_length=16, choices=Mission.DIFFICULTY_CHOICES, blank=True, default='')
    entries = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-week_start',)
        constraints = [
            models.UniqueConstraint(fields=('week_start', 'difficulty'), name='unique_weekly_leaderboard_difficulty'),
        ]

    def __str__(self):
        return f'{self.week_start} - {self.week_end}'


class AgentChat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_chats',
    )
    title = models.CharField(max_length=120, blank=True, default='')
    messages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at', '-id')

    def __str__(self):
        return f'{self.user} - {self.title}'
