"""Prompts for realistic, data-heavy finance task challenges."""


# Difficulty-specific suffixes are appended to one task-type prompt. They are
# separate because task variants are generated with three independent LLM calls.
DIFFICULTY_INSTRUCTIONS = {
    'easy': (
        'Difficulty: EASY. Use the smallest specified data volume and the fewest specified result values. Give a '
        'short step-by-step instruction suitable for basic AI prompting skills.'
    ),
    'medium': (
        'Difficulty: MEDIUM. Use the specified medium data volume and add one meaningful result requirement. Require '
        'independent reasoning, a structured result, and precise prompting.'
    ),
    'hard': (
        'Difficulty: HARD. Use the largest specified data volume and all specified result requirements. Require '
        'decomposition, quality control, verification, and a reusable professional approach without ambiguous grading.'
    ),
}


TASK_DIFFICULTY_CONTRACTS = {
    'bulk_categorization': {
        'easy': 'Use exactly 3 categories and exactly 24 rows. Request one total for each of the 3 categories.',
        'medium': 'Use exactly 4 categories and exactly 36 rows. Request one total for each of the 4 categories.',
        'hard': 'Use exactly 5 categories and exactly 48 rows. Request one total for each of the 5 categories.',
    },
    'plan_actual_deviation': {
        'easy': (
            'Use exactly 24 rows. Request only: (1) total positive overrun and (2) count of cost centers more than '
            '10 percent over plan.'
        ),
        'medium': (
            'Use exactly 36 rows. Request the two EASY results plus (3) largest positive deviation amount.'
        ),
        'hard': (
            'Use exactly 48 rows. Request the three MEDIUM results plus (4) average positive overrun and '
            '(5) total absolute amount of all underruns. Include at least 6 cost centers below plan. '
            'Do not request cost-center names or any other result.'
        ),
    },
    'duplicate_payment_hunt': {
        'easy': 'Use exactly 24 rows with exactly 3 duplicate pairs. Request only the number of duplicate pairs.',
        'medium': (
            'Use exactly 36 rows with exactly 4 duplicate pairs. Request (1) pair count and '
            '(2) total duplicate-payment risk amount.'
        ),
        'hard': (
            'Use exactly 48 rows with exactly 6 duplicate pairs. Request the two MEDIUM results plus '
            '(3) largest single duplicate-payment amount. Do not request invoice or vendor lists.'
        ),
    },
    'invoice_extraction': {
        'easy': (
            'Use exactly 12 invoices. Request only (1) invoice number with the highest amount and '
            '(2) total amount across all invoices.'
        ),
        'medium': (
            'Use exactly 16 invoices. Request the two EASY results plus '
            '(3) vendor with the largest summed invoice volume.'
        ),
        'hard': (
            'Use exactly 20 invoices. Request the three MEDIUM results plus (4) average invoice amount.'
        ),
    },
    'policy_violation_check': {
        'easy': (
            'Use exactly 24 rows. At least 4 of them must break a rule, spread over at least two different '
            'rules. Request only: (1) number of violations and (2) total non-reimbursable amount.'
        ),
        'medium': (
            'Use exactly 36 rows. At least 5 of them must break a rule, spread over at least two different '
            'rules. Request the two EASY results plus (3) largest single non-reimbursable amount.'
        ),
        'hard': (
            'Use exactly 48 rows. At least 6 of them must break a rule, spread over at least two different '
            'rules, and one single rule must be broken more often than every other rule. Request the three MEDIUM '
            'results plus (4) the rule that was broken most often.'
        ),
    },
    'receivables_aging': {
        'easy': (
            'Use exactly 24 rows, at least 3 of them more than 60 days overdue. Request only: (1) total '
            'overdue amount and (2) number of invoices more than 60 days overdue.'
        ),
        'medium': (
            'Use exactly 36 rows, at least 4 of them more than 60 days overdue. Request the two EASY results '
            'plus (3) total amount more than 60 days overdue.'
        ),
        'hard': (
            'Use exactly 48 rows, at least 5 of them more than 60 days overdue. Request the three MEDIUM '
            'results plus (4) the invoice number with the most days overdue.'
        ),
    },
    'vat_rate_audit': {
        'easy': (
            'Use exactly 24 rows, at least 3 of them booked with the wrong VAT rate. Request only: '
            '(1) number of incorrect lines and (2) correct total VAT across all lines.'
        ),
        'medium': (
            'Use exactly 36 rows, at least 4 of them booked with the wrong VAT rate. Request the two EASY '
            'results plus (3) total absolute VAT difference.'
        ),
        'hard': (
            'Use exactly 48 rows, at least 5 of them booked with the wrong VAT rate. Request the three '
            'MEDIUM results plus (4) largest single VAT difference.'
        ),
    },
    'bank_reconciliation': {
        'easy': (
            'Return exactly 24 rows in total, counting every bank line and every ledger line as its own '
            'object. At least 2 documents must appear only on the bank side and at least 1 only on the ledger side, '
            'and those two counts must differ. Request only: (1) number of bank-only items and (2) number of '
            'ledger-only items.'
        ),
        'medium': (
            'Return exactly 36 rows in total, counting every bank line and every ledger line as its own '
            'object. At least 3 documents must appear only on the bank side and at least 1 only on the ledger side, '
            'and those two counts must differ. Request the two EASY results plus (3) total amount of all unmatched '
            'items.'
        ),
        'hard': (
            'Return exactly 48 rows in total, counting every bank line and every ledger line as its own '
            'object. At least 3 documents must appear only on the bank side and at least 2 only on the ledger side, '
            'and those two counts must differ. Request the three MEDIUM results plus (4) largest single unmatched '
            'amount.'
        ),
    },
}


