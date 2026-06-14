from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Mission, MissionAttempt, Profile
from .services.ai_mission_generator import (
    AiMissionGenerationError,
    SYSTEM_PROMPT,
    build_user_prompt,
    generate_next_week,
    next_calendar_week,
)
from .services.mission_validation import MissionValidationError, validate_generated_payload


class AccountsApiTests(TestCase):
    def create_user(self, email, role=Profile.ROLE_ACCOUNTANT, legacy_score=0):
        user = get_user_model().objects.create_user(username=email, email=email, password='Test1234!')
        Profile.objects.create(
            user=user,
            role=role,
            onboarding_completed=True,
            mission_scores={'legacy': legacy_score} if legacy_score else {},
        )
        return user

    def create_mission(self, creator, scheduled_date=None, points=100):
        return Mission.objects.create(
            mission_type=Mission.TYPE_SINGLE_CHOICE,
            scheduled_date=scheduled_date or timezone.localdate(),
            title_de='Testmission',
            title_en='Test mission',
            description_de='Beschreibung',
            description_en='Description',
            content={
                'question': {'de': 'Richtig?', 'en': 'Correct?'},
                'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
                'correct_index': 0,
            },
            max_points=points,
            created_by=creator,
        )

    def test_first_registered_user_becomes_admin(self):
        response = self.client.post('/api/auth/register/', {
            'email': 'admin@example.com', 'password': 'Test1234!',
            'first_name': 'Ada', 'last_name': 'Admin', 'role': Profile.ROLE_ACCOUNTANT,
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], Profile.ROLE_ADMIN)

    def test_daily_missions_only_include_today_and_hide_correct_answer(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        self.create_mission(creator)
        self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/today/?lang=en', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['missions']), 1)
        self.assertEqual(response.json()['missions'][0]['content']['question'], 'Correct?')
        self.assertNotIn('correct_index', response.json()['missions'][0]['content'])

    def test_daily_missions_exclude_review_missions(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        published = self.create_mission(creator)
        review = self.create_mission(creator)
        review.status = Mission.STATUS_REVIEW
        review.save(update_fields=['status'])
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/today/', secure=True)
        self.assertEqual([item['id'] for item in response.json()['missions']], [published.id])

    def test_mission_can_only_be_completed_once_and_points_are_server_calculated(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com', legacy_score=40)
        mission = self.create_mission(creator, points=90)
        self.client.force_login(player)

        first = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': 0,
        }, content_type='application/json', secure=True)
        second = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': 0,
        }, content_type='application/json', secure=True)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['result']['score'], 90)
        self.assertEqual(first.json()['progress']['total_points'], 130)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(MissionAttempt.objects.filter(user=player, mission=mission).count(), 1)

    def test_multiple_choice_requires_the_exact_set_of_correct_answers(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        partial_player = self.create_user('partial@example.com')
        correct_player = self.create_user('correct@example.com')
        mission = self.create_mission(creator, points=50)
        mission.mission_type = Mission.TYPE_MULTIPLE_CHOICE
        mission.content = {
            'question': {'de': 'Welche passen?', 'en': 'Which apply?'},
            'options': [
                {'de': 'A', 'en': 'A'}, {'de': 'B', 'en': 'B'}, {'de': 'C', 'en': 'C'},
            ],
            'correct_indices': [0, 2],
        }
        mission.save(update_fields=['mission_type', 'content'])

        self.client.force_login(partial_player)
        partial = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': [0],
        }, content_type='application/json', secure=True)
        self.assertEqual(partial.json()['result']['score'], 0)

        self.client.force_login(correct_player)
        correct = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': [2, 0],
        }, content_type='application/json', secure=True)
        self.assertEqual(correct.json()['result']['score'], 50)
        self.assertEqual(
            MissionAttempt.objects.get(user=correct_player, mission=mission).answer['selected_indices'],
            [0, 2],
        )

    def test_only_creators_can_create_and_date_is_limited_to_two_missions(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        payload = {
            'type': 'single_choice', 'scheduled_date': timezone.localdate().isoformat(),
            'title_de': 'Titel', 'title_en': 'Title',
            'description_de': 'Beschreibung', 'description_en': 'Description',
            'question_de': 'Frage?', 'question_en': 'Question?',
            'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
            'correct_index': 0, 'max_points': 50,
        }

        self.client.force_login(player)
        denied = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(creator)
        self.assertEqual(self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True).status_code, 201)
        payload['title_de'] = 'Titel 2'
        self.assertEqual(self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True).status_code, 201)
        payload['title_de'] = 'Titel 3'
        self.assertEqual(self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True).status_code, 409)

    def test_creator_can_create_supported_types_and_edit_from_calendar(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        payload = {
            'type': Mission.TYPE_MULTIPLE_CHOICE,
            'scheduled_date': (timezone.localdate() + timedelta(days=3)).isoformat(),
            'title_de': 'Mehrfachauswahl', 'title_en': 'Multiple choice',
            'description_de': 'Kurze Beschreibung', 'description_en': 'Short description',
            'question_de': 'Welche Option passt?', 'question_en': 'Which option fits?',
            'feedback_de': 'Option zwei passt.', 'feedback_en': 'Option two fits.',
            'options': [{'de': 'Eins', 'en': 'One'}, {'de': 'Zwei', 'en': 'Two'}],
            'correct_index': 1, 'max_points': 30,
        }
        created = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)
        self.assertEqual(created.status_code, 201)
        mission = Mission.objects.get(title_en='Multiple choice')

        payload['type'] = Mission.TYPE_PROMPT_SELECTION
        payload['title_de'] = 'Prompt-Auswahl'
        payload['title_en'] = 'Prompt selection'
        updated = self.client.patch(
            f'/api/auth/missions/{mission.id}/', payload, content_type='application/json', secure=True,
        )
        self.assertEqual(updated.status_code, 200)
        mission.refresh_from_db()
        self.assertEqual(mission.mission_type, Mission.TYPE_PROMPT_SELECTION)
        self.assertEqual(mission.title_de, 'Prompt-Auswahl')
        self.assertEqual(mission.content['feedback']['en'], 'Option two fits.')

    def test_attempted_mission_cannot_be_edited(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        mission = self.create_mission(creator)
        MissionAttempt.objects.create(user=player, mission=mission, answer={'selected_index': 0}, score=100)
        self.client.force_login(creator)
        response = self.client.patch(
            f'/api/auth/missions/{mission.id}/', {}, content_type='application/json', secure=True,
        )
        self.assertEqual(response.status_code, 409)

    def test_schedule_includes_bilingual_details_and_owner_can_delete(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        mission = self.create_mission(creator)
        self.client.force_login(creator)
        today = timezone.localdate().isoformat()

        response = self.client.get(f'/api/auth/missions/schedule/?from={today}&to={today}', secure=True)
        details = response.json()['missions'][today][0]
        self.assertEqual(details['title_de'], 'Testmission')
        self.assertEqual(details['title_en'], 'Test mission')
        self.assertEqual(details['options'][0], {'de': 'Ja', 'en': 'Yes'})
        self.assertTrue(details['can_delete'])

        deleted = self.client.delete(f'/api/auth/missions/{mission.id}/', secure=True)
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Mission.objects.filter(id=mission.id).exists())

    def test_mission_with_attempts_cannot_be_deleted(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        mission = self.create_mission(creator)
        MissionAttempt.objects.create(user=player, mission=mission, answer={'selected_index': 0}, score=100)
        self.client.force_login(creator)

        response = self.client.delete(f'/api/auth/missions/{mission.id}/', secure=True)
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Mission.objects.filter(id=mission.id).exists())

    def test_review_endpoints_require_content_permission(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        mission = self.create_mission(creator)
        mission.status = Mission.STATUS_REVIEW
        mission.generated_by_ai = True
        mission.save(update_fields=['status', 'generated_by_ai'])

        self.client.force_login(player)
        self.assertEqual(self.client.get('/api/auth/missions/review/', secure=True).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/missions/review/approve-all/', secure=True).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/missions/review/reject-all/', secure=True).status_code, 403)
        self.assertEqual(self.client.post(f'/api/auth/missions/{mission.id}/approve/', secure=True).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/missions/generate-next-week/', secure=True).status_code, 403)

    def test_creator_can_review_approve_and_reject(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        approved = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        approved.status = Mission.STATUS_REVIEW
        approved.generated_by_ai = True
        approved.save(update_fields=['status', 'generated_by_ai'])
        rejected = self.create_mission(creator, timezone.localdate() + timedelta(days=2))
        rejected.status = Mission.STATUS_REVIEW
        rejected.generated_by_ai = True
        rejected.save(update_fields=['status', 'generated_by_ai'])
        self.client.force_login(creator)

        review = self.client.get('/api/auth/missions/review/', secure=True)
        self.assertEqual(len(review.json()['missions']), 2)
        self.assertEqual(self.client.post(f'/api/auth/missions/{approved.id}/approve/', secure=True).status_code, 200)
        self.assertEqual(self.client.post(f'/api/auth/missions/{rejected.id}/reject/', secure=True).status_code, 200)
        approved.refresh_from_db()
        rejected.refresh_from_db()
        self.assertEqual(approved.status, Mission.STATUS_PUBLISHED)
        self.assertEqual(approved.reviewed_by, creator)
        self.assertEqual(rejected.status, Mission.STATUS_REJECTED)

    def test_creator_can_approve_and_reject_all_review_missions(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        first = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        second = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        Mission.objects.filter(id__in=[first.id, second.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        approved = self.client.post('/api/auth/missions/review/approve-all/', secure=True)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()['approved_count'], 2)
        self.assertEqual(
            Mission.objects.filter(id__in=[first.id, second.id], status=Mission.STATUS_PUBLISHED).count(),
            2,
        )

        third = self.create_mission(creator, timezone.localdate() + timedelta(days=2))
        third.status = Mission.STATUS_REVIEW
        third.save(update_fields=['status'])
        rejected = self.client.post('/api/auth/missions/review/reject-all/', secure=True)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()['rejected_count'], 1)
        third.refresh_from_db()
        self.assertEqual(third.status, Mission.STATUS_REJECTED)

    def test_approve_all_is_atomic_when_a_day_would_exceed_two_missions(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        scheduled_date = timezone.localdate() + timedelta(days=1)
        published = self.create_mission(creator, scheduled_date)
        first_review = self.create_mission(creator, scheduled_date)
        second_review = self.create_mission(creator, scheduled_date)
        Mission.objects.filter(id__in=[first_review.id, second_review.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/review/approve-all/', secure=True)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Mission.objects.filter(status=Mission.STATUS_REVIEW).count(), 2)
        published.refresh_from_db()
        self.assertEqual(published.status, Mission.STATUS_PUBLISHED)

    @patch('accounts.views.generate_next_week')
    def test_creator_can_trigger_generation(self, generate_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        start, end = next_calendar_week()
        generate_mock.return_value = ([], start, end)
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created_count'], 0)
        generate_mock.assert_called_once_with(creator, force=False)

    def test_leaderboard_combines_legacy_and_daily_mission_points(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        leader = self.create_user('leader@example.com', legacy_score=40)
        mission = self.create_mission(creator, points=90)
        MissionAttempt.objects.create(user=leader, mission=mission, answer={'selected_index': 0}, score=90)
        self.client.force_login(leader)

        response = self.client.get('/api/auth/leaderboard/', secure=True)
        self.assertEqual(response.status_code, 200)
        entry = next(item for item in response.json()['entries'] if item['email'] == 'leader@example.com')
        self.assertEqual(entry['total_points'], 130)


class AiMissionServiceTests(TestCase):
    def create_creator(self):
        user = get_user_model().objects.create_user(
            username='creator@example.com', email='creator@example.com', password='Test1234!'
        )
        Profile.objects.create(user=user, role=Profile.ROLE_CONTENT_CREATOR)
        return user

    def valid_payload(self, target_slots):
        missions = []
        for scheduled_date, count in target_slots.items():
            for index in range(count):
                missions.append({
                    'date': scheduled_date.isoformat(),
                    'type': Mission.TYPE_PROMPT_SELECTION,
                    'title_de': f'Prompt {index}', 'title_en': f'Prompt {index}',
                    'description_de': 'Kurze Beschreibung', 'description_en': 'Short description',
                    'points': 30,
                    'content': {
                        'question_de': 'Welcher Prompt ist besser?', 'question_en': 'Which prompt is better?',
                        'options_de': ['Prompt A', 'Prompt B'], 'options_en': ['Prompt A', 'Prompt B'],
                        'correct_option_index': 1,
                        'feedback_de': 'Prompt B ist genauer.', 'feedback_en': 'Prompt B is more precise.',
                    },
                })
        return {'missions': missions}

    def test_validator_rejects_invalid_correct_index(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['content']['correct_option_index'] = 9
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_prompt_targets_accessible_everyday_finance_ai_learning(self):
        start, _ = next_calendar_week()
        prompt = build_user_prompt({start: 2})
        self.assertIn('little or no practical AI experience', SYSTEM_PROMPT)
        self.assertIn('beginner-friendly', SYSTEM_PROMPT)
        self.assertIn('monthly, quarterly, and year-end reports', SYSTEM_PROMPT)
        self.assertIn('Do not require knowledge of machine-learning algorithms', SYSTEM_PROMPT)
        self.assertIn('practical everyday AI usage', prompt)

    def test_validator_accepts_multiple_correct_answers_only_for_multiple_choice(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['type'] = Mission.TYPE_MULTIPLE_CHOICE
        payload['missions'][0]['content'].pop('correct_option_index')
        payload['missions'][0]['content']['correct_option_indices'] = [0, 1]
        normalized = validate_generated_payload(payload, {start: 1})
        self.assertEqual(normalized[0]['content']['correct_indices'], [0, 1])

        payload['missions'][0]['type'] = Mission.TYPE_PROMPT_SELECTION
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    @patch('accounts.services.ai_mission_generator.call_ai')
    def test_weekly_generation_creates_review_missions_without_overwriting_published(self, call_ai_mock):
        creator = self.create_creator()
        start, end = next_calendar_week()
        Mission.objects.create(
            mission_type=Mission.TYPE_SINGLE_CHOICE,
            scheduled_date=start,
            title_de='Veröffentlicht', title_en='Published',
            content={'question': {'de': 'Frage', 'en': 'Question'}, 'options': [], 'correct_index': 0},
            max_points=20, created_by=creator, status=Mission.STATUS_PUBLISHED,
        )
        expected_slots = {start: 1}
        expected_slots.update({start + timedelta(days=offset): 2 for offset in range(1, 7)})
        call_ai_mock.return_value = self.valid_payload(expected_slots)

        created, actual_start, actual_end = generate_next_week(creator)
        self.assertEqual((actual_start, actual_end), (start, end))
        self.assertEqual(len(created), 13)
        self.assertTrue(all(mission.status == Mission.STATUS_REVIEW for mission in created))
        self.assertTrue(all(mission.generated_by_ai for mission in created))
        self.assertEqual(Mission.objects.filter(status=Mission.STATUS_PUBLISHED).count(), 1)

    @patch('accounts.services.ai_mission_generator.call_ai')
    def test_invalid_ai_response_creates_no_missions(self, call_ai_mock):
        creator = self.create_creator()
        call_ai_mock.return_value = {'missions': []}
        with self.assertRaises(AiMissionGenerationError):
            generate_next_week(creator)
        self.assertEqual(Mission.objects.count(), 0)
