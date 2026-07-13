import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import DailyMissionReminder, Mission, MissionAttempt

logger = logging.getLogger(__name__)


def mission_email_recipients():
    User = get_user_model()
    return list(
        User.objects.filter(is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )


def send_published_mission_email(mission):
    recipients = mission_email_recipients()
    if not recipients:
        return 0

    subject = f'Neue Mission verfügbar / New mission available: {mission.title_de}'
    message = (
        'Hallo,\n\n'
        'eine neue Mission wurde veröffentlicht:\n\n'
        f'{mission.title_de}\n'
        f'{mission.description_de}\n\n'
        f'Datum: {mission.scheduled_date.isoformat()}\n\n'
        'Viel Erfolg!\n\n'
        '----------\n\n'
        'Hello,\n\n'
        'a new mission has been published:\n\n'
        f'{mission.title_en}\n'
        f'{mission.description_en}\n\n'
        f'Date: {mission.scheduled_date.isoformat()}\n\n'
        'Good luck!'
    )

    try:
        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send published mission reminder for mission %s', mission.id)
        return 0


def send_published_mission_emails(missions):
    return sum(send_published_mission_email(mission) for mission in missions)


def current_week_range(reminder_date):
    week_start = reminder_date - timedelta(days=reminder_date.weekday())
    return week_start, reminder_date


def incomplete_weekly_mission_users(reminder_date=None):
    reminder_date = reminder_date or timezone.localdate()
    week_start, week_end = current_week_range(reminder_date)
    missions = list(Mission.objects.filter(
        scheduled_date__range=(week_start, week_end),
        status=Mission.STATUS_PUBLISHED,
    ).order_by('scheduled_date', 'id'))
    if not missions:
        return [], missions

    mission_ids = [mission.id for mission in missions]
    User = get_user_model()
    users = User.objects.filter(is_active=True).exclude(email='').order_by('id')
    completed_pairs = set(MissionAttempt.objects.filter(
        mission_id__in=mission_ids,
        user__in=users,
    ).values_list('user_id', 'mission_id'))

    incomplete = []
    for user in users:
        missing_missions = [
            mission for mission in missions
            if (user.id, mission.id) not in completed_pairs
        ]
        if missing_missions:
            incomplete.append((user, missing_missions))
    return incomplete, missions


def incomplete_daily_mission_users(reminder_date=None):
    return incomplete_weekly_mission_users(reminder_date)


def send_daily_mission_reminder(user, reminder_date, missions, missing_missions):
    subject = 'Reminder: Offene Missionen der Woche / Open missions for this week'
    week_start, week_end = current_week_range(reminder_date)
    mission_lines_de = '\n'.join(
        f'- {mission.scheduled_date.isoformat()}: {mission.title_de}'
        for mission in missing_missions
    )
    mission_lines_en = '\n'.join(
        f'- {mission.scheduled_date.isoformat()}: {mission.title_en}'
        for mission in missing_missions
    )
    message = (
        f'Hallo {user.first_name or user.username},\n\n'
        'du hast diese Woche noch nicht alle Missionen abgeschlossen.\n\n'
        f'Offene Missionen: {len(missing_missions)} von {len(missions)}\n'
        f'Zeitraum: {week_start.isoformat()} bis {week_end.isoformat()}\n\n'
        f'Noch offene Missionen:\n{mission_lines_de}\n\n'
        'Schau kurz in die App und erledige sie, wenn du Zeit hast.\n\n'
        'Viele Grüße\n'
        'AI Facilitator\n\n'
        '----------\n\n'
        f'Hello {user.first_name or user.username},\n\n'
        'you have not completed all missions for this week yet.\n\n'
        f'Open missions: {len(missing_missions)} of {len(missions)}\n'
        f'Period: {week_start.isoformat()} to {week_end.isoformat()}\n\n'
        f'Still open missions:\n{mission_lines_en}\n\n'
        'Take a quick look at the app and complete them when you have time.\n\n'
        'Best regards\n'
        'AI Facilitator'
    )
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_daily_mission_reminders(reminder_date=None, dry_run=False):
    reminder_date = reminder_date or timezone.localdate()
    if reminder_date.weekday() != 4:
        return {
            'date': reminder_date,
            'mission_count': 0,
            'incomplete_count': 0,
            'sent': 0,
            'skipped': 0,
            'failed': 0,
            'dry_run': dry_run,
            'status': 'skipped_non_friday',
        }

    incomplete_users, missions = incomplete_weekly_mission_users(reminder_date)
    sent = 0
    skipped = 0
    failed = 0

    for user, missing_missions in incomplete_users:
        if DailyMissionReminder.objects.filter(user=user, reminder_date=reminder_date).exists():
            skipped += 1
            continue
        if dry_run:
            sent += 1
            continue
        try:
            send_daily_mission_reminder(user, reminder_date, missions, missing_missions)
            DailyMissionReminder.objects.create(
                user=user,
                reminder_date=reminder_date,
                mission_count=len(missions),
                missing_count=len(missing_missions),
            )
            sent += 1
        except IntegrityError:
            skipped += 1
        except Exception:
            failed += 1
            logger.exception('Failed to send daily mission reminder to user %s for %s', user.id, reminder_date)

    return {
        'date': reminder_date,
        'mission_count': len(missions),
        'incomplete_count': len(incomplete_users),
        'sent': sent,
        'skipped': skipped,
        'failed': failed,
        'dry_run': dry_run,
        'status': 'sent',
    }
