from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Profile


class AccountsApiTests(TestCase):
    def create_user(self, email, first_name, score=0):
        user = get_user_model().objects.create_user(
            username=email,
            email=email,
            password='Test1234!',
            first_name=first_name,
        )
        Profile.objects.create(
            user=user,
            mission_scores={'prompt-quality-quiz': score} if score else {},
        )
        return user

    def test_first_registered_user_becomes_admin(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'admin@example.com',
                'password': 'Test1234!',
                'first_name': 'Ada',
                'last_name': 'Admin',
                'role': Profile.ROLE_ACCOUNTANT,
            },
            content_type='application/json',
            secure=True,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], Profile.ROLE_ADMIN)

    def test_leaderboard_uses_database_scores(self):
        leader = self.create_user('leader@example.com', 'Leader', 90)
        self.create_user('starter@example.com', 'Starter', 20)
        self.client.force_login(leader)

        response = self.client.get('/api/auth/leaderboard/', secure=True)

        self.assertEqual(response.status_code, 200)
        entries = response.json()['entries']
        self.assertEqual(entries[0]['email'], 'leader@example.com')
        self.assertEqual(entries[0]['total_points'], 90)

    def test_mission_completion_keeps_best_score_and_caps_points(self):
        user = self.create_user('player@example.com', 'Player', 40)
        self.client.force_login(user)

        lower = self.client.post(
            '/api/auth/progress/complete/',
            {'mission_id': 'prompt-quality-quiz', 'score': 20},
            content_type='application/json',
            secure=True,
        )
        capped = self.client.post(
            '/api/auth/progress/complete/',
            {'mission_id': 'prompt-quality-quiz', 'score': 999},
            content_type='application/json',
            secure=True,
        )

        self.assertEqual(lower.json()['progress']['total_points'], 40)
        self.assertEqual(capped.json()['progress']['total_points'], 90)
