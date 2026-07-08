from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import AgentChat, DailyMissionReminder, Mission, MissionAttempt, Profile, WeeklyLeaderboardSnapshot
from .services.ai_mission_generator import (
    AiMissionGenerationError,
    SYSTEM_PROMPT,
    build_user_prompt,
    extract_json,
    generate_next_week,
    next_calendar_week,
    split_target_slots,
)
from .services.ai_chat_challenge import evaluate_final_answers, validate_challenge
from .services.email_notifications import send_daily_mission_reminders
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
                'feedback': {'de': 'Deutsches Feedback', 'en': 'English feedback'},
                'micro_learning': {
                    'de': 'Pruefe KI-Ergebnisse immer vor der Weiterverwendung.',
                    'en': 'Always verify AI output before reusing it.',
                },
            },
            max_points=points,
            created_by=creator,
        )

    def chat_challenge(self):
        return validate_challenge({
            'title_de': 'Abweichungsanalyse', 'title_en': 'Variance analysis',
            'description_de': 'Uebe mit einem KI-Chat.', 'description_en': 'Practice with an AI chat.',
            'task_de': 'Pruefe die Plan-Ist-Abweichung.', 'task_en': 'Check the plan-versus-actual variance.',
            'case_data_de': ['Plan: 100', 'Ist: 110'], 'case_data_en': ['Plan: 100', 'Actual: 110'],
            'chat_system_prompt_de': 'Hilf beim Rechnen.', 'chat_system_prompt_en': 'Help with the calculation.',
            'final_questions': [
                {
                    'id': 'q1', 'type': 'number', 'prompt_de': 'Abweichung?', 'prompt_en': 'Variance?',
                    'solution': 10, 'tolerance': 0.1, 'feedback_de': 'Die Abweichung betraegt 10 Prozent.',
                    'feedback_en': 'The variance is 10 percent.',
                },
                {
                    'id': 'q2', 'type': 'evidence_boolean', 'prompt_de': 'Belegt?', 'prompt_en': 'Supported?',
                    'options_de': ['Ja', 'Nein'], 'options_en': ['Yes', 'No'], 'solution': True,
                    'feedback_de': 'Die Falldaten belegen die Aussage.',
                    'feedback_en': 'The case data supports the statement.',
                },
            ],
        })

    def test_first_registered_user_becomes_admin(self):
        response = self.client.post('/api/auth/register/', {
            'email': 'admin@example.com', 'password': 'Test1234!',
            'first_name': 'Ada', 'last_name': 'Admin', 'role': Profile.ROLE_ACCOUNTANT,
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], Profile.ROLE_ADMIN)

    def completed_at_on(self, day):
        return timezone.make_aware(datetime.combine(day, time(hour=12)))

    def local_datetime(self, day, hour=10, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour=hour, minute=minute)))

    def next_business_day(self, start=None):
        day = (start or timezone.localdate()) + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        return day

    def test_daily_missions_only_include_today_and_hide_correct_answer(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        today = timezone.localdate()
        today_mission = self.create_mission(creator, today)
        self.create_mission(creator, today - timedelta(days=6))
        self.create_mission(creator, today - timedelta(days=7))
        self.create_mission(creator, today + timedelta(days=1))
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/today/?lang=en', secure=True)
        self.assertEqual(response.status_code, 200)
        missions = response.json()['missions']
        self.assertEqual([mission['id'] for mission in missions], [today_mission.id])
        self.assertEqual(missions[0]['content']['question'], 'Correct?')
        self.assertNotIn('correct_index', missions[0]['content'])
        self.assertNotIn('micro_learning', missions[0]['content'])

    @patch('accounts.views.timezone.now')
    def test_available_missions_include_open_week_missions_but_not_today_completed_or_expired(self, now_mock):
        creator = self.create_user('creator-available@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-available@example.com')
        today = date(2026, 7, 8)  # Wednesday
        now_mock.return_value = self.local_datetime(today, 10)
        self.create_mission(creator, today)
        yesterday = self.create_mission(creator, today - timedelta(days=1))
        monday = self.create_mission(creator, today - timedelta(days=2))
        completed_available = self.create_mission(creator, today - timedelta(days=2))
        self.create_mission(creator, date(2026, 7, 5))
        self.create_mission(creator, today + timedelta(days=1))
        MissionAttempt.objects.create(
            user=player, mission=completed_available, answer={'selected_indices': [0]}, score=100,
        )
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/available/?lang=en', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([mission['id'] for mission in response.json()['missions']], [yesterday.id, monday.id])

    @patch('accounts.views.timezone.now')
    def test_previous_week_missions_remain_available_until_next_monday_noon(self, now_mock):
        creator = self.create_user('creator-monday@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-monday@example.com')
        now_mock.return_value = self.local_datetime(date(2026, 7, 13), 11, 59)
        friday = self.create_mission(creator, date(2026, 7, 10))
        self.create_mission(creator, date(2026, 7, 12))
        self.create_mission(creator, date(2026, 7, 13))
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/available/?lang=en', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([mission['id'] for mission in response.json()['missions']], [friday.id])

    @patch('accounts.views.timezone.now')
    def test_all_missions_from_one_week_expire_at_next_monday_noon(self, now_mock):
        creator = self.create_user('creator-week-deadline@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-week-deadline@example.com')
        now_mock.return_value = self.local_datetime(date(2026, 7, 13), 11, 59)
        monday = self.create_mission(creator, date(2026, 7, 6))
        thursday = self.create_mission(creator, date(2026, 7, 9))
        friday = self.create_mission(creator, date(2026, 7, 10))
        self.client.force_login(player)

        before_deadline = self.client.get('/api/auth/missions/available/?lang=en', secure=True)
        self.assertEqual(
            [mission['id'] for mission in before_deadline.json()['missions']],
            [friday.id, thursday.id, monday.id],
        )

        now_mock.return_value = self.local_datetime(date(2026, 7, 13), 12, 0)
        after_deadline = self.client.get('/api/auth/missions/available/?lang=en', secure=True)
        self.assertEqual(after_deadline.json()['missions'], [])

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

    @patch('accounts.views.timezone.now')
    def test_daily_missions_hide_weekend_missions(self, now_mock):
        creator = self.create_user('creator-weekend@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-weekend@example.com')
        saturday = date(2026, 7, 11)
        now_mock.return_value = self.local_datetime(saturday, 10)
        self.create_mission(creator, saturday)
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/today/?lang=en', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['missions'], [])

    def test_archive_includes_completed_missions_even_inside_availability_window(self):
        creator = self.create_user('creator-archive@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-archive@example.com')
        today = timezone.localdate()
        available_old = self.create_mission(creator, today - timedelta(days=6))
        expired = self.create_mission(creator, today - timedelta(days=7))
        MissionAttempt.objects.create(user=player, mission=available_old, answer={'selected_indices': [0]}, score=100)
        MissionAttempt.objects.create(user=player, mission=expired, answer={'selected_indices': [0]}, score=100)
        self.client.force_login(player)

        response = self.client.get('/api/auth/missions/archive/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([mission['id'] for mission in response.json()['missions']], [expired.id, available_old.id])

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
        self.assertEqual(first.json()['result']['correct_indices'], [0])
        self.assertEqual(first.json()['progress']['total_points'], 130)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(MissionAttempt.objects.filter(user=player, mission=mission).count(), 1)

    @patch('accounts.views.timezone.now')
    def test_previous_week_mission_can_be_completed_before_monday_noon_but_not_after(self, now_mock):
        creator = self.create_user('creator-availability@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-availability@example.com')
        now_mock.return_value = self.local_datetime(date(2026, 7, 13), 11, 59)
        friday = self.create_mission(creator, date(2026, 7, 10), points=70)
        expired = self.create_mission(creator, date(2026, 7, 5), points=80)
        deadline_mission = self.create_mission(creator, date(2026, 7, 11), points=60)
        self.client.force_login(player)

        available_response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': friday.id, 'answer': 0,
        }, content_type='application/json', secure=True)
        expired_response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': expired.id, 'answer': 0,
        }, content_type='application/json', secure=True)
        now_mock.return_value = self.local_datetime(date(2026, 7, 13), 12, 0)
        deadline_response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': deadline_mission.id, 'answer': 0,
        }, content_type='application/json', secure=True)

        self.assertEqual(available_response.status_code, 200)
        self.assertEqual(available_response.json()['result']['score'], 70)
        self.assertEqual(expired_response.status_code, 404)
        self.assertEqual(deadline_response.status_code, 404)
        self.assertFalse(MissionAttempt.objects.filter(user=player, mission=expired).exists())
        self.assertFalse(MissionAttempt.objects.filter(user=player, mission=deadline_mission).exists())

    def test_completed_mission_response_uses_requested_language(self):
        creator = self.create_user('creator-language@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-language@example.com')
        mission = self.create_mission(creator)
        self.client.force_login(player)

        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': 0, 'language': 'en',
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mission']['title'], 'Test mission')
        self.assertEqual(response.json()['mission']['content']['question'], 'Correct?')
        self.assertEqual(response.json()['mission']['content']['feedback'], 'English feedback')
        self.assertEqual(
            response.json()['mission']['content']['micro_learning'],
            'Always verify AI output before reusing it.',
        )

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

    def test_prompt_ranking_requires_the_exact_order(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('ranking@example.com')
        mission = self.create_mission(creator, points=60)
        mission.mission_type = Mission.TYPE_PROMPT_RANKING
        mission.content = {
            'question': {'de': 'Sortiere.', 'en': 'Rank them.'},
            'options': [{'de': 'A', 'en': 'A'}, {'de': 'B', 'en': 'B'}, {'de': 'C', 'en': 'C'}],
            'correct_order': [1, 0, 2],
            'feedback': {'de': 'Mehr Kontext ist besser.', 'en': 'More context is better.'},
        }
        mission.save(update_fields=['mission_type', 'content'])
        self.client.force_login(player)

        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': [1, 0, 2],
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result']['score'], 60)
        self.assertEqual(MissionAttempt.objects.get(user=player, mission=mission).answer['selected_order'], [1, 0, 2])

    def test_compliance_traffic_light_awards_partial_points(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('traffic@example.com')
        mission = self.create_mission(creator, points=90)
        mission.mission_type = Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT
        mission.content = {
            'question': {'de': 'Bewerte.', 'en': 'Assess.'},
            'statements': [
                {'text': {'de': 'A', 'en': 'A'}, 'correct_color': 'green', 'feedback': {'de': 'A', 'en': 'A'}},
                {'text': {'de': 'B', 'en': 'B'}, 'correct_color': 'yellow', 'feedback': {'de': 'B', 'en': 'B'}},
                {'text': {'de': 'C', 'en': 'C'}, 'correct_color': 'red', 'feedback': {'de': 'C', 'en': 'C'}},
            ],
        }
        mission.save(update_fields=['mission_type', 'content'])
        self.client.force_login(player)

        available = self.client.get('/api/auth/missions/today/?lang=en', secure=True).json()['missions'][0]
        self.assertNotIn('correct_color', str(available['content']))
        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': ['green', 'red', 'red'],
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result']['score'], 60)
        self.assertEqual(response.json()['result']['correct_count'], 2)
        self.assertEqual(response.json()['result']['item_correct'], [True, False, True])
        self.assertFalse(response.json()['result']['correct'])

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

    @patch('accounts.views.send_published_mission_email')
    def test_published_mission_creation_sends_email_reminder(self, send_email_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.create_user('player@example.com')
        payload = {
            'type': 'single_choice', 'scheduled_date': timezone.localdate().isoformat(),
            'title_de': 'Titel', 'title_en': 'Title',
            'description_de': 'Beschreibung', 'description_en': 'Description',
            'question_de': 'Frage?', 'question_en': 'Question?',
            'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
            'correct_index': 0, 'max_points': 50,
        }
        self.client.force_login(creator)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 201)
        send_email_mock.assert_called_once()
        self.assertEqual(send_email_mock.call_args.args[0].title_de, 'Titel')

    @patch('accounts.services.email_notifications.send_daily_mission_reminder', return_value=1)
    def test_daily_mission_reminders_target_only_incomplete_users_once_on_friday(self, send_mock):
        creator = self.create_user('creator-reminder@example.com', Profile.ROLE_CONTENT_CREATOR)
        done_user = self.create_user('done@example.com')
        partial_user = self.create_user('partial@example.com')
        missing_user = self.create_user('missing@example.com')
        friday = date(2026, 6, 19)
        monday = friday - timedelta(days=4)
        first = self.create_mission(creator, monday)
        second = self.create_mission(creator, friday)
        MissionAttempt.objects.create(user=done_user, mission=first, score=10)
        MissionAttempt.objects.create(user=done_user, mission=second, score=10)
        MissionAttempt.objects.create(user=partial_user, mission=first, score=10)

        first_result = send_daily_mission_reminders(friday)
        second_result = send_daily_mission_reminders(friday)

        self.assertEqual(first_result['sent'], 3)
        self.assertEqual(first_result['incomplete_count'], 3)
        self.assertEqual(first_result['status'], 'sent')
        self.assertEqual(second_result['sent'], 0)
        self.assertEqual(second_result['skipped'], 3)
        self.assertEqual(send_mock.call_count, 3)
        partial_call = next(call for call in send_mock.call_args_list if call.args[0] == partial_user)
        self.assertEqual(partial_call.args[3], [second])
        self.assertEqual(
            set(DailyMissionReminder.objects.values_list('user__email', flat=True)),
            {'creator-reminder@example.com', 'partial@example.com', 'missing@example.com'},
        )

    @patch('accounts.services.email_notifications.send_daily_mission_reminder', return_value=1)
    def test_daily_mission_reminders_skip_non_fridays(self, send_mock):
        creator = self.create_user('creator-non-friday@example.com', Profile.ROLE_CONTENT_CREATOR)
        thursday = date(2026, 6, 18)
        self.create_mission(creator, thursday)

        result = send_daily_mission_reminders(thursday)

        self.assertEqual(result['status'], 'skipped_non_friday')
        self.assertEqual(result['sent'], 0)
        send_mock.assert_not_called()
        self.assertFalse(DailyMissionReminder.objects.exists())

    def test_creator_can_create_supported_types_and_edit_from_calendar(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        payload = {
            'type': Mission.TYPE_MULTIPLE_CHOICE,
            'scheduled_date': self.next_business_day().isoformat(),
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

    def test_creator_cannot_schedule_missions_on_weekends(self):
        creator = self.create_user('creator-weekend-schedule@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        payload = {
            'type': Mission.TYPE_SINGLE_CHOICE,
            'scheduled_date': '2026-07-11',
            'title_de': 'Wochenende', 'title_en': 'Weekend',
            'description_de': 'Kurze Beschreibung', 'description_en': 'Short description',
            'question_de': 'Welche Option passt?', 'question_en': 'Which option fits?',
            'feedback_de': 'Feedback', 'feedback_en': 'Feedback',
            'options': [{'de': 'Eins', 'en': 'One'}, {'de': 'Zwei', 'en': 'Two'}],
            'correct_index': 1, 'max_points': 30,
        }

        response = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'scheduled date must be a weekday')

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

    @patch('accounts.views.generate_training_candidate')
    def test_authenticated_user_can_generate_training_without_saving_mission(self, generate_mock):
        player = self.create_user('training@example.com')
        generate_mock.return_value = {
            'mission_type': Mission.TYPE_SINGLE_CHOICE,
            'title_de': 'Training', 'title_en': 'Training',
            'description_de': 'Beschreibung', 'description_en': 'Description',
            'max_points': 30,
            'content': {
                'question': {'de': 'Frage?', 'en': 'Question?'},
                'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
                'correct_indices': [0],
                'feedback': {'de': 'Gut.', 'en': 'Good.'},
            },
        }
        self.client.force_login(player)

        response = self.client.post('/api/auth/training/generate/', {
            'type': Mission.TYPE_SINGLE_CHOICE,
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mission']['question_en'], 'Question?')
        self.assertEqual(response.json()['mission']['test_solution']['correct_indices'], [0])
        self.assertEqual(Mission.objects.count(), 0)
        generate_mock.assert_called_once_with(Mission.TYPE_SINGLE_CHOICE)

    def test_training_generation_requires_authentication(self):
        response = self.client.post('/api/auth/training/generate/', {
            'type': Mission.TYPE_SINGLE_CHOICE,
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 401)

    def test_completed_choice_without_feedback_gets_solution_explanation(self):
        creator = self.create_user('fallback-creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('fallback-player@example.com')
        mission = self.create_mission(creator)
        mission.content.pop('feedback')
        mission.save(update_fields=['content'])
        self.client.force_login(player)

        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': 1, 'language': 'en',
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mission']['content']['feedback'], 'Correct answer: Yes.')

    @patch('accounts.views.generate_chat_challenge')
    def test_chat_challenge_hides_solutions_and_is_not_saved_as_mission(self, generate_mock):
        player = self.create_user('chat-player@example.com')
        generate_mock.return_value = self.chat_challenge()
        self.client.force_login(player)

        response = self.client.post('/api/auth/training/chat-challenge/generate/', {},
                                    content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        question = response.json()['mission']['final_questions'][0]
        self.assertNotIn('solution', question)
        self.assertNotIn('tolerance', question)
        self.assertNotIn('feedback_en', question)
        self.assertEqual(response.json()['mission']['final_questions'][1]['option_values'], [True, False])
        self.assertEqual(Mission.objects.count(), 0)

    @patch('accounts.views.chat_reply', return_value='Pruefe zuerst die Differenz zwischen Ist und Plan.')
    @patch('accounts.views.generate_chat_challenge')
    def test_chat_challenge_allows_only_three_messages(self, generate_mock, chat_reply_mock):
        player = self.create_user('chat-limit@example.com')
        generate_mock.return_value = self.chat_challenge()
        self.client.force_login(player)
        generated = self.client.post('/api/auth/training/chat-challenge/generate/', {},
                                     content_type='application/json', secure=True).json()['mission']

        for expected_remaining in (2, 1, 0):
            response = self.client.post('/api/auth/training/chat-challenge/message/', {
                'challenge_id': generated['id'], 'message': 'Gib mir einen Hinweis.', 'language': 'de',
            }, content_type='application/json', secure=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['remaining_prompts'], expected_remaining)
        blocked = self.client.post('/api/auth/training/chat-challenge/message/', {
            'challenge_id': generated['id'], 'message': 'Noch ein Hinweis.', 'language': 'de',
        }, content_type='application/json', secure=True)
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(chat_reply_mock.call_count, 3)

    def test_chat_challenge_final_answers_return_feedback_for_each_answer(self):
        result = evaluate_final_answers(self.chat_challenge(), {'q1': 10.05, 'q2': False}, 'de')

        self.assertFalse(result['correct'])
        self.assertTrue(result['items'][0]['correct'])
        self.assertFalse(result['items'][1]['correct'])
        self.assertIn('10 Prozent', result['items'][0]['feedback'])
        self.assertIn('Falldaten', result['items'][1]['feedback'])

    @patch('accounts.views.personal_agent_reply', return_value='Ich helfe dir beim Strukturieren.')
    def test_personal_agent_chat_requires_auth_and_returns_reply(self, reply_mock):
        unauthenticated = self.client.post('/api/auth/agent/chat/', {
            'messages': [{'role': 'user', 'content': 'Hilf mir'}], 'language': 'de',
        }, content_type='application/json', secure=True)
        player = self.create_user('agent-player@example.com')
        self.client.force_login(player)
        authenticated = self.client.post('/api/auth/agent/chat/', {
            'messages': [{'role': 'user', 'content': 'Hilf mir'}], 'language': 'de',
        }, content_type='application/json', secure=True)

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.json()['reply'], 'Ich helfe dir beim Strukturieren.')
        reply_mock.assert_called_once()

    @patch('accounts.views.personal_agent_reply', return_value='Gespeicherte Antwort.')
    def test_personal_agent_chats_are_saved_per_user(self, reply_mock):
        player = self.create_user('agent-history@example.com')
        other = self.create_user('agent-other@example.com')
        self.client.force_login(player)

        created = self.client.post('/api/auth/agent/chats/', {}, content_type='application/json', secure=True)
        chat_id = created.json()['chat']['id']
        message = self.client.post(f'/api/auth/agent/chats/{chat_id}/message/', {
            'message': 'Hilf mir mit einem Prompt.', 'language': 'de',
        }, content_type='application/json', secure=True)
        listing = self.client.get('/api/auth/agent/chats/', secure=True)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(message.status_code, 200)
        self.assertEqual(len(message.json()['chat']['messages']), 2)
        self.assertEqual(listing.json()['chats'][0]['id'], chat_id)
        self.assertEqual(AgentChat.objects.get(id=chat_id).user, player)

        self.client.force_login(other)
        blocked = self.client.get(f'/api/auth/agent/chats/{chat_id}/', secure=True)
        self.assertEqual(blocked.status_code, 404)
        reply_mock.assert_called_once()

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

    @patch('accounts.views.send_published_mission_email')
    def test_approving_review_mission_sends_email_reminder(self, send_email_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        mission = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        mission.status = Mission.STATUS_REVIEW
        mission.save(update_fields=['status'])
        self.client.force_login(creator)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'/api/auth/missions/{mission.id}/approve/', secure=True)

        self.assertEqual(response.status_code, 200)
        send_email_mock.assert_called_once()
        self.assertEqual(send_email_mock.call_args.args[0].id, mission.id)

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

    @patch('accounts.views.send_published_mission_emails')
    def test_approve_all_review_missions_sends_email_reminders(self, send_emails_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        first = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        second = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        Mission.objects.filter(id__in=[first.id, second.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/auth/missions/review/approve-all/', secure=True)

        self.assertEqual(response.status_code, 200)
        send_emails_mock.assert_called_once()
        self.assertEqual({mission.id for mission in send_emails_mock.call_args.args[0]}, {first.id, second.id})

    def test_review_list_and_bulk_action_are_limited_to_selected_week(self):
        creator = self.create_user('creator-filter@example.com', Profile.ROLE_CONTENT_CREATOR)
        week_start, _ = next_calendar_week()
        selected = self.create_mission(creator, week_start)
        other = self.create_mission(creator, week_start + timedelta(days=7))
        Mission.objects.filter(id__in=[selected.id, other.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        review = self.client.get(
            f'/api/auth/missions/review/?week_start={week_start.isoformat()}', secure=True,
        )
        approved = self.client.post('/api/auth/missions/review/approve-all/', {
            'week_start': week_start.isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual([mission['id'] for mission in review.json()['missions']], [selected.id])
        self.assertEqual(approved.json()['approved_count'], 1)
        selected.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(selected.status, Mission.STATUS_PUBLISHED)
        self.assertEqual(other.status, Mission.STATUS_REVIEW)

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
        generate_mock.assert_called_once_with(creator, force=False, week_start=None)

    @patch('accounts.views.generate_next_week')
    def test_creator_can_select_a_monday_for_generation(self, generate_mock):
        creator = self.create_user('creator-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        start, end = next_calendar_week()
        generate_mock.return_value = ([], start, end)
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': start.isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        generate_mock.assert_called_once_with(creator, force=False, week_start=start)

    def test_generation_week_must_be_a_future_monday(self):
        creator = self.create_user('creator-invalid-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        start, _ = next_calendar_week()
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': (start + timedelta(days=1)).isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 400)

    @patch('accounts.views.generate_next_week')
    def test_creator_can_select_the_current_week_monday(self, generate_mock):
        creator = self.create_user('creator-current-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        generate_mock.return_value = ([], current_monday, current_monday + timedelta(days=6))
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': current_monday.isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        generate_mock.assert_called_once_with(creator, force=False, week_start=current_monday)

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

    def test_streak_tracks_only_missions_completed_on_scheduled_date(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        today = timezone.localdate()

        def create_day(day, completed):
            missions = [self.create_mission(creator, day), self.create_mission(creator, day)]
            if completed:
                for mission in missions:
                    attempt = MissionAttempt.objects.create(
                        user=player, mission=mission, answer={'selected_indices': [0]}, score=mission.max_points,
                    )
                    MissionAttempt.objects.filter(id=attempt.id).update(completed_at=self.completed_at_on(day))
            return missions

        create_day(today - timedelta(days=4), True)
        create_day(today - timedelta(days=3), True)
        create_day(today - timedelta(days=2), False)
        create_day(today - timedelta(days=1), True)
        today_missions = create_day(today, False)
        self.client.force_login(player)

        progress = self.client.get('/api/auth/progress/', secure=True).json()['progress']
        self.assertEqual(progress['current_streak'], 1)
        self.assertEqual(progress['max_streak'], 2)

        for mission in today_missions:
            MissionAttempt.objects.create(
                user=player, mission=mission, answer={'selected_indices': [0]}, score=mission.max_points,
            )
        progress = self.client.get('/api/auth/progress/', secure=True).json()['progress']
        self.assertEqual(progress['current_streak'], 2)
        self.assertEqual(progress['max_streak'], 2)

        leaderboard = self.client.get('/api/auth/leaderboard/', secure=True).json()['entries']
        entry = next(item for item in leaderboard if item['email'] == 'player@example.com')
        self.assertEqual(entry['current_streak'], 2)
        self.assertEqual(entry['max_streak'], 2)

    def test_catch_up_missions_do_not_create_streak(self):
        creator = self.create_user('creator-catchup@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player-catchup@example.com')
        today = timezone.localdate()
        old_missions = [
            self.create_mission(creator, today - timedelta(days=1)),
            self.create_mission(creator, today - timedelta(days=1)),
        ]
        for mission in old_missions:
            MissionAttempt.objects.create(
                user=player, mission=mission, answer={'selected_indices': [0]}, score=mission.max_points,
            )
        self.client.force_login(player)

        progress = self.client.get('/api/auth/progress/', secure=True).json()['progress']
        self.assertEqual(progress['current_streak'], 0)
        self.assertEqual(progress['max_streak'], 0)

    def test_weekly_leaderboard_only_counts_attempts_from_current_week(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        current = self.create_mission(creator, today, points=40)
        previous = self.create_mission(creator, week_start - timedelta(days=1), points=90)
        current_attempt = MissionAttempt.objects.create(
            user=player, mission=current, answer={'selected_indices': [0]}, score=40,
        )
        previous_attempt = MissionAttempt.objects.create(
            user=player, mission=previous, answer={'selected_indices': [0]}, score=90,
        )
        MissionAttempt.objects.filter(id=current_attempt.id).update(completed_at=timezone.now())
        MissionAttempt.objects.filter(id=previous_attempt.id).update(
            completed_at=timezone.now() - timedelta(days=today.weekday() + 1),
        )
        self.client.force_login(player)

        data = self.client.get('/api/auth/leaderboard/', secure=True).json()
        weekly = next(item for item in data['weekly_entries'] if item['email'] == 'player@example.com')
        total = next(item for item in data['entries'] if item['email'] == 'player@example.com')
        self.assertEqual(weekly['total_points'], 40)
        self.assertEqual(weekly['completed_missions'], 1)
        self.assertEqual(total['total_points'], 130)

    def test_historical_weekly_leaderboard_can_be_retrieved(self):
        user = self.create_user('player@example.com')
        today = timezone.localdate()
        current_week_start = today - timedelta(days=today.weekday())
        week_start = current_week_start - timedelta(days=7)
        entries = [{
            'rank': 1, 'user_id': user.id, 'name': 'Player', 'email': user.email,
            'first_name': '', 'last_name': '', 'total_points': 80,
            'completed_missions': 4, 'level': 'Starter',
        }]
        WeeklyLeaderboardSnapshot.objects.create(
            week_start=week_start, week_end=week_start + timedelta(days=6), entries=entries,
        )
        self.client.force_login(user)

        response = self.client.get(f'/api/auth/leaderboard/history/{week_start.isoformat()}/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['entries'][0]['total_points'], 80)


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
                        'micro_learning_de': (
                            'Ein guter Prompt gibt der AI genug Orientierung, damit sie nicht raten muss. '
                            'Gerade in Finance-Aufgaben helfen Ziel, Kontext und gewünschtes Format dabei, '
                            'Ergebnisse später zu prüfen und mit Kolleginnen und Kollegen zu teilen.'
                        ),
                        'micro_learning_en': (
                            'A good prompt gives the AI enough orientation so it does not have to guess. '
                            'Especially in finance tasks, the goal, context, and desired format make results '
                            'easier to check and share with colleagues.'
                        ),
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
        self.assertIn('micro_learning_de', prompt)
        self.assertIn('micro-learning explanation', SYSTEM_PROMPT)

    def test_validator_rejects_missing_micro_learning(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['content'].pop('micro_learning_de')
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_validator_rejects_too_short_micro_learning(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['content']['micro_learning_de'] = 'Zu kurz.'
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_validator_rejects_feedback_repeated_as_micro_learning(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        content = payload['missions'][0]['content']
        content['feedback_de'] = content['micro_learning_de']
        content['feedback_en'] = content['micro_learning_en']
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_generation_batches_are_limited_to_one_day(self):
        start, _ = next_calendar_week()
        slots = {start + timedelta(days=offset): 2 for offset in range(7)}
        batches = split_target_slots(slots)
        self.assertEqual(len(batches), 7)
        self.assertTrue(all(sum(batch.values()) <= 2 for batch in batches))

    def test_json_extractor_accepts_fences_and_trailing_text(self):
        self.assertEqual(extract_json('```json\n{"missions": []}\n```'), {'missions': []})
        self.assertEqual(extract_json('Result: {"missions": []}\nDone'), {'missions': []})

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

    def test_validator_accepts_ai_single_choice(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['type'] = Mission.TYPE_SINGLE_CHOICE
        normalized = validate_generated_payload(payload, {start: 1})
        self.assertEqual(normalized[0]['mission_type'], Mission.TYPE_SINGLE_CHOICE)

    def test_validator_accepts_prompt_ranking_and_traffic_light(self):
        start, _ = next_calendar_week()
        ranking = self.valid_payload({start: 1})
        ranking['missions'][0]['type'] = Mission.TYPE_PROMPT_RANKING
        ranking['missions'][0]['content'].update({
            'options_de': ['Schlecht', 'Mittel', 'Gut'],
            'options_en': ['Bad', 'Average', 'Good'],
            'correct_order': [0, 1, 2],
        })
        ranking['missions'][0]['content'].pop('correct_option_index')
        normalized = validate_generated_payload(ranking, {start: 1})
        self.assertEqual(normalized[0]['content']['correct_order'], [0, 1, 2])

        traffic = self.valid_payload({start: 1})
        traffic['missions'][0]['type'] = Mission.TYPE_COMPLIANCE_TRAFFIC_LIGHT
        traffic['missions'][0]['content'] = {
            'question_de': 'Bewerte die Szenarien.', 'question_en': 'Assess the scenarios.',
            'statements_de': ['A', 'B', 'C'], 'statements_en': ['A', 'B', 'C'],
            'correct_colors': ['green', 'yellow', 'red'],
            'statement_feedback_de': ['Gut', 'Prüfen', 'Verboten'],
            'statement_feedback_en': ['Fine', 'Check', 'Forbidden'],
            'micro_learning_de': (
                'Die Ampel ist eine einfache Denkstütze für AI-Nutzung im Arbeitsalltag. '
                'Grün bedeutet meist unkritisch, gelb braucht zusätzliche Schutzmaßnahmen, '
                'und rot sollte nicht in ein AI-Tool eingegeben werden.'
            ),
            'micro_learning_en': (
                'The traffic light is a simple thinking aid for AI use at work. Green usually means low risk, '
                'yellow requires additional safeguards, and red should not be entered into an AI tool.'
            ),
        }
        normalized = validate_generated_payload(traffic, {start: 1})
        self.assertEqual(normalized[0]['content']['statements'][1]['correct_color'], 'yellow')

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
        call_ai_mock.side_effect = self.valid_payload

        created, actual_start, actual_end = generate_next_week(creator)
        self.assertEqual((actual_start, actual_end), (start, end))
        self.assertEqual(len(created), 9)
        self.assertTrue(all(mission.status == Mission.STATUS_REVIEW for mission in created))
        self.assertTrue(all(mission.generated_by_ai for mission in created))
        self.assertTrue(all(mission.scheduled_date.weekday() < 5 for mission in created))
        self.assertEqual(Mission.objects.filter(status=Mission.STATUS_PUBLISHED).count(), 1)
        self.assertEqual(call_ai_mock.call_count, 5)

    @patch('accounts.services.ai_mission_generator.call_ai')
    def test_invalid_ai_response_creates_no_missions(self, call_ai_mock):
        creator = self.create_creator()
        call_ai_mock.return_value = {'missions': []}
        with self.assertRaises(AiMissionGenerationError):
            generate_next_week(creator)
        self.assertEqual(Mission.objects.count(), 0)
