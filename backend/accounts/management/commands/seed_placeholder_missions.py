from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Mission, Profile
from accounts.services.generation_planning import next_calendar_week


def placeholder_variant(scheduled_date, difficulty, points):
    date_label = scheduled_date.strftime('%d.%m.%Y')
    return {
        'title_de': f'Platzhalter-Mission {date_label} ({difficulty})',
        'title_en': f'Placeholder mission {scheduled_date.isoformat()} ({difficulty})',
        'description_de': 'Temporärer Platzhalter zum Testen der Wochengenerierung.',
        'description_en': 'Temporary placeholder for testing weekly generation.',
        'content': {
            'question': {
                'de': 'Welche Antwort markiert diese Testmission als funktionsfähig?',
                'en': 'Which answer marks this test mission as working?',
            },
            'options': [
                {'de': 'Platzhalter aktiv', 'en': 'Placeholder active'},
                {'de': 'Platzhalter inaktiv', 'en': 'Placeholder inactive'},
            ],
            'correct_indices': [0],
            'feedback': {
                'de': 'Der Platzhalter ist aktiv und blockiert diesen Tag für die Wochengenerierung.',
                'en': 'The placeholder is active and blocks this day for weekly generation.',
            },
            'micro_learning': {
                'de': 'Diese Mission enthält bewusst nur Testdaten. Sie reserviert den Kalendertag, damit die '
                      'Wochengenerierung bereits belegte Tage überspringt und nur die noch offenen Tage erzeugt.',
                'en': 'This mission deliberately contains test data only. It reserves the calendar day so weekly '
                      'generation skips occupied days and creates missions only for the remaining open days.',
            },
        },
        'max_points': points,
    }


class Command(BaseCommand):
    help = 'Creates review placeholders so weekly generation skips the selected weekdays.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=date.fromisoformat,
            help='First date in YYYY-MM-DD format (defaults to next Monday).',
        )
        parser.add_argument(
            '--end-date',
            type=date.fromisoformat,
            help='Last date in YYYY-MM-DD format (defaults to Thursday of the selected week).',
        )
        parser.add_argument('--creator', help='Username or email recorded as the creator.')

    def handle(self, *args, **options):
        start_date = options['start_date'] or next_calendar_week()[0]
        end_date = options['end_date'] or start_date + timedelta(days=3)
        if end_date < start_date:
            raise CommandError('end-date must be on or after start-date')
        if start_date < timezone.localdate():
            raise CommandError('start-date must be today or later')

        dates = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                dates.append(current_date)
            current_date += timedelta(days=1)
        if not dates:
            raise CommandError('The selected range does not contain a weekday.')

        users = get_user_model().objects.filter(
            profile__role__in=[Profile.ROLE_CONTENT_CREATOR, Profile.ROLE_ADMIN]
        )
        if options['creator']:
            creator = users.filter(username=options['creator']).first() or users.filter(
                email=options['creator']
            ).first()
        else:
            creator = users.order_by('id').first()
        if creator is None:
            raise CommandError('No matching content creator or admin exists.')

        created = []
        skipped = []
        with transaction.atomic():
            occupied_dates = set(Mission.objects.select_for_update().filter(
                scheduled_date__in=dates,
                status__in=[Mission.STATUS_REVIEW, Mission.STATUS_PUBLISHED],
            ).values_list('scheduled_date', flat=True))
            for scheduled_date in dates:
                if scheduled_date in occupied_dates:
                    skipped.append(scheduled_date)
                    continue
                variants = {
                    difficulty: placeholder_variant(scheduled_date, difficulty, 20 + position * 10)
                    for position, difficulty in enumerate(Mission.DIFFICULTIES)
                }
                easy = variants[Mission.DIFFICULTY_EASY]
                created.append(Mission.objects.create(
                    mission_type=Mission.TYPE_SINGLE_CHOICE,
                    scheduled_date=scheduled_date,
                    title_de=easy['title_de'],
                    title_en=easy['title_en'],
                    description_de=easy['description_de'],
                    description_en=easy['description_en'],
                    content=easy['content'],
                    max_points=easy['max_points'],
                    topic_de='Test der Wochengenerierung',
                    topic_en='Weekly generation test',
                    learning_objective_de='Bereits belegte Tage bei der Generierung überspringen.',
                    learning_objective_en='Skip occupied days during generation.',
                    variants=variants,
                    status=Mission.STATUS_REVIEW,
                    generated_by_ai=False,
                    created_by=creator,
                ))

        created_dates = ', '.join(mission.scheduled_date.isoformat() for mission in created) or 'none'
        skipped_dates = ', '.join(value.isoformat() for value in skipped) or 'none'
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(created)} placeholder mission(s): {created_dates}. '
            f'Skipped {len(skipped)} occupied date(s): {skipped_dates}.'
        ))
