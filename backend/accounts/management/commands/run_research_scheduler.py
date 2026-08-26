import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from accounts.services.research import dispatch_due_research


class Command(BaseCommand):
    help = 'Wait for the configured weekly research time and dispatch n8n only when due.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Check once and exit.')

    def handle(self, *args, **options):
        poll_seconds = max(10, settings.RESEARCH_SCHEDULER_POLL_SECONDS)
        self.stdout.write(
            f'Research scheduler started (database check every {poll_seconds}s; n8n is called only when due).',
        )
        while True:
            close_old_connections()
            try:
                run = dispatch_due_research()
                if run is not None:
                    self.stdout.write(f'Research run {run.id}: {run.status}')
            except Exception as exception:  # Keep the scheduler alive after transient database/startup failures.
                self.stderr.write(f'Research schedule check failed: {exception}')
            finally:
                close_old_connections()
            if options['once']:
                return
            time.sleep(poll_seconds)
