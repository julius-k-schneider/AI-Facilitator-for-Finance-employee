from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_generationrun_mission_generation_run'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='mission_type',
            field=models.CharField(choices=[('single_choice', 'Single Choice'), ('multiple_choice', 'Multiple Choice'), ('compliance_decision', 'Compliance Decision'), ('prompt_selection', 'Prompt Selection'), ('prompt_ranking', 'Prompt Ranking'), ('compliance_traffic_light', 'Compliance Traffic Light'), ('bulk_categorization', 'Bulk Categorization'), ('plan_actual_deviation', 'Plan vs. Actual Deviation'), ('duplicate_payment_hunt', 'Duplicate Payment Hunt'), ('invoice_extraction', 'Invoice Extraction'), ('policy_violation_check', 'Policy Violation Check'), ('receivables_aging', 'Receivables Aging'), ('vat_rate_audit', 'VAT Rate Audit'), ('bank_reconciliation', 'Bank Reconciliation')], max_length=32),
        ),
    ]
