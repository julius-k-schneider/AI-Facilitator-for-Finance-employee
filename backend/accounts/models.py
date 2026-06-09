from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_USER = 'user'
    ROLE_CONTENT_CREATOR = 'content_creator'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_CONTENT_CREATOR, 'Content Creator'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_USER)

    def __str__(self):
        return f'{self.user.username} ({self.role})'
