import json
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib import error

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .models import GenerationRun, Mission, Profile
from .services.n8n_client import (
    N8NClient,
    N8NConnectionError,
    N8NConfigurationError,
    N8NHTTPError,
    N8NResponseError,
)


def response_with(body):
    response = MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    return response


@override_settings(DEBUG=True)
class N8NClientTests(TestCase):
    @override_settings(DEBUG=False, N8N_SERVICE_SECRET='')
    def test_production_requires_outbound_service_authentication(self):
        with self.assertRaises(N8NConfigurationError):
            N8NClient().post_json('https://n8n.test/webhook', {})

    @override_settings(N8N_REQUEST_TIMEOUT=7, N8N_SERVICE_SECRET='outbound-secret')
    @patch('accounts.services.n8n_client.request.urlopen')
    def test_successful_json_request_uses_timeout_auth_and_idempotency(self, urlopen_mock):
        urlopen_mock.return_value = response_with(b'{"status":"accepted","execution_id":"e-1"}')

        result = N8NClient().post_json('https://n8n.test/webhook', {'value': 1}, idempotency_key='run-1')

        self.assertEqual(result['execution_id'], 'e-1')
        sent_request = urlopen_mock.call_args.args[0]
        self.assertEqual(urlopen_mock.call_args.kwargs['timeout'], 7)
        self.assertEqual(sent_request.get_header('X-n8n-service-secret'), 'outbound-secret')
        self.assertEqual(sent_request.get_header('Idempotency-key'), 'run-1')
        self.assertEqual(json.loads(sent_request.data), {'value': 1})

    @patch('accounts.services.n8n_client.request.urlopen')
    def test_connection_error_has_specific_exception(self, urlopen_mock):
        urlopen_mock.side_effect = error.URLError('offline')
        with self.assertRaises(N8NConnectionError):
            N8NClient().post_json('https://n8n.test/webhook', {})

    @patch('accounts.services.n8n_client.request.urlopen')
    def test_http_error_has_status_code(self, urlopen_mock):
        urlopen_mock.side_effect = error.HTTPError('https://n8n.test', 503, 'down', {}, None)
        with self.assertRaises(N8NHTTPError) as raised:
            N8NClient().post_json('https://n8n.test/webhook', {})
        self.assertEqual(raised.exception.status_code, 503)

    @patch('accounts.services.n8n_client.request.urlopen')
    def test_invalid_json_is_rejected(self, urlopen_mock):
        urlopen_mock.return_value = response_with(b'not-json')
        with self.assertRaises(N8NResponseError):
            N8NClient().post_json('https://n8n.test/webhook', {})


