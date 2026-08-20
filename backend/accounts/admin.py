from django.contrib import admin

from .models import (
    DailyMissionReminder,
    Mission,
    MissionAssignment,
    MissionAttempt,
    Profile,
    SkillProgressionSettings,
    WeeklyLeaderboardSnapshot,
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
