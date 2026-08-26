import datetime
import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0013_generationrun_mission_generation_run'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ResearchItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('item_key', models.CharField(max_length=80, unique=True)),
                ('title', models.CharField(max_length=500)),
                ('source_name', models.CharField(max_length=240)),
                ('source_url', models.URLField(max_length=1200)),
                ('source_feed', models.URLField(blank=True, default='', max_length=1200)),
                ('source_tier', models.PositiveSmallIntegerField(default=1)),
                ('published_at', models.DateTimeField()),
                ('retrieved_at', models.DateTimeField()),
                ('last_seen_at', models.DateTimeField()),
                ('language', models.CharField(default='en', max_length=8)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('summary_de', models.TextField(blank=True, default='')),
                ('summary_en', models.TextField(blank=True, default='')),
                ('safe_facts', models.JSONField(blank=True, default=list)),
                ('mission_hooks', models.JSONField(blank=True, default=list)),
                ('relevance_score', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('confidence', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=12)),
                ('valid_until', models.DateTimeField(db_index=True)),
                ('risk_flags', models.JSONField(blank=True, default=list)),
                ('eligible', models.BooleanField(db_index=True, default=True)),
                ('content_hash', models.CharField(blank=True, default='', max_length=120)),
                ('analysis_method', models.CharField(blank=True, default='', max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_research_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-published_at', '-retrieved_at', 'title')},
        ),
        migrations.CreateModel(
            name='ResearchRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger', models.CharField(choices=[('manual', 'Manual'), ('scheduled', 'Scheduled')], max_length=16)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], db_index=True, default='queued', max_length=16)),
                ('force_refresh', models.BooleanField(default=False)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='research_runs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='ResearchSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True)),
                ('weekday', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(6)])),
                ('run_time', models.TimeField(default=datetime.time(7, 0))),
                ('timezone_name', models.CharField(default='Europe/Berlin', max_length=64)),
                ('last_triggered_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_research_schedules', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
