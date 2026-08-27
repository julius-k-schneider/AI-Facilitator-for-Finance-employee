"""AI task challenge generation and scoring.

Unlike the quiz-style missions, task challenges give the learner a larger,
realistic finance case that is meant to be solved with their own tools and an
external AI assistant (Copilot, ChatGPT, ...). The learner reads the case,
solves it outside the app, and submits structured result values plus the prompt
they used. Scoring is deterministic on the result fields; the prompt is stored
as evidence but never scored.

Each task challenge is its own mission type (not a variant of one generic
type), but they all share the same content schema and scoring machinery:

    {
      'task': {'de': ..., 'en': ...},
      'case_data': {'de': [line, ...], 'en': [line, ...]},
      'case_format': 'table' | 'prose',
      'result_fields': [
        {'id', 'type': 'number' | 'text', 'label': {'de','en'}, 'unit',
         'solution', 'tolerance', 'feedback': {'de','en'}},
        ...
      ],
      'micro_learning': {'de': ..., 'en': ...},
    }

The learner-facing content deliberately hides the solution values. Crucially,
the correct result values are computed in Python from the generated case rows -
never taken from the model - so a language model cannot corrupt the answer key
by miscalculating sums over dozens of rows.
"""

import random
from datetime import date

from accounts.prompts.task_challenges import (
    SYSTEM_PROMPT,
    build_difficulty_instruction,
    build_task_challenge_prompts,
)
from accounts.services.ai_chat_challenge import _completion
from accounts.services.ai_mission_generator import AiMissionGenerationError, extract_json


TYPE_BULK_CATEGORIZATION = 'bulk_categorization'
TYPE_PLAN_ACTUAL_DEVIATION = 'plan_actual_deviation'
TYPE_DUPLICATE_PAYMENT_HUNT = 'duplicate_payment_hunt'
TYPE_INVOICE_EXTRACTION = 'invoice_extraction'
TYPE_POLICY_VIOLATION_CHECK = 'policy_violation_check'
TYPE_RECEIVABLES_AGING = 'receivables_aging'
TYPE_VAT_RATE_AUDIT = 'vat_rate_audit'
TYPE_BANK_RECONCILIATION = 'bank_reconciliation'

DEFAULT_POINTS = 40
# One budget for every task-generation call site. A hard variant emits 48 rows with two prose
# fields each, and the generator is a reasoning model whose thinking counts against this cap:
# too low and the response is truncated mid-array, which the n8n JSON repair then closes into a
# valid but short row list - surfacing as a bogus row-count contract failure.
GENERATION_MAX_TOKENS = 12000
# The four analysis types carry many simultaneous constraints, and models reliably satisfy the
# content rules while overshooting the row count. These accept a band instead of an exact number.
# The prompts ask for an exact row count and hand the model an "index" counter to hit it.
# This small tolerance is only a net for the occasional stray row; the index field itself is
# a generation aid and is deliberately not part of the validated schema.
VOLUME_BAND_TOLERANCE = 4
MIN_ROWS = 24
MAX_ROWS = 60
MIN_INVOICES = 12
MAX_INVOICES = 20

# The travel policy the learner applies. Limits live in Python so the answer key never
# depends on the model reproducing the rule set correctly.
POLICY_HOTEL_LIMIT_PER_NIGHT = 150.0
POLICY_HOSPITALITY_LIMIT_PER_GUEST = 60.0
POLICY_TAXI_MIN_KM = 2
# Short, typeable rule names - the learner enters one of these as a text answer.
POLICY_RULE_LABELS = {
    'hotel': {'de': 'Hotel', 'en': 'Hotel'},
    'hospitality': {'de': 'Bewirtung', 'en': 'Hospitality'},
    'taxi': {'de': 'Taxi', 'en': 'Taxi'},
}
POLICY_CATEGORIES = set(POLICY_RULE_LABELS) | {'other'}

# Reduced and standard German VAT rates keyed by what was bought.
VAT_RATE_VALUES = (7, 19)
VAT_RATES = {
    'books': 7, 'periodicals': 7, 'groceries': 7, 'hotel_stay': 7, 'local_transport': 7,
    'software': 19, 'consulting': 19, 'office_supplies': 19, 'electronics': 19,
    'catering_service': 19, 'vehicle_rental': 19,
}

VOLUME_BAND_TYPES = frozenset({
    TYPE_POLICY_VIOLATION_CHECK, TYPE_RECEIVABLES_AGING, TYPE_VAT_RATE_AUDIT, TYPE_BANK_RECONCILIATION,
})

DIFFICULTY_POINTS = {'easy': 30, 'medium': 40, 'hard': 50}
DEFAULT_RESULT_FIELD_IDS = {
    TYPE_PLAN_ACTUAL_DEVIATION: ('total_overrun', 'count_over_threshold', 'max_deviation'),
    TYPE_DUPLICATE_PAYMENT_HUNT: ('duplicate_pairs_count', 'risk_amount_sum'),
    TYPE_INVOICE_EXTRACTION: ('top_invoice_number', 'top_vendor', 'total_amount'),
    TYPE_POLICY_VIOLATION_CHECK: ('violation_count', 'non_reimbursable_sum', 'largest_violation'),
    TYPE_RECEIVABLES_AGING: ('overdue_total', 'count_over_60', 'sum_over_60'),
    TYPE_VAT_RATE_AUDIT: ('wrong_line_count', 'correct_total_vat', 'vat_difference_sum'),
    TYPE_BANK_RECONCILIATION: ('bank_only_count', 'ledger_only_count', 'unmatched_amount_sum'),
}
DIFFICULTY_RESULT_FIELD_IDS = {
    TYPE_PLAN_ACTUAL_DEVIATION: {
        'easy': ('total_overrun', 'count_over_threshold'),
        'medium': ('total_overrun', 'count_over_threshold', 'max_deviation'),
        'hard': (
            'total_overrun', 'count_over_threshold', 'max_deviation',
            'average_positive_overrun', 'total_underrun',
        ),
    },
    TYPE_DUPLICATE_PAYMENT_HUNT: {
        'easy': ('duplicate_pairs_count',),
        'medium': ('duplicate_pairs_count', 'risk_amount_sum'),
        'hard': ('duplicate_pairs_count', 'risk_amount_sum', 'largest_duplicate_amount'),
    },
    TYPE_INVOICE_EXTRACTION: {
        'easy': ('top_invoice_number', 'total_amount'),
        'medium': ('top_invoice_number', 'total_amount', 'top_vendor'),
        'hard': ('top_invoice_number', 'total_amount', 'top_vendor', 'average_invoice_amount'),
    },
    TYPE_POLICY_VIOLATION_CHECK: {
        'easy': ('violation_count', 'non_reimbursable_sum'),
        'medium': ('violation_count', 'non_reimbursable_sum', 'largest_violation'),
        'hard': ('violation_count', 'non_reimbursable_sum', 'largest_violation', 'top_rule'),
    },
    TYPE_RECEIVABLES_AGING: {
        'easy': ('overdue_total', 'count_over_60'),
        'medium': ('overdue_total', 'count_over_60', 'sum_over_60'),
        'hard': ('overdue_total', 'count_over_60', 'sum_over_60', 'oldest_invoice_number'),
    },
    TYPE_VAT_RATE_AUDIT: {
        'easy': ('wrong_line_count', 'correct_total_vat'),
        'medium': ('wrong_line_count', 'correct_total_vat', 'vat_difference_sum'),
        'hard': ('wrong_line_count', 'correct_total_vat', 'vat_difference_sum', 'largest_vat_difference'),
    },
    TYPE_BANK_RECONCILIATION: {
        'easy': ('bank_only_count', 'ledger_only_count'),
        'medium': ('bank_only_count', 'ledger_only_count', 'unmatched_amount_sum'),
        'hard': ('bank_only_count', 'ledger_only_count', 'unmatched_amount_sum', 'largest_unmatched_amount'),
    },
}

