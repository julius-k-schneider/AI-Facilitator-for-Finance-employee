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

SYSTEM_PROMPT = """You design a realistic, hands-on finance work task for an experienced accountant or controller.
The learner solves the task OUTSIDE this app with their own tools (Excel) and an external AI assistant such as
Microsoft Copilot or ChatGPT, then returns only the final result values. The point of the exercise is that the
data volume makes manual work tedious, so using AI is the natural, faster path.
Return compact valid JSON only, no markdown, no commentary. Everything must be bilingual in natural German and English.
Never use or invent real personal, customer, Lufthansa-internal, SAP, or confidential data. Use plausible fictional
company names and figures."""


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise AiMissionGenerationError(f'AI task challenge field {field} is invalid')
    return value.strip()


def _format_amount(amount):
    # German number format (period thousands, comma decimal) so pasted case data is
    # recognized as a real number in a German-locale Excel, not as text.
    return f'{amount:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


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


# ---------------------------------------------------------------------------
# bulk_categorization: assign each booking line to a category, report totals.
# ---------------------------------------------------------------------------

BULK_CATEGORIZATION_PROMPT = f"""Create one "bulk categorization" finance task.

Scenario: the learner receives a long list of {MIN_ROWS}-{MAX_ROWS} booking lines (fictional) and must assign each line
to exactly one cost category based on its description, then report the total amount per category.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"clear instruction: categorize every line and report the total per category", "task_en":"...",
  "categories_de":["Reisekosten","Bürobedarf","IT und Software","Marketing"],
  "categories_en":["Travel","Office supplies","IT and software","Marketing"],
  "rows":[
    {{"date":"2026-03-01","description_de":"Bahnticket Projektreise München","description_en":"Train ticket project trip Munich","amount":124.50,"category_index":0}},
    {{"date":"2026-03-02","description_de":"Druckerpapier Bürobedarf","description_en":"Printer paper office supplies","amount":38.90,"category_index":1}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to categorize bulk finance data and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide 3 or 4 categories. categories_de and categories_en must have equal length.
- Provide between {MIN_ROWS} and {MAX_ROWS} rows. Every row needs date (YYYY-MM-DD), a bilingual description, a positive
  amount (number, max 2 decimals), and a category_index that is a valid zero-based index into the categories.
- Each description must map UNAMBIGUOUSLY to exactly one category for a finance professional. No trick lines.
- Spread the rows across all categories; every category must have at least three rows.
- Keep descriptions short (under 90 characters) and business-like."""


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
        formatted = _format_amount(amount)
        case_de.append(f'{date} | {formatted} € | {description_de}')
        case_en.append(f'{date} | {formatted} € | {description_en}')

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
            f'The correct total for {category["en"]} is {_format_amount(total)} €.',
        ))

    return {'de': case_de, 'en': case_en}, result_fields, 'table'


# ---------------------------------------------------------------------------
# plan_actual_deviation: find cost centers that overran their budget.
# ---------------------------------------------------------------------------

PLAN_ACTUAL_DEVIATION_PROMPT = f"""Create one "plan vs. actual deviation" finance task.

Scenario: the learner receives a long list of {MIN_ROWS}-{MAX_ROWS} fictional cost centers, each with a planned
(budget) amount and an actual (Ist) amount for the period, and must find which cost centers overran their budget.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"clear instruction: find cost centers that exceeded plan and report the requested totals", "task_en":"...",
  "rows":[
    {{"cost_center_de":"Marketing DACH","cost_center_en":"Marketing DACH","plan":12000.00,"actual":13850.00}},
    {{"cost_center_de":"IT Infrastruktur","cost_center_en":"IT infrastructure","plan":9000.00,"actual":8600.00}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to spot budget overruns across many cost centers and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide between {MIN_ROWS} and {MAX_ROWS} rows, each a distinct, plausible cost center name (bilingual).
- plan must be a positive number (max 2 decimals). actual must be a positive number (max 2 decimals).
- At least 8 rows must overrun their plan (actual > plan), and at least 4 of those must overrun by more than 10%,
  so there is a clear, non-trivial answer.
- Keep the mix realistic: most cost centers should be close to plan, a minority clearly over."""


