from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import Mission, Profile
from accounts.services.generation_planning import next_calendar_week, plan_next_week


class SeedPlaceholderMissionsTests(TestCase):
    def setUp(self):
        self.creator = get_user_model().objects.create_user(
            username='creator@example.com',
            email='creator@example.com',
            password='Test1234!',
        )
        Profile.objects.create(
            user=self.creator,
            role=Profile.ROLE_CONTENT_CREATOR,
            onboarding_completed=True,
        )

    def test_seed_leaves_only_friday_open_for_weekly_generation(self):
        output = StringIO()
        week_start, _week_end = next_calendar_week()

        call_command(
            'seed_placeholder_missions',
            start_date=week_start,
            end_date=week_start + timedelta(days=3),
            stdout=output,
        )

        placeholders = Mission.objects.order_by('scheduled_date')
        self.assertEqual(placeholders.count(), 4)
        self.assertTrue(all(mission.status == Mission.STATUS_REVIEW for mission in placeholders))
        self.assertTrue(all(not mission.generated_by_ai for mission in placeholders))
        self.assertTrue(all(mission.has_difficulty_variants for mission in placeholders))
        _start, _end, task_days, quiz_days = plan_next_week(week_start=week_start)
        self.assertEqual(task_days | set(quiz_days), {week_start + timedelta(days=4)})
        self.assertIn('Created 4 placeholder mission(s)', output.getvalue())

    def test_seed_skips_an_occupied_day(self):
        week_start, _week_end = next_calendar_week()
        Mission.objects.create(
            mission_type=Mission.TYPE_SINGLE_CHOICE,
            scheduled_date=week_start + timedelta(days=1),
            title_de='Vorhanden',
            title_en='Existing',
            created_by=self.creator,
            status=Mission.STATUS_PUBLISHED,
        )

        call_command(
            'seed_placeholder_missions',
            start_date=week_start,
            end_date=week_start + timedelta(days=3),
        )

        self.assertEqual(Mission.objects.count(), 4)
        self.assertEqual(Mission.objects.filter(scheduled_date=week_start + timedelta(days=1)).count(), 1)
