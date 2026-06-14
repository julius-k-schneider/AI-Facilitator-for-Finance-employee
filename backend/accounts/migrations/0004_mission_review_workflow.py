import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_mission_missionattempt'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='mission_type',
            field=models.CharField(
                choices=[
                    ('single_choice', 'Single Choice'),
                    ('multiple_choice', 'Multiple Choice'),
                    ('compliance_decision', 'Compliance Decision'),
                    ('prompt_selection', 'Prompt Selection'),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='mission',
            name='generated_by_ai',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mission',
            name='generation_batch_id',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='mission',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='mission',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_missions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='mission',
            name='status',
            field=models.CharField(
                choices=[('review', 'Review'), ('published', 'Published'), ('rejected', 'Rejected')],
                db_index=True,
                default='published',
                max_length=16,
            ),
        ),
    ]