@override_settings(
    N8N_MISSION_GENERATION_URL='https://n8n.test/webhook/mission-generation',
    N8N_CALLBACK_SECRET='callback-secret',
    N8N_WORKFLOW_VERSION='v1-test',
)
class N8NGenerationApiTests(TestCase):
    def setUp(self):
        self.creator = get_user_model().objects.create_user(
            username='creator@example.com', email='creator@example.com', password='Test1234!',
        )
        Profile.objects.create(
            user=self.creator,
            role=Profile.ROLE_CONTENT_CREATOR,
            onboarding_completed=True,
        )

    def csrf_client(self):
        client = Client(enforce_csrf_checks=True, HTTP_ORIGIN='https://testserver')
        client.force_login(self.creator)
        client.get('/api/auth/user/', secure=True)
        return client, client.cookies['csrftoken'].value

    @patch('accounts.services.n8n_mission_generation.start_mission_generation')
    def test_weekly_endpoint_starts_real_week_contract(self, start_mock):
        start_mock.return_value = {'status': 'accepted', 'execution_id': 'n8n-123'}
        client, token = self.csrf_client()

        response = client.post(
            '/api/auth/missions/generate-next-week/',
            {},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
            secure=True,
        )

        self.assertEqual(response.status_code, 202)
        run = GenerationRun.objects.get()
        self.assertEqual(run.status, GenerationRun.STATUS_DISPATCHED)
        self.assertEqual(run.n8n_execution_id, 'n8n-123')
        outbound = start_mock.call_args.args[0]
        self.assertEqual(outbound['generation_run_id'], str(run.id))
        self.assertEqual(outbound['workflow_version'], 'v1-test')
        self.assertNotIn('requested_by', outbound)
        self.assertNotIn(self.creator.email, json.dumps(outbound))
        self.assertTrue(outbound['requirements'])
        self.assertTrue(all(item['generator_requests'] for item in outbound['requirements']))

    @patch('accounts.services.n8n_mission_generation.start_mission_generation')
    def test_generation_endpoint_requires_csrf(self, start_mock):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.creator)
        response = client.post(
            '/api/auth/missions/generate-next-week/', {}, content_type='application/json', secure=True,
        )
        self.assertEqual(response.status_code, 403)
        start_mock.assert_not_called()

    def test_current_weekly_generation_run_returns_only_requesters_active_run(self):
        completed = GenerationRun.objects.create(
            requested_by=self.creator,
            kind=GenerationRun.KIND_WEEKLY_MISSIONS,
            status=GenerationRun.STATUS_COMPLETED,
            week_start=timezone.localdate(),
        )
        active = GenerationRun.objects.create(
            requested_by=self.creator,
            kind=GenerationRun.KIND_WEEKLY_MISSIONS,
            status=GenerationRun.STATUS_REVIEWING,
            week_start=timezone.localdate() + timedelta(days=7),
        )
        other_creator = get_user_model().objects.create_user(
            username='other-creator@example.com', email='other-creator@example.com', password='Test1234!',
        )
        Profile.objects.create(
            user=other_creator,
            role=Profile.ROLE_CONTENT_CREATOR,
            onboarding_completed=True,
        )
        GenerationRun.objects.create(
            requested_by=other_creator,
            kind=GenerationRun.KIND_WEEKLY_MISSIONS,
            status=GenerationRun.STATUS_REPAIRING,
            week_start=timezone.localdate() + timedelta(days=14),
        )
        client = Client()
        client.force_login(self.creator)

        response = client.get('/api/auth/mission-generation-runs/current-weekly/', secure=True)

        self.assertEqual(response.status_code, 200)
        payload = response.json()['generation_run']
        self.assertEqual(payload['id'], str(active.id))
        self.assertEqual(payload['status'], GenerationRun.STATUS_REVIEWING)
        self.assertIn('updated_at', payload)
        self.assertNotEqual(payload['id'], str(completed.id))

        active.status = GenerationRun.STATUS_FAILED
        active.save(update_fields=['status', 'updated_at'])
        response = client.get('/api/auth/mission-generation-runs/current-weekly/', secure=True)
        self.assertIsNone(response.json()['generation_run'])

    def test_current_weekly_generation_run_requires_creator_permission(self):
        learner = get_user_model().objects.create_user(
            username='learner@example.com', email='learner@example.com', password='Test1234!',
        )
        Profile.objects.create(user=learner, role=Profile.ROLE_USER, onboarding_completed=True)
        client = Client()
        client.force_login(learner)

        response = client.get('/api/auth/mission-generation-runs/current-weekly/', secure=True)

        self.assertEqual(response.status_code, 403)

    @patch('accounts.services.n8n_mission_generation.start_mission_generation')
    def test_unreachable_n8n_marks_run_failed(self, start_mock):
        start_mock.side_effect = N8NConnectionError('offline')
        client, token = self.csrf_client()
        response = client.post(
            '/api/auth/missions/generate-next-week/',
            {},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
            secure=True,
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(GenerationRun.objects.get().status, GenerationRun.STATUS_FAILED)

    def raw_quiz_payload(self, scheduled_date, title='Generated title'):
        learning_de = 'Pruefe KI-Ausgaben anhand der Ausgangsdaten und dokumentiere Abweichungen, bevor du Ergebnisse in einem Finanzprozess weiterverwendest. Eine Stichprobe schafft zusaetzliche Sicherheit.'
        learning_en = 'Check AI output against the source data and document discrepancies before reusing results in a finance process. A documented spot-check adds another layer of assurance.'
        variants = {}
        for difficulty in Mission.DIFFICULTIES:
            variants[difficulty] = {
                'title_de': f'{title} {difficulty}',
                'title_en': f'{title} {difficulty}',
                'description_de': 'Eine praktische Frage zur Pruefung von KI-Ergebnissen.',
                'description_en': 'A practical question about checking AI output.',
                'points': 30,
                'content': {
                    'question_de': 'Was sollte vor der Weiterverwendung geprueft werden?',
                    'question_en': 'What should be checked before reusing the result?',
                    'options_de': ['Ausgangsdaten und Ergebnis', 'Nur das Layout'],
                    'options_en': ['Source data and result', 'Only the layout'],
                    'correct_option_indices': [0],
                    'feedback_de': 'Die Gegenpruefung mit den Ausgangsdaten deckt Abweichungen auf.',
                    'feedback_en': 'Comparing against source data reveals discrepancies.',
                    'micro_learning_de': learning_de,
                    'micro_learning_en': learning_en,
                },
            }
        return {'missions': [{
            'date': scheduled_date.isoformat(),
            'type': Mission.TYPE_SINGLE_CHOICE,
            'topic_de': 'KI-Ergebnisse pruefen',
            'topic_en': 'Checking AI output',
            'learning_objective_de': 'KI-Ergebnisse vor der Nutzung systematisch pruefen.',
            'learning_objective_en': 'Systematically check AI output before use.',
            'variants': variants,
        }]}

    def one_quiz_run(self):
        scheduled_date = timezone.localdate() + timedelta(days=2)
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_WEEKLY_MISSIONS,
            status=GenerationRun.STATUS_RUNNING,
            requested_by=self.creator,
            week_start=scheduled_date,
            week_end=scheduled_date,
            request_payload={'requirements': [{
                'id': 'quiz-1',
                'output_type': 'quiz_mission',
                'scheduled_date': scheduled_date.isoformat(),
                'requested_mission_type': None,
            }]},
        )
        return run, scheduled_date

    def callback(self, payload, secret='callback-secret'):
        return self.client.post(
            '/internal/n8n/generation-callback/',
            payload,
            content_type='application/json',
            HTTP_X_N8N_CALLBACK_SECRET=secret,
            secure=True,
        )

    def test_validation_endpoint_uses_existing_validator(self):
        run, scheduled_date = self.one_quiz_run()
        response = self.client.post(
            '/internal/n8n/validate-mission/',
            {
                'generation_run_id': str(run.id),
                'requirement_id': 'quiz-1',
                'result': {'payload': self.raw_quiz_payload(scheduled_date)},
            },
            content_type='application/json',
            HTTP_X_N8N_CALLBACK_SECRET='callback-secret',
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])

    def test_callback_requires_service_secret_and_passed_review(self):
        run, scheduled_date = self.one_quiz_run()
        body = {
            'generation_run_id': str(run.id),
            'status': 'completed',
            'results': [{'requirement_id': 'quiz-1', 'payload': self.raw_quiz_payload(scheduled_date)}],
            'review_report': {'verdict': 'pass'},
        }
        self.assertEqual(self.callback(body, secret='wrong').status_code, 401)
        body['review_report'] = {'verdict': 'revise'}
        self.assertEqual(self.callback(body).status_code, 422)
        self.assertEqual(Mission.objects.count(), 0)

    def test_final_callback_revalidates_saves_review_mission_and_is_idempotent(self):
        run, scheduled_date = self.one_quiz_run()
        body = {
            'generation_run_id': str(run.id),
            'status': 'completed',
            'n8n_execution_id': 'exec-final',
            'results': [{'requirement_id': 'quiz-1', 'payload': self.raw_quiz_payload(scheduled_date)}],
            'review_report': {'verdict': 'pass', 'score': 0.94, 'issues': []},
            'research_context': [],
        }
        with CaptureQueriesContext(connection) as captured_queries:
            first = self.callback(body)
        second = self.callback(body)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        generation_run_queries = [
            query['sql'] for query in captured_queries.captured_queries
            if 'accounts_generationrun' in query['sql']
        ]
        self.assertFalse(any(
            'LEFT OUTER JOIN' in query and 'accounts_mission' in query
            for query in generation_run_queries
        ))
        self.assertEqual(Mission.objects.count(), 1)
        mission = Mission.objects.get()
        self.assertEqual(mission.status, Mission.STATUS_REVIEW)
        self.assertTrue(mission.generated_by_ai)
        self.assertEqual(mission.generation_run_id, run.id)
        run.refresh_from_db()
        self.assertEqual(run.status, GenerationRun.STATUS_COMPLETED)
        self.assertEqual(run.review_report['score'], 0.94)

    def test_weekly_callback_saves_successes_and_records_failed_requirements(self):
        first_date = timezone.localdate() + timedelta(days=7)
        second_date = first_date + timedelta(days=1)
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_WEEKLY_MISSIONS,
            status=GenerationRun.STATUS_REVIEWING,
            requested_by=self.creator,
            week_start=first_date,
            week_end=second_date,
            request_payload={'requirements': [
                {
                    'id': 'quiz-success',
                    'output_type': 'quiz_mission',
                    'scheduled_date': first_date.isoformat(),
                    'requested_mission_type': None,
                },
                {
                    'id': 'quiz-failed',
                    'output_type': 'quiz_mission',
                    'scheduled_date': second_date.isoformat(),
                    'requested_mission_type': None,
                },
            ]},
        )

        response = self.callback({
            'generation_run_id': str(run.id),
            'status': 'completed',
            'results': [{
                'requirement_id': 'quiz-success',
                'payload': self.raw_quiz_payload(first_date),
            }],
            'failed_requirements': [{
                'requirement_id': 'quiz-failed',
                'error_message': 'Reviewer rejected the mission after repairs',
                'repair_attempts': 2,
            }],
            'review_report': {'verdict': 'pass', 'score': 0.93, 'issues': []},
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Mission.objects.count(), 1)
        self.assertEqual(Mission.objects.get().scheduled_date, first_date)
        payload = response.json()['generation_run']
        self.assertEqual(payload['status'], GenerationRun.STATUS_COMPLETED)
        self.assertEqual(payload['created_count'], 1)
        self.assertEqual(payload['failed_count'], 1)
        self.assertTrue(payload['partial_success'])
        self.assertEqual(payload['failed_requirements'][0]['requirement_id'], 'quiz-failed')
        self.assertEqual(payload['failed_requirements'][0]['scheduled_date'], second_date.isoformat())
        self.assertEqual(payload['failed_requirements'][0]['output_type'], 'quiz_mission')
        self.assertIsNone(payload['failed_requirements'][0]['mission_type'])
        self.assertEqual(payload['failed_requirements'][0]['error_message'], 'Reviewer rejected the mission after repairs')
        run.refresh_from_db()
        self.assertEqual(run.result_metadata['failed_requirements'][0]['repair_attempts'], 2)

    def test_weekly_callback_does_not_complete_when_every_requirement_failed(self):
        run, _ = self.one_quiz_run()
        response = self.callback({
            'generation_run_id': str(run.id),
            'status': 'completed',
            'results': [],
            'failed_requirements': [{
                'requirement_id': 'quiz-1',
                'error_message': 'No acceptable mission generated',
                'repair_attempts': 2,
            }],
            'review_report': {'verdict': 'pass', 'issues': []},
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(Mission.objects.count(), 0)
        run.refresh_from_db()
        self.assertNotEqual(run.status, GenerationRun.STATUS_COMPLETED)

    def test_regeneration_callback_updates_existing_review_mission(self):
        scheduled_date = timezone.localdate() + timedelta(days=3)
        mission = Mission.objects.create(
            mission_type=Mission.TYPE_SINGLE_CHOICE,
            scheduled_date=scheduled_date,
            title_de='Alt',
            title_en='Old',
            content={},
            max_points=30,
            status=Mission.STATUS_REVIEW,
            generated_by_ai=True,
            created_by=self.creator,
        )
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_REGENERATE_MISSION,
            status=GenerationRun.STATUS_REVIEWING,
            requested_by=self.creator,
            target_mission=mission,
            request_payload={'requirements': [{
                'id': 'replacement',
                'output_type': 'quiz_mission',
                'scheduled_date': scheduled_date.isoformat(),
                'requested_mission_type': None,
            }]},
        )
        response = self.callback({
            'generation_run_id': str(run.id),
            'status': 'completed',
            'results': [{
                'requirement_id': 'replacement',
                'payload': self.raw_quiz_payload(scheduled_date, title='Neu'),
            }],
            'review_report': {'verdict': 'pass', 'issues': []},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Mission.objects.count(), 1)
        mission.refresh_from_db()
        self.assertTrue(mission.title_de.startswith('Neu'))
        self.assertEqual(mission.generation_run_id, run.id)

    def test_training_result_is_private_until_owner_consumes_it(self):
        scheduled_date = timezone.localdate()
        run = GenerationRun.objects.create(
            kind=GenerationRun.KIND_TRAINING_CHOICE,
            status=GenerationRun.STATUS_REVIEWING,
            requested_by=self.creator,
            request_payload={'requirements': [{
                'id': 'training-choice',
                'output_type': 'quiz_mission',
                'scheduled_date': scheduled_date.isoformat(),
                'requested_mission_type': Mission.TYPE_SINGLE_CHOICE,
            }]},
        )
        completed = self.callback({
            'generation_run_id': str(run.id),
            'status': 'completed',
            'results': [{
                'requirement_id': 'training-choice',
                'payload': self.raw_quiz_payload(scheduled_date),
            }],
            'review_report': {'verdict': 'pass', 'issues': []},
        })
        self.assertEqual(completed.status_code, 200)
        detail = self.client.get(f'/api/auth/mission-generation-runs/{run.id}/', secure=True)
        self.assertEqual(detail.status_code, 403)

        self.client.force_login(self.creator)
        detail = self.client.get(f'/api/auth/mission-generation-runs/{run.id}/', secure=True)
        self.assertNotIn('result_payload', detail.json()['generation_run'])
        consumed = self.client.post(
            f'/api/auth/mission-generation-runs/{run.id}/consume/', {}, content_type='application/json', secure=True,
        )
        self.assertEqual(consumed.status_code, 200)
        self.assertEqual(consumed.json()['mission']['type'], Mission.TYPE_SINGLE_CHOICE)
        self.assertEqual(Mission.objects.count(), 0)
