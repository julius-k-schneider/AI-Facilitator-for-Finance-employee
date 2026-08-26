from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import GenerationRun, Profile
from accounts.services.n8n_client import N8NClientError
from accounts.services.n8n_mission_generation import create_weekly_run, dispatch_generation_run


class Command(BaseCommand):
    help = 'Generates AI mission proposals for the next calendar week and stores them for review.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Replace AI review missions, never published ones.')
        parser.add_argument('--creator', help='Username or email recorded as the creator.')

    def handle(self, *args, **options):
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

        run = create_weekly_run(creator, force=options['force'])
        try:
            if run.status in {GenerationRun.STATUS_QUEUED, GenerationRun.STATUS_FAILED}:
                dispatch_generation_run(run)
        except N8NClientError as error_value:
            raise CommandError(str(error_value)) from error_value
        self.stdout.write(self.style.SUCCESS(
            f'Started n8n generation run {run.id} for {run.week_start.isoformat()} to {run.week_end.isoformat()}.'
        ))
