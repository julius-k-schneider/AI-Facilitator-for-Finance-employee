import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_relax_legacy_mission_columns'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GenerationRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[
                    ('weekly_missions', 'Weekly missions'),
                    ('regenerate_mission', 'Regenerate mission'),
                    ('scheduled_task', 'Scheduled task mission'),
                    ('training_choice', 'Training choice mission'),
                    ('training_task', 'Training task challenge'),
                    ('training_chat', 'Training chat challenge'),
                ], max_length=32)),
                ('status', models.CharField(choices=[
                    ('queued', 'Queued'),
                    ('dispatched', 'Dispatched'),
                    ('running', 'Running'),
                    ('validating', 'Validating'),
                    ('reviewing', 'Reviewing'),
                    ('repairing', 'Repairing'),
                    ('completed', 'Completed'),
                    ('failed', 'Failed'),
                ], db_index=True, default='queued', max_length=16)),
                ('week_start', models.DateField(blank=True, db_index=True, null=True)),
                ('week_end', models.DateField(blank=True, null=True)),
                ('force', models.BooleanField(default=False)),
                ('workflow_version', models.CharField(default='v1', max_length=32)),
                ('request_payload', models.JSONField(default=dict)),
                ('result_payload', models.JSONField(blank=True, default=dict)),
                ('research_context', models.JSONField(blank=True, default=list)),
                ('review_report', models.JSONField(blank=True, default=dict)),
                ('result_metadata', models.JSONField(blank=True, default=dict)),
                ('n8n_execution_id', models.CharField(blank=True, default='', max_length=160)),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('requested_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='mission_generation_runs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('target_mission', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='regeneration_runs',
                    to='accounts.mission',
                )),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.AddField(
            model_name='mission',
            name='generation_run',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='missions',
                to='accounts.generationrun',
            ),
        ),
    ]
