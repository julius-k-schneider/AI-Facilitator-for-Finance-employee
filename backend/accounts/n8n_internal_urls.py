from django.urls import path

from . import n8n_internal_views


urlpatterns = [
    path('validate-mission/', n8n_internal_views.validate_mission_view, name='n8n_validate_mission'),
    path('generation-callback/', n8n_internal_views.generation_callback_view, name='n8n_generation_callback'),
    path('research/sync/', n8n_internal_views.research_sync_view, name='n8n_research_sync'),
    path('research/current/', n8n_internal_views.current_research_view, name='n8n_current_research'),
    path('research/callback/', n8n_internal_views.research_callback_view, name='n8n_research_callback'),
]
