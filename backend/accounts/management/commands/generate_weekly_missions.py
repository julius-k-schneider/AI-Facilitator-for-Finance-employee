from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Profile
from accounts.services.ai_mission_generator import AiMissionGenerationError, generate_next_week


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

        try:
            missions, week_start, week_end = generate_next_week(creator, force=options['force'])
        except AiMissionGenerationError as error_value:
            raise CommandError(str(error_value)) from error_value
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(missions)} review missions for {week_start.isoformat()} to {week_end.isoformat()}.'
        ))