TASK_TOPICS = {
    TYPE_BULK_CATEGORIZATION: {
        'topic_de': 'Buchungen mit KI kategorisieren',
        'topic_en': 'Categorizing bookings with AI',
        'learning_objective_de': 'KI für eine nachvollziehbare Massenkategorisierung einsetzen und Ergebnisse prüfen.',
        'learning_objective_en': 'Use AI for traceable bulk categorization and verify the results.',
    },
    TYPE_PLAN_ACTUAL_DEVIATION: {
        'topic_de': 'Plan-Ist-Abweichungen mit KI analysieren',
        'topic_en': 'Analyzing plan-versus-actual variances with AI',
        'learning_objective_de': 'KI zur strukturierten Abweichungsanalyse einsetzen und Berechnungen validieren.',
        'learning_objective_en': 'Use AI for structured variance analysis and validate calculations.',
    },
    TYPE_DUPLICATE_PAYMENT_HUNT: {
        'topic_de': 'Mögliche Doppelzahlungen mit KI finden',
        'topic_en': 'Finding potential duplicate payments with AI',
        'learning_objective_de': 'KI zur Dublettenerkennung einsetzen und Treffer anhand klarer Kriterien prüfen.',
        'learning_objective_en': 'Use AI to detect duplicates and verify matches against clear criteria.',
    },
    TYPE_INVOICE_EXTRACTION: {
        'topic_de': 'Rechnungsdaten mit KI extrahieren',
        'topic_en': 'Extracting invoice data with AI',
        'learning_objective_de': 'Rechnungsinformationen strukturiert extrahieren und auf Vollständigkeit prüfen.',
        'learning_objective_en': 'Extract invoice information into a structure and verify completeness.',
    },
    TYPE_POLICY_VIOLATION_CHECK: {
        'topic_de': 'Reisekostenrichtlinie mit KI prüfen',
        'topic_en': 'Checking the travel policy with AI',
        'learning_objective_de': 'Ein vorgegebenes Regelwerk präzise an die KI übergeben und ihre Treffer prüfen.',
        'learning_objective_en': 'Hand a given rule set to AI precisely and verify the matches it returns.',
    },
    TYPE_RECEIVABLES_AGING: {
        'topic_de': 'Offene Posten mit KI nach Alter auswerten',
        'topic_en': 'Aging open receivables with AI',
        'learning_objective_de': 'Zahlungsziele aus Freitext ableiten und die Fristenrechnung der KI validieren.',
        'learning_objective_en': 'Derive payment terms from free text and validate the AI date arithmetic.',
    },
    TYPE_VAT_RATE_AUDIT: {
        'topic_de': 'Umsatzsteuersätze mit KI prüfen',
        'topic_en': 'Auditing VAT rates with AI',
        'learning_objective_de': 'Steuersätze aus der Leistungsbeschreibung ableiten und die Rechnung nachvollziehen.',
        'learning_objective_en': 'Derive tax rates from the service description and retrace the calculation.',
    },
    TYPE_BANK_RECONCILIATION: {
        'topic_de': 'Bankauszug mit KI abstimmen',
        'topic_en': 'Reconciling a bank statement with AI',
        'learning_objective_de': 'Freitext-Verwendungszwecke gegen Buchungen abgleichen und Treffer kritisch prüfen.',
        'learning_objective_en': 'Match free-text payment references against ledger entries and check hits critically.',
    },
}

def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise AiMissionGenerationError(f'AI task challenge field {field} is invalid')
    return value.strip()


def _format_amount(amount):
    # German number format (period thousands, comma decimal) so pasted case data is
    # recognized as a real number in a German-locale Excel, not as text.
    return f'{amount:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def _format_amount_en(amount):
    return f'{amount:,.2f}'


def _bilingual(payload, prefix, field):
    return {'de': _text(payload.get(f'{prefix}_de'), f'{field}_de'), 'en': _text(payload.get(f'{prefix}_en'), f'{field}_en')}


def _amount(value, label):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError) as exception:
        raise AiMissionGenerationError(f'AI task challenge {label} is invalid') from exception


def _number_field(field_id, label, unit, solution, tolerance, feedback_de, feedback_en):
    return {
        'id': field_id,
        'type': 'number',
        'label': label,
        'unit': unit,
        'solution': solution,
        'tolerance': tolerance,
        'feedback': {'de': feedback_de, 'en': feedback_en},
    }


def _text_field(field_id, label, solution_de, solution_en, feedback_de, feedback_en):
    return {
        'id': field_id,
        'type': 'text',
        'label': label,
        'unit': '',
        'solution': {'de': solution_de, 'en': solution_en},
        'feedback': {'de': feedback_de, 'en': feedback_en},
    }


