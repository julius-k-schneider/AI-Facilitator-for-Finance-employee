from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('controller', 'Controller'), ('accountant', 'Accountant'), ('content_creator', 'Content Creator'), ('admin', 'Admin')], default='accountant', max_length=32)),
                ('onboarding_completed', models.BooleanField(default=False)),
                ('onboarding_completed_at', models.DateTimeField(blank=True, null=True)),
                ('onboarding_progress', models.JSONField(blank=True, default=list)),
                ('mission_scores', models.JSONField(blank=True, default=dict)),
                ('progress_updated_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
