import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

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
