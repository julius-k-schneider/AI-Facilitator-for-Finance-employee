from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.services.email_notifications import send_daily_mission_reminders


class Command(BaseCommand):
    help = 'Sends Friday email reminders to users who have not completed all missions for the current week.'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='Reminder date in YYYY-MM-DD format. Defaults to today.')
        parser.add_argument('--dry-run', action='store_true', help='Show counts without sending email or writing reminder rows.')

    def handle(self, *args, **options):
        reminder_date = timezone.localdate()
        if options['date']:
            try:
                reminder_date = date.fromisoformat(options['date'])
            except ValueError as error:
                raise CommandError('--date must be in YYYY-MM-DD format') from error

        result = send_daily_mission_reminders(reminder_date=reminder_date, dry_run=options['dry_run'])
        self.stdout.write(self.style.SUCCESS(
            'Weekly mission reminders for {date}: status={status}, missions={mission_count}, incomplete={incomplete_count}, '
            'sent={sent}, skipped={skipped}, failed={failed}, dry_run={dry_run}'.format(**{
                **result,
                'date': result['date'].isoformat(),
            })
        ))
