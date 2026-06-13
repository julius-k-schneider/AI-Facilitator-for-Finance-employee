from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'onboarding_completed', 'total_points', 'progress_updated_at')
    list_filter = ('role', 'onboarding_completed')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('onboarding_completed_at', 'progress_updated_at')
