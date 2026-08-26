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

DEFAULT_POINTS = 40
MIN_ROWS = 24
MAX_ROWS = 60
MIN_INVOICES = 12
MAX_INVOICES = 20

DIFFICULTY_POINTS = {'easy': 30, 'medium': 40, 'hard': 50}
DEFAULT_RESULT_FIELD_IDS = {
    TYPE_PLAN_ACTUAL_DEVIATION: ('total_overrun', 'count_over_threshold', 'max_deviation'),
    TYPE_DUPLICATE_PAYMENT_HUNT: ('duplicate_pairs_count', 'risk_amount_sum'),
    TYPE_INVOICE_EXTRACTION: ('top_invoice_number', 'top_vendor', 'total_amount'),
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

TASK_CHALLENGE_VALIDATORS = {
    TYPE_BULK_CATEGORIZATION: _validate_bulk_categorization,
    TYPE_PLAN_ACTUAL_DEVIATION: _validate_plan_actual_deviation,
    TYPE_DUPLICATE_PAYMENT_HUNT: _validate_duplicate_payment_hunt,
    TYPE_INVOICE_EXTRACTION: _validate_invoice_extraction,
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
    if not isinstance(items, list) or len(items) != expected_items:
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
    ], json_mode=True, temperature=0.5, max_tokens=4500))
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
