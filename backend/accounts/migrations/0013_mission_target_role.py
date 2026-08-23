from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0012_relax_legacy_mission_columns')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE accounts_mission
                    ADD COLUMN IF NOT EXISTS target_role varchar(16);
                    UPDATE accounts_mission SET target_role = 'all' WHERE target_role IS NULL;
                    ALTER TABLE accounts_mission ALTER COLUMN target_role SET NOT NULL;
                    CREATE INDEX IF NOT EXISTS accounts_mission_target_role_idx
                    ON accounts_mission (target_role);
                    """,
                    reverse_sql="DROP INDEX IF EXISTS accounts_mission_target_role_idx;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='mission',
                    name='target_role',
                    field=models.CharField(
                        choices=[('all', 'All finance roles'), ('accountant', 'Accountant'), ('controller', 'Controller')],
                        db_index=True,
                        default='all',
                        max_length=16,
                    ),
                ),
            ],
        ),
    ]