def _validate_bulk_categorization(payload):
    categories_de = payload.get('categories_de')
    categories_en = payload.get('categories_en')
    if not isinstance(categories_de, list) or not isinstance(categories_en, list):
        raise AiMissionGenerationError('AI task challenge categories are invalid')
    if len(categories_de) != len(categories_en) or not 2 <= len(categories_de) <= 5:
        raise AiMissionGenerationError('AI task challenge needs 2-5 aligned categories')
    categories = [
        {'de': _text(de, 'category_de'), 'en': _text(en, 'category_en')}
        for de, en in zip(categories_de, categories_en)
    ]

    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    totals = [0.0 for _ in categories]
    counts = [0 for _ in categories]
    case_de = []
    case_en = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        date = _text(row.get('date'), f'row {index + 1} date')
        description_de = _text(row.get('description_de'), f'row {index + 1} description_de')
        description_en = _text(row.get('description_en'), f'row {index + 1} description_en')
        amount = _amount(row.get('amount'), f'row {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amount must be positive')
        try:
            category_index = int(row.get('category_index'))
        except (TypeError, ValueError) as exception:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} category is invalid') from exception
        if not 0 <= category_index < len(categories):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} category is out of range')
        totals[category_index] += amount
        counts[category_index] += 1
        case_de.append(f'{date} | {_format_amount(amount)} € | {description_de}')
        case_en.append(f'{date} | €{_format_amount_en(amount)} | {description_en}')

    if any(count < 3 for count in counts):
        raise AiMissionGenerationError('AI task challenge must use every category at least three times')

    result_fields = []
    for index, category in enumerate(categories):
        total = round(totals[index], 2)
        result_fields.append(_number_field(
            f'sum_{index}',
            {'de': f'Summe {category["de"]} (€)', 'en': f'Total {category["en"]} (€)'},
            '€', total, 0.5,
            f'Die korrekte Summe für {category["de"]} beträgt {_format_amount(total)} €.',
            f'The correct total for {category["en"]} is €{_format_amount_en(total)}.',
        ))

    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _validate_plan_actual_deviation(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    case_de = []
    case_en = []
    total_overrun = 0.0
    positive_overrun_count = 0
    total_underrun = 0.0
    over_threshold = 0
    max_deviation = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        name_de = _text(row.get('cost_center_de'), f'row {index + 1} cost_center_de')
        name_en = _text(row.get('cost_center_en'), f'row {index + 1} cost_center_en')
        plan = _amount(row.get('plan'), f'row {index + 1} plan')
        actual = _amount(row.get('actual'), f'row {index + 1} actual')
        if plan <= 0 or actual <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amounts must be positive')
        deviation = round(actual - plan, 2)
        if deviation > 0:
            total_overrun += deviation
            positive_overrun_count += 1
            if deviation / plan > 0.10:
                over_threshold += 1
        elif deviation < 0:
            total_underrun += abs(deviation)
        if max_deviation is None or deviation > max_deviation:
            max_deviation = deviation
        case_de.append(f'{name_de} | Plan {_format_amount(plan)} € | Ist {_format_amount(actual)} €')
        case_en.append(
            f'{name_en} | Plan €{_format_amount_en(plan)} | Actual €{_format_amount_en(actual)}'
        )

    if over_threshold < 4:
        raise AiMissionGenerationError('AI task challenge needs at least 4 cost centers overrunning plan by more than 10%')

    total_overrun = round(total_overrun, 2)
    max_deviation = round(max_deviation, 2)
    average_positive_overrun = round(total_overrun / positive_overrun_count, 2)
    total_underrun = round(total_underrun, 2)
    result_fields = [
        _number_field(
            'total_overrun', {'de': 'Summe der Budgetüberschreitungen (€)', 'en': 'Total budget overruns (€)'},
            '€', total_overrun, 0.5,
            f'Die Summe aller Überschreitungen beträgt {_format_amount(total_overrun)} €.',
            f'The total of all overruns is €{_format_amount_en(total_overrun)}.',
        ),
        _number_field(
            'count_over_threshold',
            {'de': 'Kostenstellen über 10% Abweichung', 'en': 'Cost centers over 10% deviation'},
            '', over_threshold, 0,
            f'{over_threshold} Kostenstellen liegen mehr als 10% über Plan.',
            f'{over_threshold} cost centers exceed plan by more than 10%.',
        ),
        _number_field(
            'max_deviation', {'de': 'Größte Einzelabweichung (€)', 'en': 'Largest single deviation (€)'},
            '€', max_deviation, 0.5,
            f'Die größte Einzelabweichung beträgt {_format_amount(max_deviation)} €.',
            f'The largest single deviation is €{_format_amount_en(max_deviation)}.',
        ),
        _number_field(
            'average_positive_overrun',
            {'de': 'Durchschnittliche positive Überschreitung (€)', 'en': 'Average positive overrun (€)'},
            '€', average_positive_overrun, 0.5,
            f'Die durchschnittliche positive Überschreitung beträgt {_format_amount(average_positive_overrun)} €.',
            f'The average positive overrun is €{_format_amount_en(average_positive_overrun)}.',
        ),
        _number_field(
            'total_underrun',
            {'de': 'Summe der Budgetunterschreitungen (€)', 'en': 'Total budget underruns (€)'},
            '€', total_underrun, 0.5,
            f'Die Summe aller absoluten Unterschreitungen beträgt {_format_amount(total_underrun)} €.',
            f'The absolute total of all underruns is €{_format_amount_en(total_underrun)}.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _validate_duplicate_payment_hunt(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    by_invoice = {}
    case_de = []
    case_en = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        date = _text(row.get('date'), f'row {index + 1} date')
        vendor_de = _text(row.get('vendor_de'), f'row {index + 1} vendor_de')
        vendor_en = _text(row.get('vendor_en'), f'row {index + 1} vendor_en')
        invoice_number = _text(row.get('invoice_number'), f'row {index + 1} invoice_number')
        amount = _amount(row.get('amount'), f'row {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amount must be positive')
        by_invoice.setdefault(invoice_number, []).append(amount)
        case_de.append(f'{date} | {vendor_de} | Rechnung {invoice_number} | {_format_amount(amount)} €')
        case_en.append(f'{date} | {vendor_en} | Invoice {invoice_number} | €{_format_amount_en(amount)}')

    duplicate_pairs = 0
    risk_amount = 0.0
    largest_duplicate_amount = 0.0
    for invoice_number, amounts in by_invoice.items():
        if len(amounts) > 2:
            raise AiMissionGenerationError(f'AI task challenge invoice number {invoice_number} appears more than twice')
        if len(amounts) == 2:
            if abs(amounts[0] - amounts[1]) > 0.01:
                raise AiMissionGenerationError(f'AI task challenge duplicate pair {invoice_number} amounts must match')
            duplicate_pairs += 1
            risk_amount += amounts[1]
            largest_duplicate_amount = max(largest_duplicate_amount, amounts[1])

    if duplicate_pairs < 3:
        raise AiMissionGenerationError('AI task challenge needs at least 3 duplicate payment pairs')

    risk_amount = round(risk_amount, 2)
    result_fields = [
        _number_field(
            'duplicate_pairs_count', {'de': 'Anzahl Doppelzahlungen', 'en': 'Number of duplicate payments'},
            '', duplicate_pairs, 0,
            f'Es gibt {duplicate_pairs} Doppelzahlungen.',
            f'There are {duplicate_pairs} duplicate payments.',
        ),
        _number_field(
            'risk_amount_sum', {'de': 'Summe Doppelzahlungsrisiko (€)', 'en': 'Total duplicate payment risk (€)'},
            '€', risk_amount, 0.5,
            f'Das Doppelzahlungsrisiko beträgt {_format_amount(risk_amount)} €.',
            f'The duplicate payment risk totals €{_format_amount_en(risk_amount)}.',
        ),
        _number_field(
            'largest_duplicate_amount',
            {'de': 'Größte einzelne Doppelzahlung (€)', 'en': 'Largest single duplicate payment (€)'},
            '€', largest_duplicate_amount, 0.5,
            f'Die größte einzelne Doppelzahlung beträgt {_format_amount(largest_duplicate_amount)} €.',
            f'The largest single duplicate payment is €{_format_amount_en(largest_duplicate_amount)}.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _normalize_text_answer(value):
    return ' '.join(str(value or '').split()).strip().casefold()


def _validate_invoice_extraction(payload):
    invoices = payload.get('invoices')
    if not isinstance(invoices, list) or not MIN_INVOICES <= len(invoices) <= MAX_INVOICES:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_INVOICES}-{MAX_INVOICES} invoices')

    case_de = []
    case_en = []
    seen_numbers = set()
    vendor_totals_de = {}
    vendor_totals_en = {}
    vendor_invoice_counts = {}
    total_amount = 0.0
    top_amount = None
    top_invoice_number = None
    for index, invoice in enumerate(invoices):
        if not isinstance(invoice, dict):
            raise AiMissionGenerationError(f'AI task challenge invoice {index + 1} is invalid')
        invoice_number = _text(invoice.get('invoice_number'), f'invoice {index + 1} invoice_number')
        if invoice_number in seen_numbers:
            raise AiMissionGenerationError(f'AI task challenge invoice number {invoice_number} is not unique')
        seen_numbers.add(invoice_number)
        vendor_de = _text(invoice.get('vendor_de'), f'invoice {index + 1} vendor_de')
        vendor_en = _text(invoice.get('vendor_en'), f'invoice {index + 1} vendor_en')
        amount = _amount(invoice.get('amount'), f'invoice {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge invoice {index + 1} amount must be positive')
        text_de = _text(invoice.get('text_de'), f'invoice {index + 1} text_de')
        text_en = _text(invoice.get('text_en'), f'invoice {index + 1} text_en')

        total_amount += amount
        vendor_totals_de[vendor_de] = vendor_totals_de.get(vendor_de, 0.0) + amount
        vendor_totals_en[vendor_en] = vendor_totals_en.get(vendor_en, 0.0) + amount
        vendor_invoice_counts[vendor_de] = vendor_invoice_counts.get(vendor_de, 0) + 1
        if top_amount is None or amount > top_amount:
            top_amount = amount
            top_invoice_number = invoice_number

        case_de.append(text_de)
        case_en.append(text_en)

    repeat_vendors = sum(1 for count in vendor_invoice_counts.values() if count > 1)
    if repeat_vendors < 3:
        raise AiMissionGenerationError('AI task challenge needs at least 3 vendors appearing on more than one invoice')

    top_vendor_de = max(vendor_totals_de, key=vendor_totals_de.get)
    top_vendor_en = max(vendor_totals_en, key=vendor_totals_en.get)
    total_amount = round(total_amount, 2)
    average_invoice_amount = round(total_amount / len(invoices), 2)

    result_fields = [
        _text_field(
            'top_invoice_number', {'de': 'Rechnungsnummer mit dem höchsten Betrag', 'en': 'Invoice number with the highest amount'},
            top_invoice_number, top_invoice_number,
            f'Die Rechnung mit dem höchsten Betrag ist {top_invoice_number}.',
            f'The invoice with the highest amount is {top_invoice_number}.',
        ),
        _text_field(
            'top_vendor', {'de': 'Lieferant mit dem größten Rechnungsvolumen', 'en': 'Vendor with the largest invoice volume'},
            top_vendor_de, top_vendor_en,
            f'Der Lieferant mit dem größten Volumen ist {top_vendor_de}.',
            f'The vendor with the largest volume is {top_vendor_en}.',
        ),
        _number_field(
            'total_amount', {'de': 'Summe aller Rechnungen (€)', 'en': 'Total of all invoices (€)'},
            '€', total_amount, 0.5,
            f'Die Summe aller Rechnungen beträgt {_format_amount(total_amount)} €.',
            f'The total of all invoices is €{_format_amount_en(total_amount)}.',
        ),
        _number_field(
            'average_invoice_amount',
            {'de': 'Durchschnittlicher Rechnungsbetrag (€)', 'en': 'Average invoice amount (€)'},
            '€', average_invoice_amount, 0.5,
            f'Der durchschnittliche Rechnungsbetrag beträgt {_format_amount(average_invoice_amount)} €.',
            f'The average invoice amount is €{_format_amount_en(average_invoice_amount)}.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'prose'

def _whole_number(value, label, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError) as exception:
        raise AiMissionGenerationError(f'AI task challenge {label} is invalid') from exception
    if not minimum <= number <= maximum:
        raise AiMissionGenerationError(f'AI task challenge {label} is out of range')
    return number


def _iso_date(value, label):
    try:
        return date.fromisoformat(_text(value, label))
    except ValueError as exception:
        raise AiMissionGenerationError(f'AI task challenge {label} is not a valid date') from exception


def _maximum(values):
    """Largest value plus whether it is the only one at that height.

    A tie makes a "largest single ..." answer ambiguous, but only for the difficulty
    that actually asks for it - so the verdict travels with the field and is enforced
    in validate_task_challenge after the field list has been trimmed.
    """
    ordered = sorted(values, reverse=True)
    if not ordered:
        return 0.0, True
    return ordered[0], len(ordered) < 2 or ordered[0] > ordered[1]


def _flag_ambiguous(field, unique):
    if not unique:
        field['ambiguous'] = True
    return field


def _policy_excess(category, units, amount):
    # Non-reimbursable portion of one expense line under the fixed travel policy.
    if category == 'hotel':
        return max(0.0, round(amount - POLICY_HOTEL_LIMIT_PER_NIGHT * units, 2))
    if category == 'hospitality':
        return max(0.0, round(amount - POLICY_HOSPITALITY_LIMIT_PER_GUEST * units, 2))
    if category == 'taxi':
        return amount if units < POLICY_TAXI_MIN_KM else 0.0
    return 0.0


def _validate_policy_violation_check(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    case_de = []
    case_en = []
    excesses = []
    violations_by_rule = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        date_value = _text(row.get('date'), f'row {index + 1} date')
        employee_de = _text(row.get('employee_de'), f'row {index + 1} employee_de')
        employee_en = _text(row.get('employee_en'), f'row {index + 1} employee_en')
        description_de = _text(row.get('description_de'), f'row {index + 1} description_de')
        description_en = _text(row.get('description_en'), f'row {index + 1} description_en')
        amount = _amount(row.get('amount'), f'row {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amount must be positive')
        category = _text(row.get('category'), f'row {index + 1} category')
        if category not in POLICY_CATEGORIES:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} category is unsupported')
        units = _whole_number(row.get('units'), f'row {index + 1} units', 1, 12)

        # The rule input must be readable from the prose - that is what makes the task AI-shaped.
        if category != 'other' and (str(units) not in description_de or str(units) not in description_en):
            raise AiMissionGenerationError(
                f'AI task challenge row {index + 1} must state its unit count as a digit in both descriptions'
            )

        excess = _policy_excess(category, units, amount)
        if excess > 0:
            excesses.append(excess)
            violations_by_rule[category] = violations_by_rule.get(category, 0) + 1

        case_de.append(f'{date_value} | {employee_de} | {description_de} | {_format_amount(amount)} €')
        case_en.append(f'{date_value} | {employee_en} | {description_en} | €{_format_amount_en(amount)}')

    if not excesses:
        raise AiMissionGenerationError('AI task challenge needs at least one policy violation')
    if len(violations_by_rule) < 2:
        raise AiMissionGenerationError('AI task challenge needs violations of at least two different rules')

    violation_count = len(excesses)
    non_reimbursable_sum = round(sum(excesses), 2)
    largest_violation, largest_is_unique = _maximum(excesses)
    top_rule = max(violations_by_rule, key=violations_by_rule.get)
    rule_counts = sorted(violations_by_rule.values(), reverse=True)
    top_rule_is_unique = len(rule_counts) < 2 or rule_counts[0] > rule_counts[1]
    top_rule_de = POLICY_RULE_LABELS[top_rule]['de']
    top_rule_en = POLICY_RULE_LABELS[top_rule]['en']

    result_fields = [
        _number_field(
            'violation_count', {'de': 'Anzahl Regelverstöße', 'en': 'Number of policy violations'},
            '', violation_count, 0,
            f'Es liegen {violation_count} Regelverstöße vor.',
            f'There are {violation_count} policy violations.',
        ),
        _number_field(
            'non_reimbursable_sum',
            {'de': 'Nicht erstattungsfähiger Betrag (€)', 'en': 'Non-reimbursable amount (€)'},
            '€', non_reimbursable_sum, 0.5,
            f'Nicht erstattungsfähig sind insgesamt {_format_amount(non_reimbursable_sum)} €.',
            f'A total of €{_format_amount_en(non_reimbursable_sum)} is non-reimbursable.',
        ),
        _flag_ambiguous(_number_field(
            'largest_violation', {'de': 'Größter Einzelverstoß (€)', 'en': 'Largest single violation (€)'},
            '€', largest_violation, 0.5,
            f'Der größte Einzelverstoß beträgt {_format_amount(largest_violation)} €.',
            f'The largest single violation is €{_format_amount_en(largest_violation)}.',
        ), largest_is_unique),
        _flag_ambiguous(_text_field(
            'top_rule',
            {'de': 'Am häufigsten verletzte Regel (Hotel, Bewirtung oder Taxi)',
             'en': 'Most frequently broken rule (Hotel, Hospitality or Taxi)'},
            top_rule_de, top_rule_en,
            f'Am häufigsten wurde die Regel {top_rule_de} verletzt.',
            f'The rule broken most often is {top_rule_en}.',
        ), top_rule_is_unique),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _validate_receivables_aging(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')
    reference_date = _iso_date(payload.get('reference_date'), 'reference_date')

    case_de = []
    case_en = []
    seen_numbers = set()
    overdue_total = 0.0
    over_60_amounts = []
    overdue_days_by_invoice = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        invoice_number = _text(row.get('invoice_number'), f'row {index + 1} invoice_number')
        if invoice_number in seen_numbers:
            raise AiMissionGenerationError(f'AI task challenge invoice number {invoice_number} is not unique')
        seen_numbers.add(invoice_number)
        customer_de = _text(row.get('customer_de'), f'row {index + 1} customer_de')
        customer_en = _text(row.get('customer_en'), f'row {index + 1} customer_en')
        term_de = _text(row.get('term_de'), f'row {index + 1} term_de')
        term_en = _text(row.get('term_en'), f'row {index + 1} term_en')
        amount = _amount(row.get('amount'), f'row {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amount must be positive')
        invoice_date = _iso_date(row.get('invoice_date'), f'row {index + 1} invoice_date')
        if invoice_date >= reference_date:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} must be dated before the reference date')
        term_days = _whole_number(row.get('term_days'), f'row {index + 1} term_days', 0, 90)

        # The payment term must be legible from the wording, not from a numeric column.
        if term_days > 0 and (str(term_days) not in term_de or str(term_days) not in term_en):
            raise AiMissionGenerationError(
                f'AI task challenge row {index + 1} must state its payment term as a digit in both languages'
            )

        days_overdue = (reference_date - invoice_date).days - term_days
        if days_overdue == 0:
            raise AiMissionGenerationError(
                f'AI task challenge row {index + 1} becomes due exactly on the reference date'
            )
        if days_overdue > 0:
            overdue_total += amount
            overdue_days_by_invoice[invoice_number] = days_overdue
            if days_overdue > 60:
                over_60_amounts.append(amount)

        case_de.append(
            f'{invoice_number} | {customer_de} | Rechnung vom {invoice_date.isoformat()} | '
            f'Zahlungsziel: {term_de} | {_format_amount(amount)} €'
        )
        case_en.append(
            f'{invoice_number} | {customer_en} | Invoiced {invoice_date.isoformat()} | '
            f'Payment term: {term_en} | €{_format_amount_en(amount)}'
        )

    if not over_60_amounts:
        raise AiMissionGenerationError('AI task challenge needs invoices more than 60 days overdue')
    if not overdue_days_by_invoice:
        raise AiMissionGenerationError('AI task challenge needs at least one overdue invoice')
    _, oldest_is_unique = _maximum(list(overdue_days_by_invoice.values()))
    oldest_invoice_number = max(overdue_days_by_invoice, key=overdue_days_by_invoice.get)

    overdue_total = round(overdue_total, 2)
    count_over_60 = len(over_60_amounts)
    sum_over_60 = round(sum(over_60_amounts), 2)

    result_fields = [
        _number_field(
            'overdue_total', {'de': 'Summe aller überfälligen Beträge (€)', 'en': 'Total overdue amount (€)'},
            '€', overdue_total, 0.5,
            f'Überfällig sind insgesamt {_format_amount(overdue_total)} €.',
            f'A total of €{_format_amount_en(overdue_total)} is overdue.',
        ),
        _number_field(
            'count_over_60', {'de': 'Rechnungen über 60 Tage überfällig', 'en': 'Invoices more than 60 days overdue'},
            '', count_over_60, 0,
            f'{count_over_60} Rechnungen sind mehr als 60 Tage überfällig.',
            f'{count_over_60} invoices are more than 60 days overdue.',
        ),
        _number_field(
            'sum_over_60',
            {'de': 'Summe über 60 Tage überfällig (€)', 'en': 'Total more than 60 days overdue (€)'},
            '€', sum_over_60, 0.5,
            f'Mehr als 60 Tage überfällig sind {_format_amount(sum_over_60)} €.',
            f'€{_format_amount_en(sum_over_60)} is more than 60 days overdue.',
        ),
        _flag_ambiguous(_text_field(
            'oldest_invoice_number',
            {'de': 'Rechnungsnummer mit den meisten Überfälligkeitstagen',
             'en': 'Invoice number with the most days overdue'},
            oldest_invoice_number, oldest_invoice_number,
            f'Am längsten überfällig ist die Rechnung {oldest_invoice_number}.',
            f'The invoice overdue the longest is {oldest_invoice_number}.',
        ), oldest_is_unique),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _validate_vat_rate_audit(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    case_de = []
    case_en = []
    correct_total_vat = 0.0
    differences = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        date_value = _text(row.get('date'), f'row {index + 1} date')
        description_de = _text(row.get('description_de'), f'row {index + 1} description_de')
        description_en = _text(row.get('description_en'), f'row {index + 1} description_en')
        category = _text(row.get('category'), f'row {index + 1} category')
        if category not in VAT_RATES:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} category is unsupported')
        net = _amount(row.get('net'), f'row {index + 1} net')
        if net <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} net must be positive')
        booked_rate = _whole_number(row.get('booked_rate'), f'row {index + 1} booked_rate', 7, 19)
        if booked_rate not in VAT_RATE_VALUES:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} booked_rate must be 7 or 19')

        booked_vat = round(net * booked_rate / 100, 2)
        correct_vat = round(net * VAT_RATES[category] / 100, 2)
        correct_total_vat += correct_vat
        difference = round(abs(booked_vat - correct_vat), 2)
        if difference > 0.01:
            differences.append(difference)

        case_de.append(
            f'{date_value} | {description_de} | Netto {_format_amount(net)} € | '
            f'gebucht mit {booked_rate} % | USt {_format_amount(booked_vat)} €'
        )
        case_en.append(
            f'{date_value} | {description_en} | Net €{_format_amount_en(net)} | '
            f'booked at {booked_rate}% | VAT €{_format_amount_en(booked_vat)}'
        )

    if not differences:
        raise AiMissionGenerationError('AI task challenge needs at least one incorrectly booked VAT line')

    wrong_line_count = len(differences)
    correct_total_vat = round(correct_total_vat, 2)
    vat_difference_sum = round(sum(differences), 2)
    largest_vat_difference, largest_vat_is_unique = _maximum(differences)

    result_fields = [
        _number_field(
            'wrong_line_count', {'de': 'Anzahl fehlerhafter Zeilen', 'en': 'Number of incorrect lines'},
            '', wrong_line_count, 0,
            f'{wrong_line_count} Zeilen wurden mit falscher Umsatzsteuer gebucht.',
            f'{wrong_line_count} lines were booked with incorrect VAT.',
        ),
        _number_field(
            'correct_total_vat', {'de': 'Korrekte Gesamt-USt (€)', 'en': 'Correct total VAT (€)'},
            '€', correct_total_vat, 0.5,
            f'Die korrekte Gesamt-Umsatzsteuer beträgt {_format_amount(correct_total_vat)} €.',
            f'The correct total VAT is €{_format_amount_en(correct_total_vat)}.',
        ),
        _number_field(
            'vat_difference_sum', {'de': 'Summe der USt-Differenzen (€)', 'en': 'Total VAT difference (€)'},
            '€', vat_difference_sum, 0.5,
            f'Die Summe der absoluten USt-Differenzen beträgt {_format_amount(vat_difference_sum)} €.',
            f'The total absolute VAT difference is €{_format_amount_en(vat_difference_sum)}.',
        ),
        _flag_ambiguous(_number_field(
            'largest_vat_difference', {'de': 'Größte einzelne USt-Differenz (€)', 'en': 'Largest single VAT difference (€)'},
            '€', largest_vat_difference, 0.5,
            f'Die größte einzelne USt-Differenz beträgt {_format_amount(largest_vat_difference)} €.',
            f'The largest single VAT difference is €{_format_amount_en(largest_vat_difference)}.',
        ), largest_vat_is_unique),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


def _validate_bank_reconciliation(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    case_de = []
    case_en = []
    by_side = {'bank': {}, 'ledger': {}}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} is invalid')
        source = _text(row.get('source'), f'row {index + 1} source')
        if source not in by_side:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} source must be bank or ledger')
        date_value = _text(row.get('date'), f'row {index + 1} date')
        document = _text(row.get('document'), f'row {index + 1} document')
        text_de = _text(row.get('text_de'), f'row {index + 1} text_de')
        text_en = _text(row.get('text_en'), f'row {index + 1} text_en')
        amount = _amount(row.get('amount'), f'row {index + 1} amount')
        if amount <= 0:
            raise AiMissionGenerationError(f'AI task challenge row {index + 1} amount must be positive')
        if document in by_side[source]:
            raise AiMissionGenerationError(f'AI task challenge document {document} appears twice on the {source} side')
        by_side[source][document] = amount

        if source == 'bank':
            case_de.append(f'Bank | {date_value} | – | {text_de} | {_format_amount(amount)} €')
            case_en.append(f'Bank | {date_value} | – | {text_en} | €{_format_amount_en(amount)}')
        else:
            case_de.append(f'Buchhaltung | {date_value} | {document} | {text_de} | {_format_amount(amount)} €')
            case_en.append(f'Ledger | {date_value} | {document} | {text_en} | €{_format_amount_en(amount)}')

    bank_only = []
    for document, amount in by_side['bank'].items():
        counterpart = by_side['ledger'].get(document)
        if counterpart is None:
            bank_only.append(amount)
        elif abs(counterpart - amount) > 0.01:
            raise AiMissionGenerationError(f'AI task challenge document {document} must match on both sides')
    ledger_only = [amount for document, amount in by_side['ledger'].items() if document not in by_side['bank']]

    if not bank_only or not ledger_only:
        raise AiMissionGenerationError('AI task challenge needs unmatched items on both sides')
    if len(bank_only) == len(ledger_only):
        raise AiMissionGenerationError('AI task challenge needs a different unmatched count per side')

    unmatched_amounts = bank_only + ledger_only
    unmatched_amount_sum = round(sum(unmatched_amounts), 2)
    largest_unmatched_amount, largest_unmatched_is_unique = _maximum(unmatched_amounts)

    result_fields = [
        _number_field(
            'bank_only_count', {'de': 'Posten nur im Bankauszug', 'en': 'Items only in the bank statement'},
            '', len(bank_only), 0,
            f'{len(bank_only)} Posten stehen nur im Bankauszug.',
            f'{len(bank_only)} items appear only in the bank statement.',
        ),
        _number_field(
            'ledger_only_count', {'de': 'Posten nur in der Buchhaltung', 'en': 'Items only in the ledger'},
            '', len(ledger_only), 0,
            f'{len(ledger_only)} Posten stehen nur in der Buchhaltung.',
            f'{len(ledger_only)} items appear only in the ledger.',
        ),
        _number_field(
            'unmatched_amount_sum',
            {'de': 'Summe aller nicht abgeglichenen Posten (€)', 'en': 'Total of all unmatched items (€)'},
            '€', unmatched_amount_sum, 0.5,
            f'Die nicht abgeglichenen Posten summieren sich auf {_format_amount(unmatched_amount_sum)} €.',
            f'The unmatched items total €{_format_amount_en(unmatched_amount_sum)}.',
        ),
        _flag_ambiguous(_number_field(
            'largest_unmatched_amount',
            {'de': 'Größter nicht abgeglichener Einzelposten (€)', 'en': 'Largest single unmatched item (€)'},
            '€', largest_unmatched_amount, 0.5,
            f'Der größte nicht abgeglichene Einzelposten beträgt {_format_amount(largest_unmatched_amount)} €.',
            f'The largest single unmatched item is €{_format_amount_en(largest_unmatched_amount)}.',
        ), largest_unmatched_is_unique),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


TASK_CHALLENGE_PROMPTS = build_task_challenge_prompts(
    MIN_ROWS,
    MAX_ROWS,
    MIN_INVOICES,
    MAX_INVOICES,
)

# Preserve the previous module-level names for imports outside this module.
BULK_CATEGORIZATION_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_BULK_CATEGORIZATION]
PLAN_ACTUAL_DEVIATION_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_PLAN_ACTUAL_DEVIATION]
DUPLICATE_PAYMENT_HUNT_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_DUPLICATE_PAYMENT_HUNT]
INVOICE_EXTRACTION_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_INVOICE_EXTRACTION]
POLICY_VIOLATION_CHECK_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_POLICY_VIOLATION_CHECK]
RECEIVABLES_AGING_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_RECEIVABLES_AGING]
VAT_RATE_AUDIT_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_VAT_RATE_AUDIT]
BANK_RECONCILIATION_PROMPT = TASK_CHALLENGE_PROMPTS[TYPE_BANK_RECONCILIATION]