def _validate_plan_actual_deviation(payload):
    rows = payload.get('rows')
    if not isinstance(rows, list) or not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise AiMissionGenerationError(f'AI task challenge needs {MIN_ROWS}-{MAX_ROWS} rows')

    case_de = []
    case_en = []
    total_overrun = 0.0
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
            if deviation / plan > 0.10:
                over_threshold += 1
        if max_deviation is None or deviation > max_deviation:
            max_deviation = deviation
        plan_fmt = _format_amount(plan)
        actual_fmt = _format_amount(actual)
        case_de.append(f'{name_de} | Plan {plan_fmt} € | Ist {actual_fmt} €')
        case_en.append(f'{name_en} | Plan {plan_fmt} € | Actual {actual_fmt} €')

    if over_threshold < 4:
        raise AiMissionGenerationError('AI task challenge needs at least 4 cost centers overrunning plan by more than 10%')

    total_overrun = round(total_overrun, 2)
    max_deviation = round(max_deviation, 2)
    result_fields = [
        _number_field(
            'total_overrun', {'de': 'Summe der Budgetüberschreitungen (€)', 'en': 'Total budget overruns (€)'},
            '€', total_overrun, 0.5,
            f'Die Summe aller Überschreitungen beträgt {_format_amount(total_overrun)} €.',
            f'The total of all overruns is {_format_amount(total_overrun)} €.',
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
            f'The largest single deviation is {_format_amount(max_deviation)} €.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


# ---------------------------------------------------------------------------
# duplicate_payment_hunt: find accidental double payments in a creditor run.
# ---------------------------------------------------------------------------

DUPLICATE_PAYMENT_HUNT_PROMPT = f"""Create one "duplicate payment hunt" finance task.

Scenario: the learner receives a long fictional accounts-payable run of {MIN_ROWS}-{MAX_ROWS} payment lines. A few
invoices were accidentally entered and paid twice (same invoice number, same amount, but the vendor name is spelled
slightly differently between the two entries, e.g. "Müller GmbH" vs. "Mueller GmbH", so a simple visual scan misses it).
The learner must find the duplicate payments.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"clear instruction: find duplicate payments (same invoice paid twice) and report count and risk amount", "task_en":"...",
  "rows":[
    {{"date":"2026-03-01","vendor_de":"Müller GmbH","vendor_en":"Mueller GmbH","invoice_number":"RE-8841","amount":1240.00}},
    {{"date":"2026-03-14","vendor_de":"Mueller GmbH","vendor_en":"Mueller GmbH","invoice_number":"RE-8841","amount":1240.00}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to find duplicate payments across a large payment run and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide between {MIN_ROWS} and {MAX_ROWS} rows.
- Every row needs date (YYYY-MM-DD), a bilingual vendor name, an invoice_number (short alphanumeric code), and a
  positive amount (max 2 decimals).
- Create exactly 3 to 6 duplicate PAIRS: for each pair, use the exact SAME invoice_number and the exact SAME amount
  in both rows, but vary the vendor spelling slightly between the two rows of the pair.
- Every other invoice_number must be unique across the whole list (used by exactly one row).
- Do not use more than two rows for the same invoice_number."""


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
        formatted = _format_amount(amount)
        case_de.append(f'{date} | {vendor_de} | Rechnung {invoice_number} | {formatted} €')
        case_en.append(f'{date} | {vendor_en} | Invoice {invoice_number} | {formatted} €')

    duplicate_pairs = 0
    risk_amount = 0.0
    for invoice_number, amounts in by_invoice.items():
        if len(amounts) > 2:
            raise AiMissionGenerationError(f'AI task challenge invoice number {invoice_number} appears more than twice')
        if len(amounts) == 2:
            if abs(amounts[0] - amounts[1]) > 0.01:
                raise AiMissionGenerationError(f'AI task challenge duplicate pair {invoice_number} amounts must match')
            duplicate_pairs += 1
            risk_amount += amounts[1]

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
            f'The duplicate payment risk totals {_format_amount(risk_amount)} €.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'table'


# ---------------------------------------------------------------------------
# invoice_extraction: extract structured facts from free-text invoice blurbs.
# ---------------------------------------------------------------------------

INVOICE_EXTRACTION_PROMPT = f"""Create one "invoice extraction" finance task.

Scenario: the learner receives {MIN_INVOICES}-{MAX_INVOICES} short fictional invoice descriptions written as natural-language
paragraphs (NOT a table) - each paragraph mentions an invoice number, a vendor name, a date, and an amount embedded
in ordinary prose, the way a scanned invoice summary or email might read. The learner must extract the requested
facts across all invoices.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"clear instruction: read every invoice text and extract the requested facts", "task_en":"...",
  "invoices":[
    {{
      "invoice_number":"INV-2941",
      "vendor_de":"Bergmann Bürotechnik GmbH","vendor_en":"Bergmann Office Technology GmbH",
      "date":"2026-02-11","amount":2140.00,
      "text_de":"Bergmann Bürotechnik GmbH stellt mit Rechnung INV-2941 vom 11.02.2026 die Lieferung von zwei Multifunktionsdruckern in Höhe von 2.140,00 € in Rechnung.",
      "text_en":"Bergmann Office Technology GmbH issued invoice INV-2941 dated 2026-02-11 for the delivery of two multifunction printers, amounting to €2,140.00."
    }}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to extract structured facts from unstructured invoice text and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide between {MIN_INVOICES} and {MAX_INVOICES} invoices.
- Each invoice_number must be unique. Amounts must be positive numbers (max 2 decimals).
- At least 3 different vendors must appear more than once (across different invoices) so totals per vendor are
  meaningful to compute.
- text_de and text_en must be 1-3 full sentences of natural prose that contain the invoice number, vendor name,
  date, and amount somewhere in the text - do not format them as a table or list."""


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
            f'The total of all invoices is {_format_amount(total_amount)} €.',
        ),
    ]
    return {'de': case_de, 'en': case_en}, result_fields, 'prose'

