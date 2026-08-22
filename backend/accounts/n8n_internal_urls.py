from django.urls import path

from . import n8n_internal_views


urlpatterns = [
    path('validate-mission/', n8n_internal_views.validate_mission_view, name='n8n_validate_mission'),
    path('generation-callback/', n8n_internal_views.generation_callback_view, name='n8n_generation_callback'),
]
