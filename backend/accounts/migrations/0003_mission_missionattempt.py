from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_reconcile_legacy_profile_schema'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mission_type', models.CharField(choices=[('single_choice', 'Single Choice')], max_length=32)),
                ('scheduled_date', models.DateField(db_index=True)),
                ('title_de', models.CharField(max_length=160)),
                ('title_en', models.CharField(max_length=160)),
                ('description_de', models.TextField(blank=True)),
                ('description_en', models.TextField(blank=True)),
                ('content', models.JSONField(default=dict)),
                ('max_points', models.PositiveIntegerField(default=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_missions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('scheduled_date', 'created_at', 'id')},
        ),
        migrations.CreateModel(
            name='MissionAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.JSONField(default=dict)),
                ('score', models.PositiveIntegerField(default=0)),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='accounts.mission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mission_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-completed_at',)},
        ),
        migrations.AddConstraint(
            model_name='missionattempt',
            constraint=models.UniqueConstraint(fields=('user', 'mission'), name='unique_user_mission_attempt'),
        ),
    ]
