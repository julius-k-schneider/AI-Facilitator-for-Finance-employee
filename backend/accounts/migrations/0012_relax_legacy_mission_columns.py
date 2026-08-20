from django.db import migrations


def relax_legacy_columns(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, 'accounts_mission'
            )
        }
        for column_name in ('difficulty', 'target_role'):
            if column_name in columns:
                schema_editor.execute(
                    f'ALTER TABLE accounts_mission ALTER COLUMN {column_name} DROP NOT NULL;'
                )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_skill_difficulty_progression'),
    ]

    operations = [
        migrations.RunPython(relax_legacy_columns, migrations.RunPython.noop),
    ]
