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
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
]