def build_difficulty_instruction(mission_type, difficulty):
    try:
        contract = TASK_DIFFICULTY_CONTRACTS[mission_type][difficulty]
        introduction = DIFFICULTY_INSTRUCTIONS[difficulty]
    except KeyError as exception:
        raise ValueError('Unsupported task difficulty contract') from exception
    return (
        f'{introduction}\nDIFFICULTY CONTRACT: {contract}\n'
        'The German and English task texts must request exactly these result values and no others. '
        'The collection array must contain exactly the stated number of objects: no more and no fewer. Stop the array '
        'immediately after the final required object. Before returning, count the data items and requested outputs and '
        'verify that both languages mean the same thing.'
    )


# Shared system policy for all four task types.
SYSTEM_PROMPT = """Reasoning: low.
You design a realistic, hands-on finance work task for an experienced accountant or controller.
The learner solves the task OUTSIDE this app with their own tools (Excel) and an external AI assistant such as
Microsoft Copilot or ChatGPT, then returns only the final result values. The point of the exercise is that the
data volume makes manual work tedious, so using AI is the natural, faster path.
Return compact valid JSON only, no markdown, no commentary. Everything must be bilingual in natural German and English.
Never use or invent real personal, customer, Lufthansa-internal, SAP, or confidential data. Use plausible fictional
company names and figures. The final DIFFICULTY CONTRACT is authoritative: obey its exact item count and request only
its named result values. Difficulty must change workload and result requirements, not merely wording or numbers."""


