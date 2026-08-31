from django.db import migrations, models


COMPLIANCE_TYPES = ['compliance_decision', 'compliance_traffic_light']


def delete_compliance_missions(apps, schema_editor):
    Mission = apps.get_model('accounts', 'Mission')
    Mission.objects.filter(mission_type__in=COMPLIANCE_TYPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_mission_analysis_task_types'),
        ('accounts', '0014_research_management'),
    ]

    operations = [
        migrations.RunPython(delete_compliance_missions, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='mission',
            name='mission_type',
            field=models.CharField(choices=[('single_choice', 'Single Choice'), ('multiple_choice', 'Multiple Choice'), ('prompt_selection', 'Prompt Selection'), ('prompt_ranking', 'Prompt Ranking'), ('bulk_categorization', 'Bulk Categorization'), ('plan_actual_deviation', 'Plan vs. Actual Deviation'), ('duplicate_payment_hunt', 'Duplicate Payment Hunt'), ('invoice_extraction', 'Invoice Extraction'), ('policy_violation_check', 'Policy Violation Check'), ('receivables_aging', 'Receivables Aging'), ('vat_rate_audit', 'VAT Rate Audit'), ('bank_reconciliation', 'Bank Reconciliation')], max_length=32),
        ),
    ]