TASK_CHALLENGE_VALIDATORS = {
    TYPE_BULK_CATEGORIZATION: _validate_bulk_categorization,
    TYPE_PLAN_ACTUAL_DEVIATION: _validate_plan_actual_deviation,
    TYPE_DUPLICATE_PAYMENT_HUNT: _validate_duplicate_payment_hunt,
    TYPE_INVOICE_EXTRACTION: _validate_invoice_extraction,
    TYPE_POLICY_VIOLATION_CHECK: _validate_policy_violation_check,
    TYPE_RECEIVABLES_AGING: _validate_receivables_aging,
    TYPE_VAT_RATE_AUDIT: _validate_vat_rate_audit,
    TYPE_BANK_RECONCILIATION: _validate_bank_reconciliation,
}

TASK_CHALLENGE_TYPES = list(TASK_CHALLENGE_PROMPTS)


def _validate_difficulty_contract(payload, mission_type, difficulty):
    if difficulty not in DIFFICULTY_POINTS:
        raise AiMissionGenerationError('Unsupported task challenge difficulty')
    if mission_type == TYPE_INVOICE_EXTRACTION:
        expected_items = {'easy': 12, 'medium': 16, 'hard': 20}[difficulty]
        items = payload.get('invoices')
        label = 'invoices'
    else:
        expected_items = {'easy': 24, 'medium': 36, 'hard': 48}[difficulty]
        items = payload.get('rows')
        label = 'rows'
    if not isinstance(items, list):
        raise AiMissionGenerationError(f'AI task challenge is missing its {label}')
    if mission_type in VOLUME_BAND_TYPES:
        # The exact count only exists to make difficulty visible; a learner cannot tell 24 rows
        # from 27. Demanding an exact number made a stray row fail the whole run, so the bands
        # tolerate overshoot while staying far apart between difficulties.
        if not expected_items <= len(items) <= expected_items + VOLUME_BAND_TOLERANCE:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs {expected_items} to '
                f'{expected_items + VOLUME_BAND_TOLERANCE} {label}'
            )
    elif len(items) != expected_items:
        raise AiMissionGenerationError(
            f'AI task challenge difficulty {difficulty} needs exactly {expected_items} {label}'
        )
    if mission_type == TYPE_BULK_CATEGORIZATION:
        expected_categories = {'easy': 3, 'medium': 4, 'hard': 5}[difficulty]
        categories = payload.get('categories_de')
        if not isinstance(categories, list) or len(categories) != expected_categories:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs exactly {expected_categories} categories'
            )
    if mission_type == TYPE_DUPLICATE_PAYMENT_HUNT:
        expected_pairs = {'easy': 3, 'medium': 4, 'hard': 6}[difficulty]
        invoice_counts = {}
        for row in items:
            if isinstance(row, dict):
                invoice_number = row.get('invoice_number')
                invoice_counts[invoice_number] = invoice_counts.get(invoice_number, 0) + 1
        actual_pairs = sum(1 for count in invoice_counts.values() if count == 2)
        if actual_pairs != expected_pairs:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs exactly {expected_pairs} duplicate pairs'
            )
    if mission_type == TYPE_POLICY_VIOLATION_CHECK:
        minimum_violations = {'easy': 4, 'medium': 5, 'hard': 6}[difficulty]
        violations = 0
        for row in items:
            if not isinstance(row, dict):
                continue
            category = row.get('category')
            if category not in POLICY_CATEGORIES:
                raise AiMissionGenerationError('AI task challenge contains an unsupported expense category')
            excess = _policy_excess(
                category,
                _whole_number(row.get('units'), 'units', 1, 12),
                _amount(row.get('amount'), 'amount'),
            )
            if excess > 0:
                violations += 1
        if violations < minimum_violations:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs at least {minimum_violations} policy violations'
            )
    if mission_type == TYPE_RECEIVABLES_AGING:
        minimum_over_60 = {'easy': 3, 'medium': 4, 'hard': 5}[difficulty]
        reference_date = _iso_date(payload.get('reference_date'), 'reference_date')
        over_60 = 0
        for row in items:
            if not isinstance(row, dict):
                continue
            invoice_date = _iso_date(row.get('invoice_date'), 'invoice_date')
            term_days = _whole_number(row.get('term_days'), 'term_days', 0, 90)
            if (reference_date - invoice_date).days - term_days > 60:
                over_60 += 1
        if over_60 < minimum_over_60:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs at least {minimum_over_60} invoices over 60 days overdue'
            )
    if mission_type == TYPE_VAT_RATE_AUDIT:
        minimum_wrong = {'easy': 3, 'medium': 4, 'hard': 5}[difficulty]
        wrong_lines = 0
        for row in items:
            if not isinstance(row, dict):
                continue
            if row.get('category') not in VAT_RATES:
                raise AiMissionGenerationError('AI task challenge contains an unsupported VAT category')
            if _whole_number(row.get('booked_rate'), 'booked_rate', 7, 19) != VAT_RATES[row['category']]:
                wrong_lines += 1
        if wrong_lines < minimum_wrong:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs at least {minimum_wrong} incorrect VAT lines'
            )
    if mission_type == TYPE_BANK_RECONCILIATION:
        minimum_bank_only, minimum_ledger_only = {'easy': (2, 1), 'medium': (3, 1), 'hard': (3, 2)}[difficulty]
        documents = {'bank': set(), 'ledger': set()}
        for row in items:
            if not isinstance(row, dict):
                continue
            if row.get('source') not in documents:
                raise AiMissionGenerationError('AI task challenge row source must be bank or ledger')
            documents[row['source']].add(row.get('document'))
        bank_only = len(documents['bank'] - documents['ledger'])
        ledger_only = len(documents['ledger'] - documents['bank'])
        if bank_only < minimum_bank_only or ledger_only < minimum_ledger_only:
            raise AiMissionGenerationError(
                f'AI task challenge difficulty {difficulty} needs at least {minimum_bank_only} bank-only and '
                f'{minimum_ledger_only} ledger-only items'
            )
    if mission_type == TYPE_PLAN_ACTUAL_DEVIATION and difficulty == 'hard':
        underruns = sum(
            1 for row in items
            if isinstance(row, dict) and _amount(row.get('actual'), 'actual') < _amount(row.get('plan'), 'plan')
        )
        if underruns < 6:
            raise AiMissionGenerationError('AI hard task challenge needs at least 6 cost centers below plan')


