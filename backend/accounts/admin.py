from django.contrib import admin

from .models import Mission, MissionAttempt, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'onboarding_completed', 'total_points', 'progress_updated_at')
    list_filter = ('role', 'onboarding_completed')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('onboarding_completed_at', 'progress_updated_at')


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('title_de', 'mission_type', 'scheduled_date', 'status', 'generated_by_ai', 'max_points', 'created_by')
    list_filter = ('status', 'generated_by_ai', 'mission_type', 'scheduled_date')
    search_fields = ('title_de', 'title_en')


@admin.register(MissionAttempt)
class MissionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'score', 'completed_at')
    list_filter = ('mission__scheduled_date',)
    readonly_fields = ('completed_at',)
