import logging

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

    subject = f'Neue Mission verfuegbar: {mission.title_de}'
    message = (
        'Hallo,\n\n'
        'eine neue Mission wurde veroeffentlicht:\n\n'
        f'{mission.title_de}\n'
        f'{mission.description_de}\n\n'
        f'Datum: {mission.scheduled_date.isoformat()}\n\n'
        'Viel Erfolg!'
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


def incomplete_daily_mission_users(reminder_date=None):
    reminder_date = reminder_date or timezone.localdate()
    missions = list(Mission.objects.filter(
        scheduled_date=reminder_date,
        status=Mission.STATUS_PUBLISHED,
    ).order_by('id'))
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
        completed_count = sum((user.id, mission_id) in completed_pairs for mission_id in mission_ids)
        missing_count = len(mission_ids) - completed_count
        if missing_count > 0:
            incomplete.append((user, missing_count))
    return incomplete, missions


def send_daily_mission_reminder(user, reminder_date, missions, missing_count):
    subject = 'Reminder: Deine Daily Missions warten noch'
    mission_lines = '\n'.join(f'- {mission.title_de}' for mission in missions)
    message = (
        f'Hallo {user.first_name or user.username},\n\n'
        'du hast deine heutigen Daily Missions noch nicht vollstaendig abgeschlossen.\n\n'
        f'Offene Missionen: {missing_count} von {len(missions)}\n'
        f'Datum: {reminder_date.isoformat()}\n\n'
        f'Heutige Missionen:\n{mission_lines}\n\n'
        'Schau kurz in die App und erledige sie, wenn du Zeit hast.\n\n'
        'Viele Gruesse\n'
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
    incomplete_users, missions = incomplete_daily_mission_users(reminder_date)
    sent = 0
    skipped = 0
    failed = 0

    for user, missing_count in incomplete_users:
        if DailyMissionReminder.objects.filter(user=user, reminder_date=reminder_date).exists():
            skipped += 1
            continue
        if dry_run:
            sent += 1
            continue
        try:
            send_daily_mission_reminder(user, reminder_date, missions, missing_count)
            DailyMissionReminder.objects.create(
                user=user,
                reminder_date=reminder_date,
                mission_count=len(missions),
                missing_count=missing_count,
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
    }