def _task_instruction(payload, mission_type, difficulty):
    if difficulty is None:
        return _bilingual(payload, 'task', 'task')
    if mission_type == TYPE_BULK_CATEGORIZATION:
        categories_de = ', '.join(_text(value, 'category_de') for value in payload.get('categories_de', []))
        categories_en = ', '.join(_text(value, 'category_en') for value in payload.get('categories_en', []))
        return {
            'de': (
                f'Ordnen Sie jede Zeile genau einmal einer dieser Kategorien zu: {categories_de}. '
                'Berichten Sie anschließend die Gesamtsumme für jede Kategorie.'
            ),
            'en': (
                f'Assign every row exactly once to one of these categories: {categories_en}. '
                'Then report the total for every category.'
            ),
        }
    if mission_type == TYPE_PLAN_ACTUAL_DEVIATION:
        instructions = {
            'easy': {
                'de': 'Berechnen Sie die Summe aller positiven Überschreitungen und die Anzahl der Kostenstellen, die mehr als 10 % über Plan liegen.',
                'en': 'Calculate the total of all positive overruns and the number of cost centers more than 10% over plan.',
            },
            'medium': {
                'de': 'Berechnen Sie die Summe aller positiven Überschreitungen, die Anzahl der Kostenstellen über 10 % und die größte positive Einzelabweichung.',
                'en': 'Calculate total positive overruns, the count of cost centers over 10%, and the largest positive deviation.',
            },
            'hard': {
                'de': 'Berechnen Sie die Summe aller positiven Überschreitungen, die Anzahl über 10 %, die größte und die durchschnittliche positive Überschreitung sowie die Summe aller absoluten Unterschreitungen.',
                'en': 'Calculate total positive overruns, the count over 10%, the largest and average positive overrun, and the absolute total of all underruns.',
            },
        }
        return instructions[difficulty]
    if mission_type == TYPE_DUPLICATE_PAYMENT_HUNT:
        instructions = {
            'easy': {
                'de': 'Ermitteln Sie die Anzahl der Doppelzahlungspaare anhand gleicher Rechnungsnummer und gleichen Betrags.',
                'en': 'Determine the number of duplicate-payment pairs using matching invoice numbers and amounts.',
            },
            'medium': {
                'de': 'Ermitteln Sie die Anzahl der Doppelzahlungspaare und die Summe des Doppelzahlungsrisikos.',
                'en': 'Determine the number of duplicate-payment pairs and the total duplicate-payment risk.',
            },
            'hard': {
                'de': 'Ermitteln Sie die Anzahl der Doppelzahlungspaare, die Summe des Doppelzahlungsrisikos und den größten einzelnen Doppelzahlungsbetrag.',
                'en': 'Determine the number of duplicate-payment pairs, total duplicate-payment risk, and largest single duplicate-payment amount.',
            },
        }
        return instructions[difficulty]
    if mission_type == TYPE_POLICY_VIOLATION_CHECK:
        # The rule set lives in Python, so the learner-facing text has to restate it verbatim.
        preamble = {
            'de': (
                'Prüfen Sie die Spesenzeilen gegen diese Richtlinie: Hotel höchstens 150 € pro Nacht, Bewirtung '
                'höchstens 60 € pro Person, Taxi erst ab 2 km erstattungsfähig (darunter ist der volle Betrag nicht '
                'erstattungsfähig). Bei Hotel und Bewirtung ist nur der Betrag oberhalb der Grenze nicht '
                'erstattungsfähig. Alle übrigen Positionen sind zulässig. '
            ),
            'en': (
                'Check the expense lines against this policy: hotel at most €150 per night, client hospitality at '
                'most €60 per guest, taxi only reimbursable from 2 km (below that the full amount is '
                'non-reimbursable). For hotel and hospitality only the amount above the limit is non-reimbursable. '
                'All other lines are compliant. '
            ),
        }
        requests = {
            'easy': {
                'de': 'Ermitteln Sie die Anzahl der Regelverstöße und den gesamten nicht erstattungsfähigen Betrag.',
                'en': 'Determine the number of policy violations and the total non-reimbursable amount.',
            },
            'medium': {
                'de': 'Ermitteln Sie die Anzahl der Regelverstöße, den gesamten nicht erstattungsfähigen Betrag und den größten Einzelverstoß.',
                'en': 'Determine the number of violations, the total non-reimbursable amount, and the largest single violation.',
            },
            'hard': {
                'de': 'Ermitteln Sie die Anzahl der Regelverstöße, den gesamten nicht erstattungsfähigen Betrag, den größten Einzelverstoß und die am häufigsten verletzte Regel (Hotel, Bewirtung oder Taxi).',
                'en': 'Determine the number of violations, the total non-reimbursable amount, the largest single violation, and the rule broken most often (Hotel, Hospitality or Taxi).',
            },
        }
        return {language: preamble[language] + requests[difficulty][language] for language in ('de', 'en')}
    if mission_type == TYPE_RECEIVABLES_AGING:
        reference_date = _text(payload.get('reference_date'), 'reference_date')
        preamble = {
            'de': (
                f'Stichtag der Auswertung ist der {reference_date}. Leiten Sie die Fälligkeit jeder Rechnung aus '
                'Rechnungsdatum und Zahlungsziel ab. Überfällig ist eine Rechnung, deren Fälligkeit vor dem Stichtag '
                'liegt. '
            ),
            'en': (
                f'The cut-off date for the analysis is {reference_date}. Derive each due date from the invoice date '
                'and the payment term. An invoice is overdue when its due date lies before the cut-off date. '
            ),
        }
        requests = {
            'easy': {
                'de': 'Ermitteln Sie die Summe aller überfälligen Beträge und die Anzahl der Rechnungen, die mehr als 60 Tage überfällig sind.',
                'en': 'Determine the total overdue amount and the number of invoices more than 60 days overdue.',
            },
            'medium': {
                'de': 'Ermitteln Sie die Summe aller überfälligen Beträge, die Anzahl der Rechnungen über 60 Tage und deren Summe.',
                'en': 'Determine the total overdue amount, the number of invoices more than 60 days overdue, and their total.',
            },
            'hard': {
                'de': 'Ermitteln Sie die Summe aller überfälligen Beträge, die Anzahl der Rechnungen über 60 Tage, deren Summe und die Rechnungsnummer mit den meisten Überfälligkeitstagen.',
                'en': 'Determine the total overdue amount, the number of invoices more than 60 days overdue, their total, and the invoice number with the most days overdue.',
            },
        }
        return {language: preamble[language] + requests[difficulty][language] for language in ('de', 'en')}
    if mission_type == TYPE_VAT_RATE_AUDIT:
        preamble = {
            'de': (
                'Der ermäßigte Satz von 7 % gilt für Bücher, Zeitschriften, Lebensmittel, Hotelübernachtungen und '
                'den öffentlichen Nahverkehr; für alle anderen Leistungen gelten 19 %. Leiten Sie den richtigen Satz '
                'aus der Leistungsbeschreibung ab und vergleichen Sie ihn mit der gebuchten Umsatzsteuer. '
            ),
            'en': (
                'The reduced rate of 7% applies to books, periodicals, groceries, hotel stays and local public '
                'transport; all other services carry 19%. Derive the correct rate from the service description and '
                'compare it against the VAT actually booked. '
            ),
        }
        requests = {
            'easy': {
                'de': 'Ermitteln Sie die Anzahl der fehlerhaft gebuchten Zeilen und die korrekte Gesamt-Umsatzsteuer über alle Zeilen.',
                'en': 'Determine the number of incorrectly booked lines and the correct total VAT across all lines.',
            },
            'medium': {
                'de': 'Ermitteln Sie die Anzahl der fehlerhaften Zeilen, die korrekte Gesamt-Umsatzsteuer und die Summe der absoluten USt-Differenzen.',
                'en': 'Determine the number of incorrect lines, the correct total VAT, and the total absolute VAT difference.',
            },
            'hard': {
                'de': 'Ermitteln Sie die Anzahl der fehlerhaften Zeilen, die korrekte Gesamt-Umsatzsteuer, die Summe der absoluten USt-Differenzen und die größte einzelne USt-Differenz.',
                'en': 'Determine the number of incorrect lines, the correct total VAT, the total absolute VAT difference, and the largest single VAT difference.',
            },
        }
        return {language: preamble[language] + requests[difficulty][language] for language in ('de', 'en')}
    if mission_type == TYPE_BANK_RECONCILIATION:
        preamble = {
            'de': (
                'Ein Posten gilt als abgeglichen, wenn dieselbe Belegnummer mit demselben Betrag im Bankauszug und '
                'in der Buchhaltung vorkommt. Die Bankzeilen nennen die Belegnummer nur im Verwendungszweck. '
            ),
            'en': (
                'An item counts as reconciled when the same document number appears with the same amount in both the '
                'bank statement and the ledger. Bank lines carry the document number only inside the payment '
                'reference. '
            ),
        }
        requests = {
            'easy': {
                'de': 'Ermitteln Sie, wie viele Posten nur im Bankauszug und wie viele nur in der Buchhaltung stehen.',
                'en': 'Determine how many items appear only in the bank statement and how many only in the ledger.',
            },
            'medium': {
                'de': 'Ermitteln Sie die Anzahl der Posten nur im Bankauszug, die Anzahl nur in der Buchhaltung und die Summe aller nicht abgeglichenen Posten.',
                'en': 'Determine the number of bank-only items, the number of ledger-only items, and the total of all unmatched items.',
            },
            'hard': {
                'de': 'Ermitteln Sie die Anzahl der Posten nur im Bankauszug, die Anzahl nur in der Buchhaltung, die Summe aller nicht abgeglichenen Posten und den größten nicht abgeglichenen Einzelposten.',
                'en': 'Determine the number of bank-only items, the number of ledger-only items, the total of all unmatched items, and the largest single unmatched item.',
            },
        }
        return {language: preamble[language] + requests[difficulty][language] for language in ('de', 'en')}
    instructions = {
        'easy': {
            'de': 'Ermitteln Sie die Rechnungsnummer mit dem höchsten Betrag und die Gesamtsumme aller Rechnungen.',
            'en': 'Determine the invoice number with the highest amount and the total across all invoices.',
        },
        'medium': {
            'de': 'Ermitteln Sie die Rechnungsnummer mit dem höchsten Betrag, die Gesamtsumme und den Lieferanten mit dem größten Rechnungsvolumen.',
            'en': 'Determine the highest-amount invoice number, total amount, and vendor with the largest invoice volume.',
        },
        'hard': {
            'de': 'Ermitteln Sie die Rechnungsnummer mit dem höchsten Betrag, Gesamtsumme, Lieferant mit dem größten Volumen und durchschnittlichen Rechnungsbetrag.',
            'en': 'Determine the highest-amount invoice number, total amount, vendor with the largest volume, and average invoice amount.',
        },
    }
    return instructions[difficulty]