# Builds prompts with the same row limits that the deterministic Python validators
# enforce. Keeping the limits injected prevents prompt/validator drift.
def build_task_challenge_prompts(min_rows, max_rows, min_invoices, max_invoices):
    # Bulk categorization: classify booking lines and aggregate amounts.
    bulk_categorization = f"""Create one "bulk categorization" finance task.

Scenario: the learner receives a long list of fictional booking lines whose exact size is defined only by the final
DIFFICULTY CONTRACT and must assign each line
to exactly one cost category based on its description, then report the total amount per category.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction matching the appended difficulty contract and explicitly naming every German category",
  "task_en":"equivalent instruction naming every English category",
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
- Provide 3-5 categories as fixed by the appended difficulty contract. categories_de and categories_en must have equal length.
- Provide exactly the row count from the final DIFFICULTY CONTRACT. Every row needs date (YYYY-MM-DD), a bilingual description, a positive
  amount (number, max 2 decimals), and a category_index that is a valid zero-based index into the categories.
- Each description must map UNAMBIGUOUSLY to exactly one category for a finance professional. No trick lines.
- task_de and task_en must explicitly list the generated categories in their matching language.
- Give every row a category-specific cue. Avoid ambiguous items such as generic client meals, furniture, subscriptions,
  or events unless the description itself makes the intended category unmistakable.
- Spread the rows across all categories; every category must have at least three rows.
- Keep descriptions short (under 90 characters) and business-like."""

    # Plan-versus-actual analysis: detect and aggregate budget overruns.
    plan_actual_deviation = f"""Create one "plan vs. actual deviation" finance task.

Scenario: the learner receives a long list of fictional cost centers whose exact size is defined only by the final
DIFFICULTY CONTRACT, each with a planned
(budget) amount and an actual (Ist) amount for the period, and must find which cost centers overran their budget.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract",
  "task_en":"equivalent instruction requesting exactly those results in English",
  "rows":[
    {{"cost_center_de":"Marketing DACH","cost_center_en":"Marketing DACH","plan":12000.00,"actual":13850.00}},
    {{"cost_center_de":"IT Infrastruktur","cost_center_en":"IT infrastructure","plan":9000.00,"actual":8600.00}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to spot budget overruns across many cost centers and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide exactly the row count from the final DIFFICULTY CONTRACT, each with a distinct, plausible cost center name (bilingual).
- plan must be a positive number (max 2 decimals). actual must be a positive number (max 2 decimals).
- At least 8 rows must overrun their plan (actual > plan), and at least 4 of those must overrun by more than 10%,
  so there is a clear, non-trivial answer.
- Request only the results named by the appended difficulty contract. Never invent additional KPIs.
- Keep the mix realistic: most cost centers should be close to plan, a minority clearly over."""

    # Duplicate-payment hunt: identify pairs despite spelling variations.
    duplicate_payment_hunt = f"""Create one "duplicate payment hunt" finance task.

Scenario: the learner receives a long fictional accounts-payable run whose exact row count is defined only by the final
DIFFICULTY CONTRACT. A few
invoices were accidentally entered and paid twice (same invoice number, same amount, but the vendor name is spelled
slightly differently between the two entries, e.g. "Müller GmbH" vs. "Mueller GmbH", so a simple visual scan misses it).
The learner must find the duplicate payments.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
  "rows":[
    {{"date":"2026-03-01","vendor_de":"Müller GmbH","vendor_en":"Mueller GmbH","invoice_number":"RE-8841","amount":1240.00}},
    {{"date":"2026-03-14","vendor_de":"Mueller GmbH","vendor_en":"Mueller GmbH","invoice_number":"RE-8841","amount":1240.00}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about using AI to find duplicate payments across a large payment run and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Provide exactly the row count from the final DIFFICULTY CONTRACT.
- Every row needs date (YYYY-MM-DD), a bilingual vendor name, an invoice_number (short alphanumeric code), and a
  positive amount (max 2 decimals).
- Create exactly 3 to 6 duplicate PAIRS: for each pair, use the exact SAME invoice_number and the exact SAME amount
  in both rows, but vary the vendor spelling slightly between the two rows of the pair.
- Every other invoice_number must be unique across the whole list (used by exactly one row).
- Do not use more than two rows for the same invoice_number.
- Request only the results named by the appended difficulty contract. Do not request vendor names, invoice lists, or
  other fields. Keep amounts as JSON numbers; presentation handles locale formatting."""

    # Invoice extraction: convert unstructured invoice prose into structured facts.
    invoice_extraction = f"""Create one "invoice extraction" finance task.

Scenario: the learner receives the exact number of short fictional invoice descriptions defined only by the final
DIFFICULTY CONTRACT, written as natural-language
paragraphs (NOT a table) - each paragraph mentions an invoice number, a vendor name, a date, and an amount embedded
in ordinary prose, the way a scanned invoice summary or email might read. The learner must extract the requested
facts across all invoices.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
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
- Provide exactly the invoice count from the final DIFFICULTY CONTRACT.
- Each invoice_number must be unique. Amounts must be positive numbers (max 2 decimals).
- At least 3 different vendors must appear more than once (across different invoices) so totals per vendor are
  meaningful to compute.
- Request only the results named by the appended difficulty contract. Never invent additional KPIs.
- text_de and text_en must be 1-3 full sentences of natural prose that contain the invoice number, vendor name,
  date, and amount somewhere in the text - do not format them as a table or list."""

    # Travel-policy check: apply a stated rule set to free-text expense lines.
    policy_violation_check = f"""Create one "travel policy violation check" finance task.

Scenario: the learner receives {min_rows}-{max_rows} fictional expense lines. Each line describes the expense in
ordinary prose, and the facts needed to apply the policy (number of guests, number of nights, distance in km) appear
ONLY inside that prose - never as a separate column. The learner must apply this fixed policy:
- Hotel: at most 150 EUR per night
- Client hospitality: at most 60 EUR per guest
- Taxi: only reimbursable from 2 km travelled; below that the full amount is non-reimbursable
Anything else is always compliant. For hotel and hospitality, only the amount ABOVE the limit is non-reimbursable.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
  "rows":[
    {{"index":1,"date":"2026-03-04","employee_de":"M. Vogel","employee_en":"M. Vogel","category":"hospitality","units":3,"amount":214.00,
      "description_de":"Abendessen mit 3 Kunden im Restaurant Vitali","description_en":"Dinner with 3 clients at Restaurant Vitali"}},
    {{"index":2,"date":"2026-03-05","employee_de":"S. Krause","employee_en":"S. Krause","category":"hotel","units":2,"amount":280.00,
      "description_de":"Hotel Rheinblick, 2 Naechte waehrend des Audits","description_en":"Hotel Rheinblick, 2 nights during the audit"}},
    {{"index":3,"date":"2026-03-06","employee_de":"S. Krause","employee_en":"S. Krause","category":"other","units":1,"amount":48.00,
      "description_de":"Bahnticket zweiter Klasse nach Koeln","description_en":"Second class train ticket to Cologne"}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about handing a rule set to AI and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Return the data array under the JSON key "rows" exactly as shown above and never rename it.
- Provide exactly as many rows as the appended difficulty contract names - no more, no fewer.
- Number every row consecutively in an "index" field starting at 1. The index of the last row must equal the
  row count the contract names - count with it and check yourself before returning.
- category must be exactly one of "hotel", "hospitality", "taxi", "other".
- units is the number of nights (hotel), the number of guests (hospitality), or the whole kilometres travelled (taxi).
  Use 1 for category "other". units must be a whole number between 1 and 12.
- The SAME number must appear as a digit inside description_de and description_en for hotel, hospitality and taxi rows
  (for example "3 Kunden" / "3 clients", "2 Naechte" / "2 nights", "1 km"). Never spell the number out as a word.
- Each row may break at most one rule. Keep "other" rows clearly compliant and never mention nights, guests or km in them.
- Meet at least the number of violations named by the appended difficulty contract, spread over at least two
  different categories. All remaining rows must be comfortably within the limits, not borderline.
- Vary the violation amounts so that no two violations exceed their limit by the same amount.
- Never state in the description whether a line is compliant. The learner must derive that from the policy."""

    # Receivables aging: parse a natural-language payment term, then compute days overdue.
    receivables_aging = f"""Create one "receivables aging" finance task.

Scenario: the learner receives {min_rows}-{max_rows} fictional open customer invoices. Each invoice shows its invoice
date and its payment term written in ordinary business language ("30 Tage netto", "sofort faellig",
"14 Tage abzueglich 2% Skonto"), never as a due date. The learner must derive the due date, compare it against the
reference date, and bucket the invoices by days overdue.

Return exactly this JSON structure:
{{
  "reference_date":"2026-04-30",
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
  "rows":[
    {{"index":1,"invoice_number":"RE-2211","customer_de":"Brandt Logistik GmbH","customer_en":"Brandt Logistics GmbH",
      "invoice_date":"2026-01-15","term_days":30,"term_de":"30 Tage netto","term_en":"30 days net","amount":4200.00}},
    {{"index":2,"invoice_number":"RE-2288","customer_de":"Seiler Anlagenbau AG","customer_en":"Seiler Plant Engineering AG",
      "invoice_date":"2026-04-20","term_days":0,"term_de":"sofort faellig","term_en":"due immediately","amount":880.00}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about letting AI derive due dates from written payment terms and verifying its output",
  "micro_learning_en":"..."
}}

Rules:
- Return the data array under the JSON key "rows" exactly as shown above and never rename it.
- Provide exactly as many rows as the appended difficulty contract names - no more, no fewer.
- Number every row consecutively in an "index" field starting at 1. The index of the last row must equal the
  row count the contract names - count with it and check yourself before returning.
- Every invoice_number must be unique.
- reference_date is the cut-off date for the whole analysis and must be stated in task_de and task_en.
- term_days must be a whole number between 0 and 90 and must match the wording of term_de and term_en exactly.
  Whenever term_days is greater than 0, that same number must appear as a digit in both term texts.
- invoice_date must be a real date before reference_date. Amounts must be positive numbers (max 2 decimals).
- No invoice may become due exactly on the reference date, so "overdue" is never ambiguous.
- Meet at least the number of invoices more than 60 days overdue named by the appended difficulty contract.
- Include a realistic mix: several invoices not yet due, several a few days overdue, several a few weeks overdue.
- Exactly one invoice must have the highest number of days overdue - no tie for the oldest position."""

    # VAT audit: the correct rate follows from what was bought, described in prose.
    vat_rate_audit = f"""Create one "VAT rate audit" finance task.

Scenario: the learner receives {min_rows}-{max_rows} fictional booking lines. Each line describes in prose what was
bought, plus the net amount and the VAT rate that was actually applied when booking. The correct rate follows from
WHAT was bought: 7% for books, periodicals, groceries, hotel stays and local public transport; 19% for everything
else. On some lines the wrong rate was applied.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
  "rows":[
    {{"index":1,"date":"2026-03-02","category":"books","net":420.00,"booked_rate":19,
      "description_de":"Lieferung von Fachbuechern zum Bilanzrecht","description_en":"Delivery of accounting law textbooks"}},
    {{"index":2,"date":"2026-03-03","category":"consulting","net":1500.00,"booked_rate":19,
      "description_de":"Beratungshonorar Prozessoptimierung","description_en":"Consulting fee for process optimisation"}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about checking VAT rates with AI and verifying its arithmetic",
  "micro_learning_en":"..."
}}

Rules:
- Return the data array under the JSON key "rows" exactly as shown above and never rename it.
- Provide exactly as many rows as the appended difficulty contract names - no more, no fewer.
- Number every row consecutively in an "index" field starting at 1. The index of the last row must equal the
  row count the contract names - count with it and check yourself before returning.
- category must be exactly one of the reduced-rate values
  "books", "periodicals", "groceries", "hotel_stay", "local_transport" or the standard-rate values
  "software", "consulting", "office_supplies", "electronics", "catering_service", "vehicle_rental".
- description_de and description_en must make the category unmistakable to a finance professional. Never name the
  percentage or the word VAT in the description, and never hint that a line is wrong.
- net must be a positive number (max 2 decimals). booked_rate must be the whole number 7 or 19 - never a decimal,
  never a percent sign, never a euro amount. Do NOT calculate any VAT amount; the application derives every figure
  from net and the rate.
- On correct lines booked_rate equals the rate that the category requires. On incorrect lines it is the other rate.
- Meet at least the number of incorrect lines named by the appended difficulty contract, and use both reduced-rate
  and standard-rate categories among them.
- Vary the net amounts so that no two incorrect lines end up with the same VAT difference."""

    # Bank reconciliation: match a free-text bank statement against a structured ledger.
    bank_reconciliation = f"""Create one "bank reconciliation" finance task.

Scenario: the learner receives {min_rows}-{max_rows} fictional lines from two sources in one list. Bank lines carry
only a payment reference written as free text the way a real bank statement reads ("Zahlung Re 8841 Mueller GmbH",
"UEBERWEISUNG RG-2024-113"), while ledger lines carry a clean document number. Most lines match one-to-one across
the two sources; a few exist on only one side. The learner must find the unmatched items.

Return exactly this JSON structure:
{{
  "title_de":"...", "title_en":"...",
  "description_de":"one short sentence, no duration, no 'choose the answer'", "description_en":"...",
  "task_de":"instruction requesting exactly the results from the appended difficulty contract", "task_en":"...",
  "rows":[
    {{"index":1,"source":"bank","date":"2026-03-01","document":"RE-8841","amount":1240.00,
      "text_de":"Zahlung Re 8841 Mueller GmbH Dauerauftrag","text_en":"Payment inv 8841 Mueller GmbH standing order"}},
    {{"index":2,"source":"ledger","date":"2026-03-01","document":"RE-8841","amount":1240.00,
      "text_de":"Mueller GmbH Wartungsvertrag","text_en":"Mueller GmbH maintenance contract"}}
  ],
  "micro_learning_de":"2-4 sentences, transferable rule of thumb about reconciling a free-text bank statement with AI and verifying its matches",
  "micro_learning_en":"..."
}}

Rules:
- Return the data array under the JSON key "rows" exactly as shown above and never rename it.
- Provide exactly as many rows in total as the appended difficulty contract names - no more, no fewer - and count
  every single line as its own row: a matched pair is TWO rows, one with source "bank" and one with source "ledger".
- Number every row consecutively in an "index" field starting at 1. The index of the last row must equal the
  row count the contract names - count with it and check yourself before returning.
- Meet at least the unmatched counts named by the appended difficulty contract and fill the rest with matched pairs
  so the total object count lands exactly on the contract number.
- A matched pair is one bank row and one ledger row with the identical document value and the identical amount.
- Every document value belonging to an unmatched line must appear on that side only and exactly once in the whole list.
- text_de and text_en of a bank row must contain the document number in a messy, human way: lower case, spaces or no
  separator, an abbreviation in front of it. Never print the clean document value on a bank row.
- text_de and text_en of a ledger row are short and business-like and must NOT repeat the document number; the
  rendered line already carries it as its own column.
- Amounts must be positive numbers (max 2 decimals). Vary them so unmatched items are not obvious from the amount alone.
- Exactly one unmatched line must carry the largest amount among all unmatched lines - no tie."""

    return {
        'bulk_categorization': bulk_categorization,
        'plan_actual_deviation': plan_actual_deviation,
        'duplicate_payment_hunt': duplicate_payment_hunt,
        'invoice_extraction': invoice_extraction,
        'policy_violation_check': policy_violation_check,
        'receivables_aging': receivables_aging,
        'vat_rate_audit': vat_rate_audit,
        'bank_reconciliation': bank_reconciliation,
    }
