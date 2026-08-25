from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (
    AgentChat,
    DailyMissionReminder,
    GenerationRun,
    Mission,
    MissionAssignment,
    MissionAttempt,
    Profile,
    SkillProgressionSettings,
    WeeklyLeaderboardSnapshot,
)
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
from .services.email_notifications import send_daily_mission_reminder, send_daily_mission_reminders
from .services.mission_validation import MissionValidationError, validate_generated_payload
from .services.skill_progression import evaluate_skill_progression, set_skill_level_manually


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

    def test_self_registration_cannot_request_privileged_role(self):
        self.create_user('existing-admin@example.com', Profile.ROLE_ADMIN)
        response = self.client.post('/api/auth/register/', {
            'email': 'attacker@example.com', 'password': 'Test1234!',
            'first_name': 'Eve', 'last_name': 'Example', 'role': Profile.ROLE_ADMIN,
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(email='attacker@example.com').exists())

    def completed_at_on(self, day):
        return timezone.make_aware(datetime.combine(day, time(hour=12)))

    def local_datetime(self, day, hour=10, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour=hour, minute=minute)))

    def next_business_day(self, start=None):
        day = (start or timezone.localdate()) + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        return day

    def manual_mission_payload(self, scheduled_date=None, mission_type=Mission.TYPE_SINGLE_CHOICE):
        variants = {}
        for position, difficulty in enumerate(Mission.DIFFICULTIES):
            variants[difficulty] = {
                'title_de': f'Titel {difficulty}',
                'title_en': f'Title {difficulty}',
                'description_de': f'Beschreibung {difficulty}',
                'description_en': f'Description {difficulty}',
                'question_de': f'Frage {difficulty}?',
                'question_en': f'Question {difficulty}?',
                'feedback_de': f'Feedback {difficulty}',
                'feedback_en': f'Feedback {difficulty}',
                'micro_learning_de': f'Lernhinweis {difficulty}',
                'micro_learning_en': f'Learning note {difficulty}',
                'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
                'correct_indices': [0],
                'max_points': 30 + position * 10,
            }
        return {
            'type': mission_type,
            'scheduled_date': (scheduled_date or timezone.localdate()).isoformat(),
            'topic_de': 'Gemeinsames Thema',
            'topic_en': 'Shared topic',
            'learning_objective_de': 'Gemeinsames Lernziel',
            'learning_objective_en': 'Shared learning objective',
            'variants': variants,
        }

    def manual_task_mission_payload(self, scheduled_date, mission_type=Mission.TYPE_BULK_CATEGORIZATION):
        variants = {}
        for position, difficulty in enumerate(Mission.DIFFICULTIES):
            variants[difficulty] = {
                'title_de': f'Praxisaufgabe {difficulty}',
                'title_en': f'Hands-on task {difficulty}',
                'description_de': f'Bearbeite einen Finance-Fall auf Stufe {difficulty}.',
                'description_en': f'Complete a finance case at {difficulty} level.',
                'question_de': f'Werte die Falldaten für {difficulty} aus.',
                'question_en': f'Evaluate the {difficulty} case data.',
                'case_format': 'prose' if mission_type == Mission.TYPE_INVOICE_EXTRACTION else 'table',
                'case_data_de': ['2026-08-01 | Beispiel GmbH | 125,00 EUR'],
                'case_data_en': ['2026-08-01 | Example Ltd | EUR 125.00'],
                'result_fields': [
                    {
                        'id': 'total_amount', 'type': 'number',
                        'label_de': 'Gesamtbetrag', 'label_en': 'Total amount',
                        'unit': 'EUR', 'solution': 125, 'tolerance': 0.01,
                        'feedback_de': 'Der Gesamtbetrag beträgt 125 EUR.',
                        'feedback_en': 'The total amount is EUR 125.',
                    },
                    {
                        'id': 'vendor', 'type': 'text',
                        'label_de': 'Lieferant', 'label_en': 'Vendor', 'unit': '',
                        'solution': {'de': 'Beispiel GmbH', 'en': 'Example Ltd'},
                        'feedback_de': 'Der Lieferant ist Beispiel GmbH.',
                        'feedback_en': 'The vendor is Example Ltd.',
                    },
                ],
                'micro_learning_de': 'Prüfe strukturierte Ergebnisse immer gegen die Quelldaten.',
                'micro_learning_en': 'Always verify structured results against the source data.',
                'max_points': 30 + position * 10,
            }
        return {
            'type': mission_type,
            'scheduled_date': scheduled_date.isoformat(),
            'topic_de': 'Finance-Falldaten strukturiert auswerten',
            'topic_en': 'Evaluate finance case data in a structured way',
            'learning_objective_de': 'Falldaten zweisprachig analysieren und Ergebnisse prüfen.',
            'learning_objective_en': 'Analyze bilingual case data and verify the results.',
            'variants': variants,
        }

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

    def test_only_creators_can_create_and_date_is_limited_to_one_mission(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.create_user('player@example.com')
        payload = self.manual_mission_payload()

        self.client.force_login(player)
        denied = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(creator)
        self.assertEqual(self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True).status_code, 201)
        payload['variants']['easy']['title_de'] = 'Titel 2'
        self.assertEqual(self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True).status_code, 409)

    @patch('accounts.services.email_notifications.send_mail')
    def test_published_mission_creation_does_not_send_email(self, send_mail_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.create_user('player@example.com')
        payload = self.manual_mission_payload()
        self.client.force_login(creator)

        response = self.client.post(
            '/api/auth/missions/schedule/', payload, content_type='application/json', secure=True,
        )

        self.assertEqual(response.status_code, 201)
        send_mail_mock.assert_not_called()

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

    @patch('accounts.services.email_notifications.send_mail', return_value=1)
    def test_weekly_reminder_uses_german_dates_and_mentions_monday_noon_deadline(self, send_mail_mock):
        user = self.create_user('reminder-copy@example.com')
        creator = self.create_user('creator-copy@example.com', Profile.ROLE_CONTENT_CREATOR)
        friday = date(2026, 8, 21)
        monday = date(2026, 8, 17)
        mission = self.create_mission(creator, monday)

        result = send_daily_mission_reminder(user, friday, [mission], [mission])

        self.assertEqual(result, 1)
        message = send_mail_mock.call_args.args[1]
        self.assertIn('17.08.2026', message)
        self.assertIn('Zeitraum: 17.08.2026 bis 21.08.2026', message)
        self.assertIn('bis Montag, den 24.08.2026, um 12:00 Uhr bearbeiten', message)
        self.assertIn('until Monday, 2026-08-24, at 12:00 noon', message)

    def test_creator_can_create_supported_types_and_edit_from_calendar(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        payload = self.manual_mission_payload(
            self.next_business_day(), mission_type=Mission.TYPE_MULTIPLE_CHOICE,
        )
        for variant in payload['variants'].values():
            variant['title_de'] = 'Mehrfachauswahl'
            variant['title_en'] = 'Multiple choice'
            variant['correct_indices'] = [1]
        created = self.client.post('/api/auth/missions/schedule/', payload, content_type='application/json', secure=True)
        self.assertEqual(created.status_code, 201)
        mission = Mission.objects.get(title_en='Multiple choice')
        self.assertTrue(mission.has_difficulty_variants)
        self.assertEqual(mission.topic_en, 'Shared topic')
        self.assertEqual(mission.variants[Mission.DIFFICULTY_HARD]['max_points'], 50)

        payload['type'] = Mission.TYPE_PROMPT_SELECTION
        for variant in payload['variants'].values():
            variant['title_de'] = 'Prompt-Auswahl'
            variant['title_en'] = 'Prompt selection'
        updated = self.client.patch(
            f'/api/auth/missions/{mission.id}/', payload, content_type='application/json', secure=True,
        )
        self.assertEqual(updated.status_code, 200)
        mission.refresh_from_db()
        self.assertEqual(mission.mission_type, Mission.TYPE_PROMPT_SELECTION)
        self.assertEqual(mission.title_de, 'Prompt-Auswahl')
        self.assertEqual(mission.content['feedback']['en'], 'Feedback easy')
        self.assertEqual(mission.variants[Mission.DIFFICULTY_MEDIUM]['title_en'], 'Prompt selection')

    def test_creator_can_create_and_edit_every_task_mission_type(self):
        creator = self.create_user('creator-task-editor@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        scheduled_date = self.next_business_day()
        created_ids = []

        for mission_type in sorted(Mission.TASK_TYPES):
            payload = self.manual_task_mission_payload(scheduled_date, mission_type)
            response = self.client.post(
                '/api/auth/missions/schedule/', payload, content_type='application/json', secure=True,
            )
            self.assertEqual(response.status_code, 201, response.json())
            mission = Mission.objects.get(scheduled_date=scheduled_date)
            self.assertEqual(mission.mission_type, mission_type)
            self.assertEqual(mission.variants['medium']['content']['case_data']['en'][0], '2026-08-01 | Example Ltd | EUR 125.00')
            self.assertEqual(mission.variants['hard']['content']['result_fields'][1]['solution']['de'], 'Beispiel GmbH')
            created_ids.append(mission.id)
            scheduled_date = self.next_business_day(scheduled_date)

        mission = Mission.objects.get(id=created_ids[0])
        payload = self.manual_task_mission_payload(mission.scheduled_date, mission.mission_type)
        payload['variants']['hard']['result_fields'][1]['solution']['en'] = 'Updated Vendor Ltd'
        payload['variants']['hard']['result_fields'][1]['feedback_en'] = 'The updated vendor is correct.'
        updated = self.client.patch(
            f'/api/auth/missions/{mission.id}/', payload, content_type='application/json', secure=True,
        )
        self.assertEqual(updated.status_code, 200, updated.json())
        mission.refresh_from_db()
        hard_field = mission.variants['hard']['content']['result_fields'][1]
        self.assertEqual(hard_field['solution']['en'], 'Updated Vendor Ltd')
        self.assertEqual(hard_field['feedback']['en'], 'The updated vendor is correct.')

        schedule = self.client.get(
            f'/api/auth/missions/schedule/?from={mission.scheduled_date}&to={mission.scheduled_date}', secure=True,
        )
        result_field = schedule.json()['missions'][mission.scheduled_date.isoformat()][0]['result_fields'][0]
        self.assertEqual(result_field['tolerance'], 0.01)
        self.assertEqual(result_field['feedback_en'], 'The total amount is EUR 125.')

    def test_manual_creator_requires_all_three_difficulty_variants(self):
        creator = self.create_user('creator-variants@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        payload = self.manual_mission_payload(self.next_business_day())
        payload['variants'].pop(Mission.DIFFICULTY_HARD)

        response = self.client.post(
            '/api/auth/missions/schedule/', payload, content_type='application/json', secure=True,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'exactly easy, medium, and hard variants are required')
        self.assertFalse(Mission.objects.filter(scheduled_date=payload['scheduled_date']).exists())

    def test_creator_cannot_schedule_missions_on_weekends(self):
        creator = self.create_user('creator-weekend-schedule@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        next_saturday = timezone.localdate() + timedelta(days=(5 - timezone.localdate().weekday()) % 7 or 7)
        payload = self.manual_mission_payload(next_saturday)

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

    @patch('accounts.views.dispatch_generation_run')
    def test_authenticated_user_can_start_training_without_saving_mission(self, dispatch_mock):
        player = self.create_user('training@example.com')
        self.client.force_login(player)

        response = self.client.post('/api/auth/training/generate/', {
            'type': Mission.TYPE_SINGLE_CHOICE,
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['generation_run']['kind'], GenerationRun.KIND_TRAINING_CHOICE)
        self.assertEqual(Mission.objects.count(), 0)
        dispatch_mock.assert_called_once()

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

    def test_chat_challenge_consume_hides_solutions_and_is_not_saved_as_mission(self):
        player = self.create_user('chat-player@example.com')
        self.client.force_login(player)
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_TRAINING_CHAT,
            status=GenerationRun.STATUS_COMPLETED,
            requested_by=player,
            request_payload={},
            result_payload={'training-chat': self.chat_challenge()},
        )

        response = self.client.post(f'/api/auth/mission-generation-runs/{run.id}/consume/', {},
                                    content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 200)
        question = response.json()['mission']['final_questions'][0]
        self.assertNotIn('solution', question)
        self.assertNotIn('tolerance', question)
        self.assertNotIn('feedback_en', question)
        self.assertEqual(response.json()['mission']['final_questions'][1]['option_values'], [True, False])
        self.assertEqual(Mission.objects.count(), 0)

    @patch('accounts.views.chat_reply', return_value='Pruefe zuerst die Differenz zwischen Ist und Plan.')
    def test_chat_challenge_allows_only_three_messages(self, chat_reply_mock):
        player = self.create_user('chat-limit@example.com')
        self.client.force_login(player)
        challenge_id = 'challenge-1'
        challenge = self.chat_challenge()
        challenge['history'] = []
        challenge['prompt_count'] = 0
        session = self.client.session
        session['training_chat_challenges'] = {challenge_id: challenge}
        session.save()

        for expected_remaining in (2, 1, 0):
            response = self.client.post('/api/auth/training/chat-challenge/message/', {
                'challenge_id': challenge_id, 'message': 'Gib mir einen Hinweis.', 'language': 'de',
            }, content_type='application/json', secure=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['remaining_prompts'], expected_remaining)
        blocked = self.client.post('/api/auth/training/chat-challenge/message/', {
            'challenge_id': challenge_id, 'message': 'Noch ein Hinweis.', 'language': 'de',
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

    @patch('accounts.services.email_notifications.send_mail')
    def test_approving_review_mission_does_not_send_email(self, send_mail_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        mission = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        mission.status = Mission.STATUS_REVIEW
        mission.save(update_fields=['status'])
        self.client.force_login(creator)

        response = self.client.post(f'/api/auth/missions/{mission.id}/approve/', secure=True)

        self.assertEqual(response.status_code, 200)
        send_mail_mock.assert_not_called()

    def test_creator_can_approve_and_reject_all_review_missions(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        first = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        second = self.create_mission(creator, timezone.localdate() + timedelta(days=2))
        Mission.objects.filter(id__in=[first.id, second.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        approved = self.client.post('/api/auth/missions/review/approve-all/', secure=True)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()['approved_count'], 2)
        self.assertEqual(
            Mission.objects.filter(id__in=[first.id, second.id], status=Mission.STATUS_PUBLISHED).count(),
            2,
        )

        third = self.create_mission(creator, timezone.localdate() + timedelta(days=3))
        third.status = Mission.STATUS_REVIEW
        third.save(update_fields=['status'])
        rejected = self.client.post('/api/auth/missions/review/reject-all/', secure=True)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()['rejected_count'], 1)
        third.refresh_from_db()
        self.assertEqual(third.status, Mission.STATUS_REJECTED)

    @patch('accounts.services.email_notifications.send_mail')
    def test_approve_all_review_missions_does_not_send_emails(self, send_mail_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        first = self.create_mission(creator, timezone.localdate() + timedelta(days=1))
        second = self.create_mission(creator, timezone.localdate() + timedelta(days=2))
        Mission.objects.filter(id__in=[first.id, second.id]).update(status=Mission.STATUS_REVIEW)
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/review/approve-all/', secure=True)

        self.assertEqual(response.status_code, 200)
        send_mail_mock.assert_not_called()

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

    def test_approve_all_is_atomic_when_a_day_would_exceed_one_mission(self):
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

    @patch('accounts.views.dispatch_generation_run')
    def test_creator_can_trigger_generation(self, dispatch_mock):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 202)
        run = GenerationRun.objects.get()
        self.assertEqual(run.kind, GenerationRun.KIND_WEEKLY_MISSIONS)
        self.assertTrue(run.request_payload['requirements'])
        dispatch_mock.assert_called_once_with(run)

    @patch('accounts.views.dispatch_generation_run')
    def test_creator_can_select_a_monday_for_generation(self, dispatch_mock):
        creator = self.create_user('creator-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        start, _end = next_calendar_week()
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': start.isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(GenerationRun.objects.get().week_start, start)
        dispatch_mock.assert_called_once()

    def test_generation_week_must_be_a_future_monday(self):
        creator = self.create_user('creator-invalid-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        start, _ = next_calendar_week()
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': (start + timedelta(days=1)).isoformat(),
        }, content_type='application/json', secure=True)

        self.assertEqual(response.status_code, 400)

    @patch('accounts.views.dispatch_generation_run')
    def test_creator_can_select_the_current_week_monday(self, dispatch_mock):
        creator = self.create_user('creator-current-week@example.com', Profile.ROLE_CONTENT_CREATOR)
        today = timezone.localdate()
        current_monday = today - timedelta(days=today.weekday())
        self.client.force_login(creator)

        response = self.client.post('/api/auth/missions/generate-next-week/', {
            'week_start': current_monday.isoformat(),
        }, content_type='application/json', secure=True)

        expected_status = 200 if not GenerationRun.objects.get().request_payload['requirements'] else 202
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(GenerationRun.objects.get().week_start, current_monday)

    def test_difficulty_leaderboard_uses_classified_attempts_only(self):
        creator = self.create_user('creator@example.com', Profile.ROLE_CONTENT_CREATOR)
        leader = self.create_user('leader@example.com', legacy_score=40)
        mission = self.create_mission(creator, points=90)
        MissionAttempt.objects.create(
            user=leader, mission=mission, answer={'selected_index': 0}, score=90,
            max_points=90, difficulty=Mission.DIFFICULTY_EASY,
        )
        self.client.force_login(leader)

        response = self.client.get('/api/auth/leaderboard/', secure=True)
        self.assertEqual(response.status_code, 200)
        entry = next(item for item in response.json()['entries'] if item['email'] == 'leader@example.com')
        self.assertEqual(entry['total_points'], 90)

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
                        difficulty=Mission.DIFFICULTY_EASY,
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
                difficulty=Mission.DIFFICULTY_EASY,
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
            max_points=40, difficulty=Mission.DIFFICULTY_EASY,
        )
        previous_attempt = MissionAttempt.objects.create(
            user=player, mission=previous, answer={'selected_indices': [0]}, score=90,
            max_points=90, difficulty=Mission.DIFFICULTY_EASY,
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

    def test_leaderboards_hide_users_without_points(self):
        creator = self.create_user('creator-empty-board@example.com', Profile.ROLE_CONTENT_CREATOR)
        empty_user = self.create_user('empty-board@example.com')
        zero_score_user = self.create_user('zero-board@example.com')
        scoring_user = self.create_user('scoring-board@example.com')
        mission = self.create_mission(creator)
        MissionAttempt.objects.create(
            user=zero_score_user, mission=mission, score=0, max_points=100,
            difficulty=Mission.DIFFICULTY_EASY,
        )
        MissionAttempt.objects.create(
            user=scoring_user, mission=mission, score=10, max_points=100,
            difficulty=Mission.DIFFICULTY_EASY,
        )
        self.client.force_login(scoring_user)

        data = self.client.get('/api/auth/leaderboard/?difficulty=easy', secure=True).json()

        for entries in (data['entries'], data['weekly_entries']):
            user_ids = [entry['user_id'] for entry in entries]
            self.assertNotIn(empty_user.id, user_ids)
            self.assertNotIn(zero_score_user.id, user_ids)
            self.assertIn(scoring_user.id, user_ids)

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
            week_start=week_start, week_end=week_start + timedelta(days=6),
            difficulty=Mission.DIFFICULTY_EASY, entries=entries,
        )
        self.client.force_login(user)

        response = self.client.get(f'/api/auth/leaderboard/history/{week_start.isoformat()}/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['entries'][0]['total_points'], 80)


class SkillProgressionTests(TestCase):
    def create_user(self, email, skill_level=Profile.SKILL_BEGINNER, role=Profile.ROLE_ACCOUNTANT):
        user = get_user_model().objects.create_user(username=email, email=email, password='Test1234!')
        Profile.objects.create(
            user=user,
            role=role,
            skill_level=skill_level,
            onboarding_completed=True,
        )
        return user

    def create_variant_mission(self, creator, scheduled_date=None):
        variants = {}
        labels = {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'}
        for difficulty in Mission.DIFFICULTIES:
            variants[difficulty] = {
                'title_de': labels[difficulty],
                'title_en': labels[difficulty],
                'description_de': f'{labels[difficulty]} Beschreibung',
                'description_en': f'{labels[difficulty]} description',
                'max_points': 100,
                'content': {
                    'question': {'de': f'{labels[difficulty]} Frage?', 'en': f'{labels[difficulty]} question?'},
                    'options': [{'de': 'Ja', 'en': 'Yes'}, {'de': 'Nein', 'en': 'No'}],
                    'correct_indices': [0],
                    'feedback': {'de': 'Richtig.', 'en': 'Correct.'},
                    'micro_learning': {'de': 'Prüfe Ergebnisse.', 'en': 'Verify results.'},
                },
            }
        easy = variants[Mission.DIFFICULTY_EASY]
        return Mission.objects.create(
            mission_type=Mission.TYPE_SINGLE_CHOICE,
            scheduled_date=scheduled_date or timezone.localdate(),
            title_de=easy['title_de'],
            title_en=easy['title_en'],
            description_de=easy['description_de'],
            description_en=easy['description_en'],
            content=easy['content'],
            max_points=100,
            topic_de='Ergebnisse prüfen',
            topic_en='Verify results',
            learning_objective_de='KI-Ergebnisse passend zur Komplexität prüfen.',
            learning_objective_en='Verify AI output at an appropriate complexity.',
            variants=variants,
            created_by=creator,
        )

    def configure(self, minimum=3, window=3, promotion=80, demotion=50, enabled=True):
        settings_object = SkillProgressionSettings.load()
        settings_object.automatic_progression_enabled = enabled
        settings_object.evaluation_window = window
        settings_object.minimum_missions = minimum
        settings_object.promotion_threshold = promotion
        settings_object.demotion_threshold = demotion
        settings_object.save()
        return settings_object

    def record_result(self, user, creator, difficulty, score):
        mission = self.create_variant_mission(creator)
        return MissionAttempt.objects.create(
            user=user,
            mission=mission,
            answer={'selected_indices': [0]},
            score=score,
            max_points=100,
            difficulty=difficulty,
        )

    def test_new_users_default_to_beginner(self):
        user = get_user_model().objects.create_user(username='new@example.com')
        profile = Profile.objects.create(user=user)
        self.assertEqual(profile.skill_level, Profile.SKILL_BEGINNER)

    def test_daily_variant_assignment_maps_all_skill_levels(self):
        creator = self.create_user('creator-levels@example.com', role=Profile.ROLE_CONTENT_CREATOR)
        mission = self.create_variant_mission(creator)
        for skill_level, difficulty in (
            (Profile.SKILL_BEGINNER, Mission.DIFFICULTY_EASY),
            (Profile.SKILL_ADVANCED, Mission.DIFFICULTY_MEDIUM),
            (Profile.SKILL_PRO, Mission.DIFFICULTY_HARD),
        ):
            user = self.create_user(f'{skill_level}@example.com', skill_level=skill_level)
            self.client.force_login(user)
            payload = self.client.get('/api/auth/missions/today/?lang=en', secure=True).json()['missions'][0]
            self.assertEqual(payload['difficulty'], difficulty)
            self.assertEqual(payload['title'], difficulty.title())
            self.assertEqual(MissionAssignment.objects.get(user=user, mission=mission).difficulty, difficulty)

    def test_progression_requires_minimum_and_resets_between_promotions(self):
        self.configure(minimum=2, window=2)
        creator = self.create_user('creator-progress@example.com', role=Profile.ROLE_CONTENT_CREATOR)
        user = self.create_user('progress@example.com')
        profile = user.profile
        self.record_result(user, creator, Mission.DIFFICULTY_EASY, 100)
        change, _summary = evaluate_skill_progression(profile)
        self.assertIsNone(change)
        profile.refresh_from_db()
        self.assertEqual(profile.skill_level, Profile.SKILL_BEGINNER)

        self.record_result(user, creator, Mission.DIFFICULTY_EASY, 80)
        change, summary = evaluate_skill_progression(profile)
        self.assertEqual(change['new_level'], Profile.SKILL_ADVANCED)
        self.assertEqual(summary['relevant_completed_missions'], 0)
        change, _summary = evaluate_skill_progression(profile)
        self.assertIsNone(change)

        self.record_result(user, creator, Mission.DIFFICULTY_MEDIUM, 100)
        profile.refresh_from_db()
        self.assertIsNone(evaluate_skill_progression(profile)[0])
        self.record_result(user, creator, Mission.DIFFICULTY_MEDIUM, 100)
        change, _summary = evaluate_skill_progression(profile)
        self.assertEqual(change['new_level'], Profile.SKILL_PRO)

    def test_demotion_boundaries_neutral_range_and_disabled_progression(self):
        self.configure(minimum=1, window=1)
        creator = self.create_user('creator-boundaries@example.com', role=Profile.ROLE_CONTENT_CREATOR)

        beginner = self.create_user('beginner@example.com')
        self.record_result(beginner, creator, Mission.DIFFICULTY_EASY, 20)
        self.assertIsNone(evaluate_skill_progression(beginner.profile)[0])

        advanced = self.create_user('advanced@example.com', Profile.SKILL_ADVANCED)
        self.record_result(advanced, creator, Mission.DIFFICULTY_MEDIUM, 49)
        change, _summary = evaluate_skill_progression(advanced.profile)
        self.assertEqual(change['new_level'], Profile.SKILL_BEGINNER)

        pro = self.create_user('pro@example.com', Profile.SKILL_PRO)
        self.record_result(pro, creator, Mission.DIFFICULTY_HARD, 100)
        self.assertIsNone(evaluate_skill_progression(pro.profile)[0])

        pro_low = self.create_user('pro-low@example.com', Profile.SKILL_PRO)
        self.record_result(pro_low, creator, Mission.DIFFICULTY_HARD, 20)
        change, _summary = evaluate_skill_progression(pro_low.profile)
        self.assertEqual(change['new_level'], Profile.SKILL_ADVANCED)

        neutral = self.create_user('neutral@example.com', Profile.SKILL_ADVANCED)
        self.record_result(neutral, creator, Mission.DIFFICULTY_MEDIUM, 50)
        self.assertIsNone(evaluate_skill_progression(neutral.profile)[0])

        disabled = self.create_user('disabled@example.com')
        self.configure(minimum=1, window=1, enabled=False)
        self.record_result(disabled, creator, Mission.DIFFICULTY_EASY, 100)
        self.assertIsNone(evaluate_skill_progression(disabled.profile)[0])

    def test_manual_admin_change_resets_evaluation_phase(self):
        creator = self.create_user('creator-manual@example.com', role=Profile.ROLE_CONTENT_CREATOR)
        admin = self.create_user('admin-manual@example.com', role=Profile.ROLE_ADMIN)
        user = self.create_user('manual@example.com')
        old_attempt = self.record_result(user, creator, Mission.DIFFICULTY_EASY, 100)
        self.client.force_login(admin)
        response = self.client.patch(
            f'/api/auth/users/{user.id}/skill-level/',
            {'skill_level': Profile.SKILL_PRO},
            content_type='application/json',
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.skill_level, Profile.SKILL_PRO)
        self.assertGreater(user.profile.skill_level_entered_at, old_attempt.completed_at)
        self.assertEqual(response.json()['user']['skill_progression']['relevant_completed_missions'], 0)

    def test_progression_settings_validation_and_persistence(self):
        admin = self.create_user('settings-admin@example.com', role=Profile.ROLE_ADMIN)
        self.client.force_login(admin)
        invalid = self.client.patch('/api/auth/settings/skill-progression/', {
            'automatic_progression_enabled': True,
            'evaluation_window': 10,
            'minimum_missions': 10,
            'promotion_threshold': 50,
            'demotion_threshold': 50,
        }, content_type='application/json', secure=True)
        self.assertEqual(invalid.status_code, 400)
        valid = self.client.patch('/api/auth/settings/skill-progression/', {
            'automatic_progression_enabled': False,
            'evaluation_window': 6,
            'minimum_missions': 4,
            'promotion_threshold': 85,
            'demotion_threshold': 40,
        }, content_type='application/json', secure=True)
        self.assertEqual(valid.status_code, 200)
        settings_object = SkillProgressionSettings.load()
        self.assertFalse(settings_object.automatic_progression_enabled)
        self.assertEqual(settings_object.evaluation_window, 6)

    def test_users_can_appear_in_multiple_difficulty_leaderboards(self):
        creator = self.create_user('creator-board@example.com', role=Profile.ROLE_CONTENT_CREATOR)
        user = self.create_user('board@example.com')
        self.record_result(user, creator, Mission.DIFFICULTY_EASY, 30)
        self.record_result(user, creator, Mission.DIFFICULTY_MEDIUM, 60)
        self.record_result(user, creator, Mission.DIFFICULTY_HARD, 90)
        set_skill_level_manually(user.profile, Profile.SKILL_PRO)
        self.client.force_login(user)
        for difficulty, expected in (('easy', 30), ('medium', 60), ('hard', 90)):
            data = self.client.get(f'/api/auth/leaderboard/?difficulty={difficulty}', secure=True).json()
            entry = next(item for item in data['entries'] if item['user_id'] == user.id)
            weekly_entry = next(item for item in data['weekly_entries'] if item['user_id'] == user.id)
            self.assertEqual(entry['total_points'], expected)
            self.assertEqual(entry['completed_missions'], 1)
            self.assertEqual(weekly_entry['total_points'], expected)

    def test_historical_leaderboard_keeps_scoring_users_after_skill_level_change(self):
        user = self.create_user('history-skill@example.com')
        today = timezone.localdate()
        current_week_start = today - timedelta(days=today.weekday())
        week_start = current_week_start - timedelta(days=7)
        WeeklyLeaderboardSnapshot.objects.create(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            difficulty=Mission.DIFFICULTY_EASY,
            entries=[{
                'rank': 1, 'user_id': user.id, 'name': 'History Skill', 'email': user.email,
                'first_name': '', 'last_name': '', 'total_points': 80,
                'completed_missions': 4, 'level': 'Starter',
            }, {
                'rank': 2, 'user_id': 999999, 'name': 'No Points', 'email': 'none@example.com',
                'first_name': '', 'last_name': '', 'total_points': 0,
                'completed_missions': 0, 'level': 'Starter',
            }],
        )
        set_skill_level_manually(user.profile, Profile.SKILL_PRO)
        self.client.force_login(user)

        response = self.client.get(
            f'/api/auth/leaderboard/history/{week_start.isoformat()}/?difficulty=easy', secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([entry['user_id'] for entry in response.json()['entries']], [user.id])

    def test_same_day_level_change_keeps_one_completed_assignment(self):
        self.configure(minimum=1, window=1)
        creator = self.create_user('creator-day@example.com', role=Profile.ROLE_CONTENT_CREATOR)
        user = self.create_user('day@example.com')
        mission = self.create_variant_mission(creator)
        second = self.create_variant_mission(creator)
        self.client.force_login(user)

        daily = self.client.get('/api/auth/missions/today/?lang=en', secure=True).json()['missions']
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]['difficulty'], Mission.DIFFICULTY_EASY)
        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id,
            'answer': 0,
            'language': 'en',
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['skill_change']['new_level'], Profile.SKILL_ADVANCED)
        daily = self.client.get('/api/auth/missions/today/?lang=en', secure=True).json()['missions']
        self.assertEqual(len(daily), 1)
        self.assertTrue(daily[0]['completed'])
        self.assertEqual(daily[0]['difficulty'], Mission.DIFFICULTY_EASY)
        blocked = self.client.post('/api/auth/progress/complete/', {
            'mission_id': second.id,
            'answer': 0,
        }, content_type='application/json', secure=True)
        self.assertEqual(blocked.status_code, 404)

        tomorrow = self.create_variant_mission(creator, timezone.localdate() + timedelta(days=1))
        from accounts.views import assigned_mission_difficulty
        self.assertEqual(
            assigned_mission_difficulty(tomorrow, user, create=True),
            Mission.DIFFICULTY_MEDIUM,
        )


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
                content = {
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
                }
                variant = {
                    'title_de': f'Prompt {index}', 'title_en': f'Prompt {index}',
                    'description_de': 'Kurze Beschreibung', 'description_en': 'Short description',
                    'points': 30,
                    'content': content,
                }
                missions.append({
                    'date': scheduled_date.isoformat(),
                    'type': Mission.TYPE_PROMPT_SELECTION,
                    'topic_de': 'Gute Prompts', 'topic_en': 'Good prompts',
                    'learning_objective_de': 'Präzise Prompts formulieren.',
                    'learning_objective_en': 'Write precise prompts.',
                    'variants': {difficulty: {**variant} for difficulty in Mission.DIFFICULTIES},
                    'content': content,
                })
        return {'missions': missions}

    def test_validator_rejects_invalid_correct_index(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        payload['missions'][0]['content']['correct_option_index'] = 9
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_validator_requires_exactly_three_variants_with_one_shared_objective(self):
        start, _ = next_calendar_week()
        payload = self.valid_payload({start: 1})
        normalized = validate_generated_payload(payload, {start: 1})[0]
        self.assertEqual(set(normalized['variants']), set(Mission.DIFFICULTIES))
        self.assertEqual(normalized['learning_objective_en'], 'Write precise prompts.')
        payload['missions'][0]['variants'].pop(Mission.DIFFICULTY_HARD)
        with self.assertRaises(MissionValidationError):
            validate_generated_payload(payload, {start: 1})

    def test_prompt_targets_accessible_everyday_finance_ai_learning(self):
        start, _ = next_calendar_week()
        prompt = build_user_prompt({start: 1})
        self.assertTrue(SYSTEM_PROMPT.startswith('Reasoning: low.'))
        self.assertIn('little or no practical AI experience', SYSTEM_PROMPT)
        self.assertIn('beginner-friendly', SYSTEM_PROMPT)
        self.assertIn('monthly, quarterly, and year-end reports', SYSTEM_PROMPT)
        self.assertIn('Do not require knowledge of machine-learning algorithms', SYSTEM_PROMPT)
        self.assertIn('practical everyday AI usage', prompt)
        self.assertIn('micro_learning_de', prompt)
        self.assertIn('micro-learning explanation', SYSTEM_PROMPT)
        self.assertIn('output format', SYSTEM_PROMPT)
        self.assertIn('at least three interacting constraints', SYSTEM_PROMPT)
        self.assertIn('compare the three questions side by side', prompt)
        self.assertIn('"points":20', prompt)
        self.assertIn('"points":40', prompt)

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
        slots = {start + timedelta(days=offset): 1 for offset in range(7)}
        batches = split_target_slots(slots)
        self.assertEqual(len(batches), 7)
        self.assertTrue(all(sum(batch.values()) == 1 for batch in batches))

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
        traffic_content = {
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
        traffic['missions'][0]['content'] = traffic_content
        for variant in traffic['missions'][0]['variants'].values():
            variant['content'] = traffic_content
        normalized = validate_generated_payload(traffic, {start: 1})
        self.assertEqual(normalized[0]['content']['statements'][1]['correct_color'], 'yellow')

    def task_candidate(self):
        return {
            'mission_type': Mission.TYPE_BULK_CATEGORIZATION,
            'title_de': 'Task', 'title_en': 'Task', 'description_de': 'd', 'description_en': 'd',
            'max_points': 40, 'content': {
                'task': {'de': 't', 'en': 't'}, 'case_data': {'de': [], 'en': []}, 'case_format': 'table',
                'result_fields': [], 'micro_learning': {'de': 'x' * 30, 'en': 'x' * 30},
            },
        }

    @patch('accounts.services.ai_task_challenge.generate_task_challenge')
    @patch('accounts.services.ai_mission_generator.call_ai')
    def test_weekly_generation_splits_workweek_into_quiz_and_task_days(self, call_ai_mock, generate_task_mock):
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
        generate_task_mock.side_effect = lambda *args, **kwargs: self.task_candidate()

        created, actual_start, actual_end = generate_next_week(creator)
        self.assertEqual((actual_start, actual_end), (start, end))

        # Monday already has content, so it is left untouched entirely - no top-up.
        monday_missions = Mission.objects.filter(scheduled_date=start)
        self.assertEqual(monday_missions.count(), 1)
        self.assertEqual(monday_missions.first().status, Mission.STATUS_PUBLISHED)

        # Weekends are never scheduled.
        weekend_days = [start + timedelta(days=offset) for offset in (5, 6)]
        self.assertEqual(Mission.objects.filter(scheduled_date__in=weekend_days).count(), 0)

        # 4 open weekdays (Tue-Fri): each gets exactly one mission topic.
        self.assertEqual(len(created), 4)
        self.assertTrue(all(mission.status == Mission.STATUS_REVIEW for mission in created))
        self.assertTrue(all(mission.generated_by_ai for mission in created))
        task_created = [mission for mission in created if mission.mission_type in Mission.TASK_TYPES]
        quiz_created = [mission for mission in created if mission.mission_type in Mission.CHOICE_TYPES]
        self.assertEqual(len(task_created), 2)
        self.assertEqual(len(quiz_created), 2)
        for day in (start + timedelta(days=offset) for offset in range(1, 5)):
            day_missions = [mission for mission in created if mission.scheduled_date == day]
            self.assertEqual(len(day_missions), 1)
            self.assertTrue(day_missions[0].has_difficulty_variants)

    @patch('accounts.services.ai_task_challenge.generate_task_challenge')
    @patch('accounts.services.ai_mission_generator.call_ai')
    def test_invalid_ai_response_creates_no_missions(self, call_ai_mock, generate_task_mock):
        creator = self.create_creator()
        call_ai_mock.return_value = {'missions': []}
        generate_task_mock.side_effect = AiMissionGenerationError('boom')
        with self.assertRaises(AiMissionGenerationError):
            generate_next_week(creator)
        self.assertEqual(Mission.objects.count(), 0)


class AiTaskChallengeTests(TestCase):
    def make_user(self, email, role=Profile.ROLE_ACCOUNTANT):
        user = get_user_model().objects.create_user(username=email, email=email, password='Test1234!')
        Profile.objects.create(user=user, role=role, onboarding_completed=True)
        return user

    def raw_payload(self, rows=30):
        return {
            'title_de': 'Buchungen kategorisieren', 'title_en': 'Categorize bookings',
            'description_de': 'Ordne Buchungen den Kostenarten zu.', 'description_en': 'Assign bookings to cost types.',
            'task_de': 'Ordne jede Zeile zu und nenne die Summe je Kategorie.',
            'task_en': 'Assign every line and report the total per category.',
            'categories_de': ['Reisekosten', 'Buerobedarf', 'IT'],
            'categories_en': ['Travel', 'Office', 'IT'],
            'rows': [
                {
                    'date': '2026-03-%02d' % (index % 28 + 1),
                    'description_de': 'Position %d' % index, 'description_en': 'Item %d' % index,
                    'amount': round(10 + index * 1.5, 2), 'category_index': index % 3,
                }
                for index in range(rows)
            ],
            'micro_learning_de': 'KI beschleunigt das Kategorisieren grosser Datenmengen; pruefe Stichproben stets selbst nach.',
            'micro_learning_en': 'AI speeds up categorizing large data volumes; always spot-check its assignments yourself.',
        }

    def content(self):
        from accounts.services.ai_task_challenge import validate_task_challenge
        return validate_task_challenge(self.raw_payload(), 'bulk_categorization')['content']

    def create_task_mission(self, creator, status=Mission.STATUS_PUBLISHED):
        content = self.content()
        return Mission.objects.create(
            mission_type=Mission.TYPE_BULK_CATEGORIZATION,
            scheduled_date=timezone.localdate(),
            title_de='Buchungen kategorisieren', title_en='Categorize bookings',
            description_de='Ordne Buchungen zu.', description_en='Assign bookings.',
            content=content, max_points=40, status=status, generated_by_ai=True, created_by=creator,
        )

    def test_validation_computes_totals_and_public_hides_solutions(self):
        from accounts.services.ai_task_challenge import public_content, validate_task_challenge
        candidate = validate_task_challenge(self.raw_payload(), 'bulk_categorization')
        fields = candidate['content']['result_fields']
        self.assertEqual(len(fields), 3)
        expected = [0.0, 0.0, 0.0]
        for index in range(30):
            expected[index % 3] += round(10 + index * 1.5, 2)
        self.assertEqual([round(field['solution'], 2) for field in fields], [round(value, 2) for value in expected])
        self.assertIn('€10.00', candidate['content']['case_data']['en'][0])
        self.assertIn('€', fields[0]['feedback']['en'])
        self.assertNotIn('10,00', candidate['content']['case_data']['en'][0])
        public = public_content(candidate['content'], 'de')
        for field in public['result_fields']:
            self.assertNotIn('solution', field)
            self.assertNotIn('tolerance', field)
        self.assertEqual(len(public['case_data']), 30)

    def test_invalid_category_index_is_rejected(self):
        from accounts.services.ai_mission_generator import AiMissionGenerationError
        from accounts.services.ai_task_challenge import validate_task_challenge
        payload = self.raw_payload()
        payload['rows'][0]['category_index'] = 9
        with self.assertRaises(AiMissionGenerationError):
            validate_task_challenge(payload, 'bulk_categorization')

    def test_daily_task_challenge_hides_solutions(self):
        creator = self.make_user('creator-task@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.make_user('player-task@example.com')
        self.create_task_mission(creator)
        self.client.force_login(player)
        response = self.client.get('/api/auth/missions/today/?lang=de', secure=True)
        self.assertEqual(response.status_code, 200)
        mission = response.json()['missions'][0]
        self.assertEqual(mission['type'], Mission.TYPE_BULK_CATEGORIZATION)
        self.assertEqual(len(mission['content']['case_data']), 30)
        for field in mission['content']['result_fields']:
            self.assertNotIn('solution', field)

    def test_scoring_awards_partial_points_and_stores_prompt(self):
        creator = self.make_user('creator-score@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.make_user('player-score@example.com')
        mission = self.create_task_mission(creator)
        fields = mission.content['result_fields']
        values = {field['id']: field['solution'] for field in fields}
        values[fields[0]['id']] = -1  # one wrong
        self.client.force_login(player)
        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': {'values': values, 'prompt': 'Kategorisiere diese Buchungen ...'},
            'language': 'de',
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        result = response.json()['result']
        self.assertEqual(result['correct_count'], 2)
        self.assertEqual(result['total_count'], 3)
        self.assertFalse(result['correct'])
        self.assertEqual(result['score'], 40 * 2 // 3)
        attempt = MissionAttempt.objects.get(user=player, mission=mission)
        self.assertEqual(attempt.answer['prompt'], 'Kategorisiere diese Buchungen ...')

    def test_full_score_marks_correct(self):
        creator = self.make_user('creator-full@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.make_user('player-full@example.com')
        mission = self.create_task_mission(creator)
        values = {field['id']: field['solution'] for field in mission.content['result_fields']}
        self.client.force_login(player)
        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': {'values': values, 'prompt': ''}, 'language': 'de',
        }, content_type='application/json', secure=True)
        result = response.json()['result']
        self.assertTrue(result['correct'])
        self.assertEqual(result['score'], 40)

    def test_missing_values_are_rejected(self):
        creator = self.make_user('creator-missing@example.com', Profile.ROLE_CONTENT_CREATOR)
        player = self.make_user('player-missing@example.com')
        mission = self.create_task_mission(creator)
        self.client.force_login(player)
        response = self.client.post('/api/auth/progress/complete/', {
            'mission_id': mission.id, 'answer': {'prompt': 'x'}, 'language': 'de',
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)

    def test_generate_endpoint_starts_review_mission_run(self):
        creator = self.make_user('creator-gen@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        with patch('accounts.views.dispatch_generation_run') as dispatch_mock:
            response = self.client.post('/api/auth/missions/generate-task-challenge/', {
                'mission_type': 'bulk_categorization',
            }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 202)
        run = GenerationRun.objects.get()
        self.assertEqual(run.kind, GenerationRun.KIND_SCHEDULED_TASK)
        self.assertEqual(run.request_payload['requirements'][0]['mission_type'], 'bulk_categorization')
        self.assertEqual(Mission.objects.count(), 0)
        dispatch_mock.assert_called_once_with(run)

    def test_generate_endpoint_rejects_non_creator(self):
        player = self.make_user('player-forbidden@example.com')
        self.client.force_login(player)
        response = self.client.post('/api/auth/missions/generate-task-challenge/', {}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 403)

    def test_generate_endpoint_rejects_unknown_mission_type(self):
        creator = self.make_user('creator-unknown@example.com', Profile.ROLE_CONTENT_CREATOR)
        self.client.force_login(creator)
        response = self.client.post('/api/auth/missions/generate-task-challenge/', {
            'mission_type': 'not_a_real_type',
        }, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)

    def test_generate_task_day_candidates_fills_requested_days(self):
        from accounts.services import ai_mission_generator
        candidate = {
            'mission_type': Mission.TYPE_BULK_CATEGORIZATION, 'title_de': 't', 'title_en': 't',
            'description_de': 'd', 'description_en': 'd', 'max_points': 40, 'content': self.content(),
        }
        day = timezone.localdate()
        with patch('accounts.services.ai_task_challenge.generate_task_challenge', return_value=candidate):
            candidates, failed_days = ai_mission_generator.generate_task_day_candidates([day])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['scheduled_date'], day)
        self.assertEqual(failed_days, [])

    def test_generate_task_day_candidates_falls_back_on_failure(self):
        from accounts.services import ai_mission_generator
        from accounts.services.ai_mission_generator import AiMissionGenerationError
        day = timezone.localdate()
        with patch('accounts.services.ai_task_challenge.generate_task_challenge', side_effect=AiMissionGenerationError('boom')):
            candidates, failed_days = ai_mission_generator.generate_task_day_candidates([day])
        self.assertEqual(candidates, [])
        self.assertEqual(failed_days, [day])


class AiTaskChallengeOtherTypesTests(TestCase):
    """Validates the 4 additional task challenge types beyond bulk_categorization."""

    def plan_actual_deviation_payload(self):
        rows = []
        for index in range(24):
            if index < 5:
                actual = 1200.0
            elif index < 16:
                actual = 1000.0
            else:
                actual = 1050.0
            rows.append({
                'cost_center_de': f'Kostenstelle {index}', 'cost_center_en': f'Cost center {index}',
                'plan': 1000.0, 'actual': actual,
            })
        return {
            'title_de': 'Abweichungen finden', 'title_en': 'Find deviations',
            'description_de': 'Finde Budgetueberschreitungen.', 'description_en': 'Find budget overruns.',
            'task_de': 'Finde die Kostenstellen ueber Plan.', 'task_en': 'Find cost centers over plan.',
            'rows': rows,
            'micro_learning_de': 'KI findet Ausreisser in grossen Budgetlisten schneller; pruefe die Treffer stichprobenartig nach.',
            'micro_learning_en': 'AI spots outliers in large budget lists faster; spot-check the hits afterwards.',
        }

    def test_plan_actual_deviation_computes_totals(self):
        from accounts.services.ai_task_challenge import validate_task_challenge
        candidate = validate_task_challenge(self.plan_actual_deviation_payload(), 'plan_actual_deviation')
        fields = {field['id']: field for field in candidate['content']['result_fields']}
        self.assertAlmostEqual(fields['total_overrun']['solution'], 1400.0)
        self.assertEqual(fields['count_over_threshold']['solution'], 5)
        self.assertAlmostEqual(fields['max_deviation']['solution'], 200.0)

    def duplicate_payment_hunt_payload(self):
        rows = []
        duplicate_amounts = [500.0, 600.0, 700.0, 800.0]
        for pair_index, amount in enumerate(duplicate_amounts):
            for copy_index in range(2):
                rows.append({
                    'date': '2026-03-01', 'invoice_number': f'DUP-{pair_index}',
                    'vendor_de': f'Lieferant {pair_index}{"" if copy_index == 0 else " GmbH"}',
                    'vendor_en': f'Vendor {pair_index}', 'amount': amount,
                })
        for index in range(16):
            rows.append({
                'date': '2026-03-02', 'invoice_number': f'INV-{index}',
                'vendor_de': f'Einzellieferant {index}', 'vendor_en': f'Single vendor {index}',
                'amount': 10.0 + index,
            })
        return {
            'title_de': 'Doppelzahlungen finden', 'title_en': 'Find duplicate payments',
            'description_de': 'Finde doppelt bezahlte Rechnungen.', 'description_en': 'Find duplicate invoice payments.',
            'task_de': 'Finde die Doppelzahlungen.', 'task_en': 'Find the duplicate payments.',
            'rows': rows,
            'micro_learning_de': 'KI findet Duplikate ueber viele Zeilen zuverlaessiger als das Auge; pruefe Treffer stichprobenartig nach.',
            'micro_learning_en': 'AI finds duplicates across many rows more reliably than the eye; spot-check hits afterwards.',
        }

    def test_duplicate_payment_hunt_computes_totals(self):
        from accounts.services.ai_task_challenge import validate_task_challenge
        candidate = validate_task_challenge(self.duplicate_payment_hunt_payload(), 'duplicate_payment_hunt')
        fields = {field['id']: field for field in candidate['content']['result_fields']}
        self.assertEqual(fields['duplicate_pairs_count']['solution'], 4)
        self.assertAlmostEqual(fields['risk_amount_sum']['solution'], 2600.0)

    def invoice_extraction_payload(self):
        vendors = [
            ('V1', 100.0, 3), ('V2', 200.0, 3), ('V3', 50.0, 3),
        ]
        invoices = []
        counter = 0
        for vendor_key, amount, count in vendors:
            for copy_index in range(count):
                counter += 1
                invoices.append({
                    'invoice_number': f'{vendor_key}-{copy_index}',
                    'vendor_de': f'{vendor_key} GmbH', 'vendor_en': f'{vendor_key} Ltd',
                    'date': '2026-03-01', 'amount': amount,
                    'text_de': f'Rechnung {vendor_key}-{copy_index} ueber {amount} Euro.',
                    'text_en': f'Invoice {vendor_key}-{copy_index} for {amount} euros.',
                })
        for vendor_key, amount in (('V4', 550.0), ('V5', 10.0), ('V6', 20.0)):
            counter += 1
            invoices.append({
                'invoice_number': f'{vendor_key}-0',
                'vendor_de': f'{vendor_key} GmbH', 'vendor_en': f'{vendor_key} Ltd',
                'date': '2026-03-01', 'amount': amount,
                'text_de': f'Rechnung {vendor_key}-0 ueber {amount} Euro.',
                'text_en': f'Invoice {vendor_key}-0 for {amount} euros.',
            })
        return {
            'title_de': 'Rechnungen extrahieren', 'title_en': 'Extract invoices',
            'description_de': 'Lies die Rechnungstexte.', 'description_en': 'Read the invoice texts.',
            'task_de': 'Extrahiere die geforderten Angaben.', 'task_en': 'Extract the requested facts.',
            'invoices': invoices,
            'micro_learning_de': 'KI extrahiert Fakten aus Fliesstext zuverlaessig; pruefe Zahlen stichprobenartig nach.',
            'micro_learning_en': 'AI reliably extracts facts from prose text; spot-check figures afterwards.',
        }

    def test_invoice_extraction_computes_totals_and_scores_text_fields(self):
        from accounts.services.ai_task_challenge import evaluate_task_answers, validate_task_challenge
        candidate = validate_task_challenge(self.invoice_extraction_payload(), 'invoice_extraction')
        content = candidate['content']
        self.assertEqual(content['case_format'], 'prose')
        fields = {field['id']: field for field in content['result_fields']}
        self.assertEqual(fields['top_invoice_number']['solution'], {'de': 'V4-0', 'en': 'V4-0'})
        self.assertEqual(fields['top_vendor']['solution'], {'de': 'V2 GmbH', 'en': 'V2 Ltd'})
        self.assertAlmostEqual(fields['total_amount']['solution'], 1630.0)

        values = {
            'top_invoice_number': '  v4-0 ',  # different case/whitespace, must still match
            'top_vendor': 'V2 GmbH',
            'total_amount': 1630.0,
        }
        result = evaluate_task_answers(content, values, 'de')
        self.assertTrue(result['all_correct'])

        wrong_values = {**values, 'top_invoice_number': 'V1-0'}
        wrong_result = evaluate_task_answers(content, wrong_values, 'de')
        self.assertFalse(wrong_result['all_correct'])
        self.assertEqual(wrong_result['correct_count'], 2)


class AiTaskChallengeDifficultyContractTests(TestCase):
    def common(self):
        return {
            'title_de': 'Finanzdaten analysieren', 'title_en': 'Analyze finance data',
            'description_de': 'Bearbeiten Sie einen fiktiven Finanzdatensatz.',
            'description_en': 'Work with a fictional finance dataset.',
            'task_de': 'Wird deterministisch ersetzt.', 'task_en': 'Replaced deterministically.',
            'micro_learning_de': 'Klare Anforderungen und eine anschließende Stichprobe machen KI-Ergebnisse nachvollziehbar und sicher nutzbar.',
            'micro_learning_en': 'Clear requirements and a subsequent spot-check make AI output traceable and safe to use.',
        }

    def bulk_payload(self, difficulty):
        category_count = {'easy': 3, 'medium': 4, 'hard': 5}[difficulty]
        row_count = {'easy': 24, 'medium': 36, 'hard': 48}[difficulty]
        categories_de = ['Reise', 'Büro', 'IT', 'Marketing', 'Weiterbildung'][:category_count]
        categories_en = ['Travel', 'Office', 'IT', 'Marketing', 'Training'][:category_count]
        return {
            **self.common(), 'categories_de': categories_de, 'categories_en': categories_en,
            'rows': [{
                'date': f'2026-03-{index % 28 + 1:02d}',
                'description_de': f'{categories_de[index % category_count]} Beleg {index}',
                'description_en': f'{categories_en[index % category_count]} receipt {index}',
                'amount': 100 + index, 'category_index': index % category_count,
            } for index in range(row_count)],
        }

    def plan_payload(self, difficulty):
        row_count = {'easy': 24, 'medium': 36, 'hard': 48}[difficulty]
        rows = []
        for index in range(row_count):
            actual = 1200 if index < 8 else (900 if difficulty == 'hard' and index < 14 else 1000)
            rows.append({
                'cost_center_de': f'Kostenstelle {index}', 'cost_center_en': f'Cost center {index}',
                'plan': 1000, 'actual': actual,
            })
        return {**self.common(), 'rows': rows}

    def duplicate_payload(self, difficulty):
        pair_count = {'easy': 3, 'medium': 4, 'hard': 6}[difficulty]
        row_count = {'easy': 24, 'medium': 36, 'hard': 48}[difficulty]
        rows = []
        for pair_index in range(pair_count):
            for copy_index in range(2):
                rows.append({
                    'date': '2026-03-01', 'invoice_number': f'DUP-{pair_index}',
                    'vendor_de': f'Lieferant {pair_index}-{copy_index}',
                    'vendor_en': f'Vendor {pair_index}-{copy_index}', 'amount': 500 + pair_index * 100,
                })
        rows.extend({
            'date': '2026-03-02', 'invoice_number': f'UNIQUE-{index}',
            'vendor_de': f'Einzellieferant {index}', 'vendor_en': f'Single vendor {index}',
            'amount': 50 + index,
        } for index in range(row_count - len(rows)))
        return {**self.common(), 'rows': rows}

    def invoice_payload(self, difficulty):
        invoice_count = {'easy': 12, 'medium': 16, 'hard': 20}[difficulty]
        invoices = []
        for index in range(invoice_count):
            vendor = index % 4
            amount = 100 + index * 10
            invoices.append({
                'invoice_number': f'INV-{index}',
                'vendor_de': f'Lieferant {vendor} GmbH', 'vendor_en': f'Vendor {vendor} Ltd',
                'date': '2026-03-01', 'amount': amount,
                'text_de': f'Lieferant {vendor} stellt Rechnung INV-{index} über {amount} Euro.',
                'text_en': f'Vendor {vendor} issued invoice INV-{index} for {amount} euros.',
            })
        return {**self.common(), 'invoices': invoices}

    def test_every_task_type_has_observable_difficulty_progression(self):
        from accounts.services.ai_task_challenge import validate_task_challenge
        expected_fields = {
            'bulk_categorization': {'easy': 3, 'medium': 4, 'hard': 5},
            'plan_actual_deviation': {'easy': 2, 'medium': 3, 'hard': 5},
            'duplicate_payment_hunt': {'easy': 1, 'medium': 2, 'hard': 3},
            'invoice_extraction': {'easy': 2, 'medium': 3, 'hard': 4},
        }
        builders = {
            'bulk_categorization': self.bulk_payload,
            'plan_actual_deviation': self.plan_payload,
            'duplicate_payment_hunt': self.duplicate_payload,
            'invoice_extraction': self.invoice_payload,
        }
        expected_items = {
            'bulk_categorization': [24, 36, 48],
            'plan_actual_deviation': [24, 36, 48],
            'duplicate_payment_hunt': [24, 36, 48],
            'invoice_extraction': [12, 16, 20],
        }
        for mission_type, builder in builders.items():
            variants = [
                validate_task_challenge(builder(difficulty), mission_type, difficulty=difficulty)
                for difficulty in ('easy', 'medium', 'hard')
            ]
            self.assertEqual([len(item['content']['case_data']['de']) for item in variants], expected_items[mission_type])
            self.assertEqual(
                [len(item['content']['result_fields']) for item in variants],
                [expected_fields[mission_type][difficulty] for difficulty in ('easy', 'medium', 'hard')],
            )
            self.assertEqual([item['max_points'] for item in variants], [30, 40, 50])
            self.assertEqual(len({item['content']['task']['de'] for item in variants}), 3)

    def test_wrong_difficulty_volume_is_rejected(self):
        payload = self.plan_payload('easy')
        payload['rows'].append({
            'cost_center_de': 'Extra', 'cost_center_en': 'Extra', 'plan': 1000, 'actual': 900,
        })
        with self.assertRaisesRegex(AiMissionGenerationError, 'exactly 24 rows'):
            from accounts.services.ai_task_challenge import validate_task_challenge
            validate_task_challenge(payload, 'plan_actual_deviation', difficulty='easy')

    def test_prompt_contracts_name_exact_volume_and_results(self):
        from accounts.prompts.task_challenges import build_difficulty_instruction
        easy = build_difficulty_instruction('plan_actual_deviation', 'easy')
        hard = build_difficulty_instruction('plan_actual_deviation', 'hard')
        self.assertIn('exactly 24 rows', easy)
        self.assertIn('only:', easy)
        self.assertIn('exactly 48 rows', hard)
        self.assertIn('average positive overrun', hard)
        self.assertIn('no others', hard)


class AiTaskChallengeTrainingTests(TestCase):
    def make_user(self, email):
        user = get_user_model().objects.create_user(username=email, email=email, password='Test1234!')
        Profile.objects.create(user=user, role=Profile.ROLE_ACCOUNTANT, onboarding_completed=True)
        return user

    def candidate(self):
        from accounts.services.ai_task_challenge import validate_task_challenge
        payload = {
            'title_de': 'Buchungen', 'title_en': 'Bookings',
            'description_de': 'Ordne zu.', 'description_en': 'Assign.',
            'task_de': 'Ordne jede Zeile zu und nenne die Summe je Kategorie.',
            'task_en': 'Assign every line and report totals.',
            'categories_de': ['Reise', 'Buero', 'IT'], 'categories_en': ['Travel', 'Office', 'IT'],
            'rows': [
                {'date': '2026-03-%02d' % (i % 28 + 1), 'description_de': 'P%d' % i, 'description_en': 'I%d' % i,
                 'amount': round(10 + i * 1.5, 2), 'category_index': i % 3}
                for i in range(30)
            ],
            'micro_learning_de': 'KI beschleunigt das Kategorisieren; pruefe Stichproben stets selbst nach dem Ergebnis.',
            'micro_learning_en': 'AI speeds up categorizing; always spot-check the assignments yourself afterwards.',
        }
        return validate_task_challenge(payload, 'bulk_categorization')

    def test_training_generate_hides_solutions_then_submit_scores(self):
        player = self.make_user('training-task@example.com')
        self.client.force_login(player)
        candidate = self.candidate()
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_TRAINING_TASK,
            status=GenerationRun.STATUS_COMPLETED,
            requested_by=player,
            request_payload={},
            result_payload={'training-task': candidate},
        )
        generated = self.client.post(f'/api/auth/mission-generation-runs/{run.id}/consume/', {},
                                     content_type='application/json', secure=True)
        self.assertEqual(generated.status_code, 200)
        mission = generated.json()['mission']
        challenge_id = mission['id']
        self.assertEqual(len(mission['case_data_de']), 30)
        for field in mission['result_fields']:
            self.assertNotIn('solution', field)
        # solve fully using the known candidate solutions
        values = {field['id']: field['solution'] for field in candidate['content']['result_fields']}
        submitted = self.client.post('/api/auth/training/task-challenge/submit/', {
            'challenge_id': challenge_id, 'values': values, 'language': 'de',
        }, content_type='application/json', secure=True)
        self.assertEqual(submitted.status_code, 200)
        result = submitted.json()['result']
        self.assertTrue(result['correct'])
        self.assertEqual(result['correct_count'], 3)
        # session challenge is consumed
        again = self.client.post('/api/auth/training/task-challenge/submit/', {
            'challenge_id': challenge_id, 'values': values, 'language': 'de',
        }, content_type='application/json', secure=True)
        self.assertEqual(again.status_code, 404)

    def test_training_generate_requires_authentication(self):
        response = self.client.post('/api/auth/training/task-challenge/generate/', {},
                                    content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 401)
