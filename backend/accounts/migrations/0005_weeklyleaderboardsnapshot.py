from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_mission_review_workflow'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklyLeaderboardSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField(unique=True)),
                ('week_end', models.DateField()),
                ('entries', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ('-week_start',)},
        ),
    ]