TASK_CHALLENGE_PROMPTS = {
    TYPE_BULK_CATEGORIZATION: BULK_CATEGORIZATION_PROMPT,
    TYPE_PLAN_ACTUAL_DEVIATION: PLAN_ACTUAL_DEVIATION_PROMPT,
    TYPE_DUPLICATE_PAYMENT_HUNT: DUPLICATE_PAYMENT_HUNT_PROMPT,
    TYPE_INVOICE_EXTRACTION: INVOICE_EXTRACTION_PROMPT,
}

TASK_CHALLENGE_VALIDATORS = {
    TYPE_BULK_CATEGORIZATION: _validate_bulk_categorization,
    TYPE_PLAN_ACTUAL_DEVIATION: _validate_plan_actual_deviation,
    TYPE_DUPLICATE_PAYMENT_HUNT: _validate_duplicate_payment_hunt,
    TYPE_INVOICE_EXTRACTION: _validate_invoice_extraction,
}

TASK_CHALLENGE_TYPES = list(TASK_CHALLENGE_PROMPTS)


def validate_task_challenge(payload, mission_type):
    if not isinstance(payload, dict):
        raise AiMissionGenerationError('AI task challenge is invalid')
    if mission_type not in TASK_CHALLENGE_VALIDATORS:
        raise AiMissionGenerationError('Unsupported task challenge type')
    case_data, result_fields, case_format = TASK_CHALLENGE_VALIDATORS[mission_type](payload)
    content = {
        'task': _bilingual(payload, 'task', 'task'),
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
        'max_points': DEFAULT_POINTS,
        'content': content,
    }


def generate_task_challenge(mission_type=None):
    mission_type = mission_type or random.choice(TASK_CHALLENGE_TYPES)
    if mission_type not in TASK_CHALLENGE_PROMPTS:
        raise AiMissionGenerationError('Unsupported task challenge type')
    payload = extract_json(_completion([
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': TASK_CHALLENGE_PROMPTS[mission_type]},
    ], json_mode=True, temperature=0.5, max_tokens=4500))
    return validate_task_challenge(payload, mission_type)


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
