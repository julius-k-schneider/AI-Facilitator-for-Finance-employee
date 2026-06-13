from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Erweitert den Standard-User um anwendungsspezifische Felder."""

    ROLE_CONTROLLER = 'controller'
    ROLE_ACCOUNTANT = 'accountant'
    # Vorerst sind nur diese beiden Rollen vorgesehen.
    ROLE_CHOICES = [
        (ROLE_CONTROLLER, 'Controller'),
        (ROLE_ACCOUNTANT, 'Accountant'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ACCOUNTANT,
    )

    # Onboarding muss abgeschlossen sein, bevor die Daily Challenges
    # freigeschaltet werden. Der Content ist im Frontend hardcoded; hier wird
    # nur der Zustand persistiert.
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    # Liste bereits abgeschlossener Kapitel-IDs (für Wiederaufnahme des Flows).
    onboarding_progress = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'
