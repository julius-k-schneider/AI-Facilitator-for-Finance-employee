from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('user/', views.user_view, name='user'),
    path('users/', views.users_view, name='users'),
    path('users/<int:user_id>/role/', views.update_user_role_view, name='update_user_role'),
    path('users/<int:user_id>/', views.delete_user_view, name='delete_user'),
    path('register/', views.register_view, name='register'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('onboarding/progress/', views.onboarding_progress_view, name='onboarding_progress'),
    path('onboarding/complete/', views.onboarding_complete_view, name='onboarding_complete'),
    path('progress/', views.progress_view, name='progress'),
    path('progress/complete/', views.complete_mission_view, name='complete_mission'),
    path('missions/today/', views.daily_missions_view, name='daily_missions'),
    path('missions/schedule/', views.mission_schedule_view, name='mission_schedule'),
    path('missions/review/', views.mission_review_view, name='mission_review'),
    path('missions/review/approve-all/', views.approve_all_review_missions_view, name='approve_all_review_missions'),
    path('missions/review/reject-all/', views.reject_all_review_missions_view, name='reject_all_review_missions'),
    path('missions/generate-next-week/', views.generate_next_week_missions_view, name='generate_next_week_missions'),
    path('training/generate/', views.generate_training_mission_view, name='generate_training_mission'),
    path('training/chat-challenge/generate/', views.generate_training_chat_challenge_view, name='generate_training_chat_challenge'),
    path('training/chat-challenge/message/', views.training_chat_message_view, name='training_chat_message'),
    path('training/chat-challenge/submit/', views.submit_training_chat_challenge_view, name='submit_training_chat_challenge'),
    path('missions/<int:mission_id>/approve/', views.approve_mission_view, name='approve_mission'),
    path('missions/<int:mission_id>/regenerate/', views.regenerate_mission_view, name='regenerate_mission'),
    path('missions/<int:mission_id>/reject/', views.reject_mission_view, name='reject_mission'),
    path('missions/<int:mission_id>/', views.mission_detail_view, name='mission_detail'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('leaderboard/history/<str:week_start>/', views.leaderboard_history_view, name='leaderboard_history'),
]
