from django.contrib import admin

from .models import DailyMissionReminder, Mission, MissionAttempt, Profile, WeeklyLeaderboardSnapshot


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'onboarding_completed', 'total_points', 'progress_updated_at')
    list_filter = ('role', 'onboarding_completed')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('onboarding_completed_at', 'progress_updated_at')

@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('title_de', 'mission_type', 'target_role', 'difficulty', 'scheduled_date', 'status', 'generated_by_ai', 'max_points', 'created_by')
    list_filter = ('status','generated_by_ai', 'mission_type','target_role', 'difficulty', 'scheduled_date')
    search_fields = ('title_de', 'title_en')

@admin.register(MissionAttempt)
class MissionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'score', 'completed_at')
    list_filter = ('mission__scheduled_date',)
    readonly_fields = ('completed_at',)


@admin.register(WeeklyLeaderboardSnapshot)
class WeeklyLeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(DailyMissionReminder)
class DailyMissionReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_date', 'mission_count', 'missing_count', 'sent_at')
    list_filter = ('reminder_date',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('sent_at',)
