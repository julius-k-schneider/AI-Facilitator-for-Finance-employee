import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def copy_attempt_max_points(apps, schema_editor):
    MissionAttempt = apps.get_model('accounts', 'MissionAttempt')
    for attempt in MissionAttempt.objects.select_related('mission').iterator():
        attempt.max_points = attempt.mission.max_points
        attempt.save(update_fields=['max_points'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_mission_task_challenge_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='skill_level',
            field=models.CharField(
                choices=[('beginner', 'Beginner'), ('advanced', 'Advanced'), ('pro', 'Pro')],
                default='beginner',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='profile',
            name='skill_level_entered_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='mission',
            name='topic_de',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='mission',
            name='topic_en',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='mission',
            name='learning_objective_de',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='mission',
            name='learning_objective_en',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='mission',
            name='variants',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='missionattempt',
            name='difficulty',
            field=models.CharField(
                blank=True,
                choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
                db_index=True,
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='missionattempt',
            name='max_points',
            field=models.PositiveIntegerField(default=100),
        ),
        migrations.RunPython(copy_attempt_max_points, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='weeklyleaderboardsnapshot',
            name='week_start',
            field=models.DateField(),
        ),
        migrations.AddField(
            model_name='weeklyleaderboardsnapshot',
            name='difficulty',
            field=models.CharField(
                blank=True,
                choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
                default='',
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name='weeklyleaderboardsnapshot',
            constraint=models.UniqueConstraint(
                fields=('week_start', 'difficulty'),
                name='unique_weekly_leaderboard_difficulty',
            ),
        ),
        migrations.CreateModel(
            name='MissionAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('difficulty', models.CharField(
                    choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
                    max_length=16,
                )),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('mission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments',
                    to='accounts.mission',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mission_assignments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ('assigned_at',)},
        ),
        migrations.AddConstraint(
            model_name='missionassignment',
            constraint=models.UniqueConstraint(
                fields=('user', 'mission'),
                name='unique_user_mission_assignment',
            ),
        ),
        migrations.CreateModel(
            name='SkillProgressionSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('automatic_progression_enabled', models.BooleanField(default=True)),
                ('evaluation_window', models.PositiveIntegerField(
                    default=10,
                    validators=[django.core.validators.MinValueValidator(1)],
                )),
                ('minimum_missions', models.PositiveIntegerField(
                    default=10,
                    validators=[django.core.validators.MinValueValidator(1)],
                )),
                ('promotion_threshold', models.PositiveSmallIntegerField(
                    default=80,
                    validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                )),
                ('demotion_threshold', models.PositiveSmallIntegerField(
                    default=50,
                    validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'skill progression settings',
                'verbose_name_plural': 'skill progression settings',
            },
        ),
    ]
