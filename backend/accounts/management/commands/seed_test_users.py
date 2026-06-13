from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile


SEED_USERS = [
    ('anna.becker@example.com', 'Anna', 'Becker', 90, 110),
    ('ben.fischer@example.com', 'Ben', 'Fischer', 80, 95),
    ('clara.hoffmann@example.com', 'Clara', 'Hoffmann', 70, 85),
    ('david.klein@example.com', 'David', 'Klein', 60, 70),
    ('elena.wagner@example.com', 'Elena', 'Wagner', 50, 60),
    ('felix.schulz@example.com', 'Felix', 'Schulz', 40, 45),
]


class Command(BaseCommand):
    help = 'Creates idempotent database-backed users for local leaderboard testing.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='Test1234!')

    def handle(self, *args, **options):
        User = get_user_model()
        for index, (email, first_name, last_name, prompt_score, compliance_score) in enumerate(SEED_USERS):
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                },
            )
            if created:
                user.set_password(options['password'])
                user.save(update_fields=['password'])

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.ROLE_ADMIN if index == 0 else Profile.ROLE_ACCOUNTANT
            profile.onboarding_completed = True
            profile.onboarding_completed_at = profile.onboarding_completed_at or timezone.now()
            profile.mission_scores = {
                'prompt-quality-quiz': prompt_score,
                'compliance-check-challenge': compliance_score,
            }
            profile.progress_updated_at = timezone.now()
            profile.save()
            self.stdout.write(self.style.SUCCESS(f'Upserted {email}'))
