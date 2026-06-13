from django.db import migrations


LEGACY_TABLE = 'accounts_userprofile'
PROFILE_TABLE = 'accounts_profile'


def reconcile_profile_schema(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    quote = connection.ops.quote_name

    if PROFILE_TABLE not in tables and LEGACY_TABLE in tables:
        schema_editor.execute(
            f'ALTER TABLE {quote(LEGACY_TABLE)} RENAME TO {quote(PROFILE_TABLE)}'
        )

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, PROFILE_TABLE)
        }

    if connection.vendor == 'postgresql':
        definitions = {
            'onboarding_completed': 'boolean NOT NULL DEFAULT false',
            'onboarding_completed_at': 'timestamp with time zone NULL',
            'onboarding_progress': "jsonb NOT NULL DEFAULT '[]'::jsonb",
            'mission_scores': "jsonb NOT NULL DEFAULT '{}'::jsonb",
            'progress_updated_at': 'timestamp with time zone NULL',
        }
    else:
        definitions = {
            'onboarding_completed': 'boolean NOT NULL DEFAULT 0',
            'onboarding_completed_at': 'datetime NULL',
            'onboarding_progress': "text NOT NULL DEFAULT '[]'",
            'mission_scores': "text NOT NULL DEFAULT '{}'",
            'progress_updated_at': 'datetime NULL',
        }

    for field_name, definition in definitions.items():
        if field_name not in columns:
            schema_editor.execute(
                f'ALTER TABLE {quote(PROFILE_TABLE)} '
                f'ADD COLUMN {quote(field_name)} {definition}'
            )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(reconcile_profile_schema, migrations.RunPython.noop),
    ]