def _result_fields_for_difficulty(result_fields, mission_type, difficulty):
    if mission_type == TYPE_BULK_CATEGORIZATION:
        return result_fields
    field_ids = (
        DIFFICULTY_RESULT_FIELD_IDS[mission_type][difficulty]
        if difficulty is not None
        else DEFAULT_RESULT_FIELD_IDS[mission_type]
    )
    by_id = {field['id']: field for field in result_fields}
    try:
        return [by_id[field_id] for field_id in field_ids]
    except KeyError as exception:
        raise AiMissionGenerationError('Task challenge result-field contract is incomplete') from exception


def validate_task_challenge(payload, mission_type, difficulty=None):
    if not isinstance(payload, dict):
        raise AiMissionGenerationError('AI task challenge is invalid')
    if mission_type not in TASK_CHALLENGE_VALIDATORS:
        raise AiMissionGenerationError('Unsupported task challenge type')
    if difficulty is not None:
        _validate_difficulty_contract(payload, mission_type, difficulty)
    case_data, result_fields, case_format = TASK_CHALLENGE_VALIDATORS[mission_type](payload)
    result_fields = _result_fields_for_difficulty(result_fields, mission_type, difficulty)
    # A tie only matters for a field this difficulty actually asks for. Enforcing it on the
    # full field set rejected easy variants over answers they never request.
    for field in result_fields:
        if field.pop('ambiguous', False):
            raise AiMissionGenerationError(
                f'AI task challenge result {field["id"]} has no unique answer'
            )
    content = {
        'task': _task_instruction(payload, mission_type, difficulty),
        'case_data': case_data,
        'case_format': case_format,
        'result_fields': result_fields,
        'micro_learning': _bilingual(payload, 'micro_learning', 'micro_learning'),
    }
    return {
        'mission_type': mission_type,
        'title_de': _text(payload.get('title_de'), 'title_de'),
        'title_en': _text(payload.get('title_en'), 'title_en'),
        'description_de': _text(payload.get('description_de'), 'description_de'),
        'description_en': _text(payload.get('description_en'), 'description_en'),
        'max_points': DIFFICULTY_POINTS.get(difficulty, DEFAULT_POINTS),
        'content': content,
    }


