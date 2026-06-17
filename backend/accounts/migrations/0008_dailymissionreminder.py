from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_agentchat'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyMissionReminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reminder_date', models.DateField(db_index=True)),
                ('mission_count', models.PositiveIntegerField(default=0)),
                ('missing_count', models.PositiveIntegerField(default=0)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_mission_reminders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-sent_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='dailymissionreminder',
            constraint=models.UniqueConstraint(fields=('user', 'reminder_date'), name='unique_daily_mission_reminder'),
        ),
    ]
