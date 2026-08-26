from django.contrib import admin

from .models import (
    DailyMissionReminder,
    GenerationRun,
    Mission,
    MissionAssignment,
    MissionAttempt,
    Profile,
    ResearchItem,
    ResearchRun,
    ResearchSchedule,
    SkillProgressionSettings,
    WeeklyLeaderboardSnapshot,
)


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'status', 'requested_by', 'week_start', 'created_at', 'completed_at')
    list_filter = ('kind', 'status', 'created_at')
    search_fields = ('id', 'n8n_execution_id', 'requested_by__username', 'requested_by__email')
    readonly_fields = (
        'id', 'request_payload', 'result_payload', 'review_report', 'research_context',
        'result_metadata', 'created_at', 'updated_at', 'started_at', 'completed_at', 'failed_at',
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'skill_level', 'onboarding_completed', 'total_points', 'progress_updated_at')
    list_filter = ('role', 'skill_level', 'onboarding_completed')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('onboarding_completed_at', 'progress_updated_at', 'skill_level_entered_at')


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('title_de', 'mission_type', 'scheduled_date', 'status', 'generated_by_ai', 'max_points', 'created_by')
    list_filter = ('status', 'generated_by_ai', 'mission_type', 'scheduled_date')
    search_fields = ('title_de', 'title_en')


@admin.register(MissionAttempt)
class MissionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'difficulty', 'score', 'max_points', 'completed_at')
    list_filter = ('difficulty', 'mission__scheduled_date')
    readonly_fields = ('completed_at',)


@admin.register(WeeklyLeaderboardSnapshot)
class WeeklyLeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'difficulty', 'created_at')
    list_filter = ('difficulty',)
    readonly_fields = ('created_at',)


@admin.register(DailyMissionReminder)
class DailyMissionReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_date', 'mission_count', 'missing_count', 'sent_at')
    list_filter = ('reminder_date',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('sent_at',)


@admin.register(MissionAssignment)
class MissionAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'difficulty', 'assigned_at')
    list_filter = ('difficulty',)
    readonly_fields = ('assigned_at',)


@admin.register(SkillProgressionSettings)
class SkillProgressionSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'automatic_progression_enabled',
        'evaluation_window',
        'minimum_missions',
        'promotion_threshold',
        'demotion_threshold',
        'updated_at',
    )

    def has_add_permission(self, request):
        return not SkillProgressionSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResearchItem)
class ResearchItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_name', 'confidence', 'relevance_score', 'eligible', 'valid_until')
    list_filter = ('eligible', 'confidence', 'language')
    search_fields = ('title', 'source_name', 'summary_de', 'summary_en', 'item_key')


@admin.register(ResearchRun)
class ResearchRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'trigger', 'status', 'requested_by', 'created_at', 'completed_at')
    list_filter = ('trigger', 'status')
    readonly_fields = ('id', 'result', 'created_at', 'updated_at', 'started_at', 'completed_at')


@admin.register(ResearchSchedule)
class ResearchScheduleAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'weekday', 'run_time', 'timezone_name', 'last_triggered_at', 'updated_at')

    def has_add_permission(self, request):
        return not ResearchSchedule.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