def generate_task_challenge(mission_type=None, difficulty=None):
    mission_type = mission_type or random.choice(TASK_CHALLENGE_TYPES)
    if mission_type not in TASK_CHALLENGE_PROMPTS:
        raise AiMissionGenerationError('Unsupported task challenge type')
    difficulty_instruction = build_difficulty_instruction(mission_type, difficulty) if difficulty else ''
    payload = extract_json(_completion([
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': f'{TASK_CHALLENGE_PROMPTS[mission_type]}\n\n{difficulty_instruction}'},
    ], json_mode=True, temperature=0.5, max_tokens=GENERATION_MAX_TOKENS))
    return validate_task_challenge(payload, mission_type, difficulty=difficulty)


def generate_task_challenge_variants(mission_type=None):
    mission_type = mission_type or random.choice(TASK_CHALLENGE_TYPES)
    variants = {
        difficulty: generate_task_challenge(mission_type, difficulty=difficulty)
        for difficulty in ('easy', 'medium', 'hard')
    }
    easy = variants['easy']
    return {
        **easy,
        **TASK_TOPICS[mission_type],
        'variants': {
            difficulty: {
                'title_de': candidate['title_de'],
                'title_en': candidate['title_en'],
                'description_de': candidate['description_de'],
                'description_en': candidate['description_en'],
                'max_points': candidate['max_points'],
                'content': candidate['content'],
            }
            for difficulty, candidate in variants.items()
        },
    }


