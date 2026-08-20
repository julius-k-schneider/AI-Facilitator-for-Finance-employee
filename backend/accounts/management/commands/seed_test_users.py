from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from accounts.models import Mission, Profile, WeeklyLeaderboardSnapshot


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

        creator = User.objects.get(username=SEED_USERS[0][0])
        today = timezone.localdate()
        missions = [
                {
                    'title_de': 'Sicherer Einsatz von AI',
                    'title_en': 'Safe use of AI',
                    'description_de': 'Prüfe, welche Daten in ein AI-Tool eingegeben werden dürfen.',
                    'description_en': 'Check which data may be entered into an AI tool.',
                    'question': {
                        'de': 'Welche Daten dürfen in einem öffentlichen AI-Tool verwendet werden?',
                        'en': 'Which data may be used in a public AI tool?',
                    },
                    'options': [
                        {'de': 'Anonymisierte, nicht vertrauliche Daten', 'en': 'Anonymized, non-confidential data'},
                        {'de': 'Personenbezogene Gehaltsdaten', 'en': 'Personal salary data'},
                        {'de': 'Vertrauliche Monatsberichte', 'en': 'Confidential monthly reports'},
                    ],
                    'correct_index': 0,
                    'max_points': 100,
                },
                {
                    'title_de': 'Präzise Finance-Prompts',
                    'title_en': 'Precise finance prompts',
                    'description_de': 'Erkenne den Prompt mit dem klarsten Arbeitsauftrag.',
                    'description_en': 'Identify the prompt with the clearest task.',
                    'question': {
                        'de': 'Welcher Prompt ist für eine Abweichungsanalyse am besten geeignet?',
                        'en': 'Which prompt is best suited for a variance analysis?',
                    },
                    'options': [
                        {'de': 'Analysiere die Zahlen.', 'en': 'Analyze the numbers.'},
                        {'de': 'Vergleiche Ist und Plan, nenne die fünf größten Abweichungen und mögliche Ursachen.', 'en': 'Compare actuals and plan, list the five largest variances and possible causes.'},
                        {'de': 'Was ist hier wichtig?', 'en': 'What is important here?'},
                    ],
                    'correct_index': 1,
                    'max_points': 100,
                },
        ]
        for item in missions:
            mission = Mission.objects.filter(
                scheduled_date=today,
                created_by=creator,
                title_en=item['title_en'],
            ).first()
            if mission is None and Mission.objects.filter(scheduled_date=today).exists():
                continue
            if mission is None:
                mission = Mission(scheduled_date=today, created_by=creator)
            mission.mission_type = Mission.TYPE_SINGLE_CHOICE
            mission.title_de = item['title_de']
            mission.title_en = item['title_en']
            mission.description_de = item['description_de']
            mission.description_en = item['description_en']
            mission.content = {
                'question': item['question'],
                'options': item['options'],
                'correct_index': item['correct_index'],
            }
            mission.max_points = item['max_points']
            mission.save()
        self.stdout.write(self.style.SUCCESS('Upserted one bilingual mission for today'))

        current_week_start = today - timedelta(days=today.weekday())
        users = list(User.objects.filter(username__in=[item[0] for item in SEED_USERS]))
        users_by_email = {user.username: user for user in users}
        for weeks_ago in (1, 2):
            week_start = current_week_start - timedelta(weeks=weeks_ago)
            entries = []
            for index, (email, first_name, last_name, _, _) in enumerate(SEED_USERS):
                user = users_by_email[email]
                points = max(20, 150 - index * 17 + weeks_ago * 6)
                completed = max(1, 8 - index)
                entries.append({
                    'user_id': user.id,
                    'name': f'{first_name} {last_name}',
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'total_points': points,
                    'completed_missions': completed,
                    'level': 'Advanced' if points >= 180 else 'Practitioner' if points >= 90 else 'Starter',
                })
            entries.sort(key=lambda entry: (-entry['total_points'], -entry['completed_missions'], entry['name']))
            for rank, entry in enumerate(entries, start=1):
                entry['rank'] = rank
            WeeklyLeaderboardSnapshot.objects.update_or_create(
                week_start=week_start,
                difficulty=Mission.DIFFICULTY_EASY,
                defaults={'week_end': week_start + timedelta(days=6), 'entries': entries},
            )
        self.stdout.write(self.style.SUCCESS('Upserted leaderboard snapshots for the previous two weeks'))