def public_content(content, language):
    language = 'en' if language == 'en' else 'de'
    return {
        'question': content['task'][language],
        'task': content['task'][language],
        'case_data': content['case_data'][language],
        'case_format': content.get('case_format', 'table'),
        'result_fields': [
            {
                'id': field['id'],
                'type': field['type'],
                'label': field['label'][language],
                'unit': field.get('unit', ''),
            }
            for field in content['result_fields']
        ],
    }


def evaluate_task_answers(content, values, language):
    language = 'en' if language == 'en' else 'de'
    fields = content['result_fields']
    field_results = []
    correct_count = 0
    for field in fields:
        raw = values.get(field['id'])
        if field['type'] == 'number':
            try:
                correct = abs(float(raw) - float(field['solution'])) <= float(field.get('tolerance', 0))
            except (TypeError, ValueError):
                correct = False
            solution_value = field['solution']
        else:
            solution = field['solution']
            expected = solution.get(language) if isinstance(solution, dict) else solution
            normalized_raw = _normalize_text_answer(raw)
            correct = bool(normalized_raw) and normalized_raw == _normalize_text_answer(expected)
            solution_value = expected
        if correct:
            correct_count += 1
        field_results.append({
            'id': field['id'],
            'correct': correct,
            'solution': solution_value,
            'feedback': field['feedback'][language],
        })
    total = len(fields)
    return {
        'correct_count': correct_count,
        'total_count': total,
        'all_correct': correct_count == total,
        'field_results': field_results,
    }
