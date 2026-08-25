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
        'The contract overrides every generic range in the base prompt. Before returning, count the data items and '
        'requested outputs and verify that both languages mean the same thing.'
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

Scenario: the learner receives a long list of {min_rows}-{max_rows} booking lines (fictional) and must assign each line
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
- Provide between {min_rows} and {max_rows} rows. Every row needs date (YYYY-MM-DD), a bilingual description, a positive
  amount (number, max 2 decimals), and a category_index that is a valid zero-based index into the categories.
- Each description must map UNAMBIGUOUSLY to exactly one category for a finance professional. No trick lines.
- task_de and task_en must explicitly list the generated categories in their matching language.
- Give every row a category-specific cue. Avoid ambiguous items such as generic client meals, furniture, subscriptions,
  or events unless the description itself makes the intended category unmistakable.
- Spread the rows across all categories; every category must have at least three rows.
- Keep descriptions short (under 90 characters) and business-like."""

    # Plan-versus-actual analysis: detect and aggregate budget overruns.
    plan_actual_deviation = f"""Create one "plan vs. actual deviation" finance task.

Scenario: the learner receives a long list of {min_rows}-{max_rows} fictional cost centers, each with a planned
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
- Provide between {min_rows} and {max_rows} rows, each a distinct, plausible cost center name (bilingual).
- plan must be a positive number (max 2 decimals). actual must be a positive number (max 2 decimals).
- At least 8 rows must overrun their plan (actual > plan), and at least 4 of those must overrun by more than 10%,
  so there is a clear, non-trivial answer.
- Request only the results named by the appended difficulty contract. Never invent additional KPIs.
- Keep the mix realistic: most cost centers should be close to plan, a minority clearly over."""

    # Duplicate-payment hunt: identify pairs despite spelling variations.
    duplicate_payment_hunt = f"""Create one "duplicate payment hunt" finance task.

Scenario: the learner receives a long fictional accounts-payable run of {min_rows}-{max_rows} payment lines. A few
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
- Provide between {min_rows} and {max_rows} rows.
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

Scenario: the learner receives {min_invoices}-{max_invoices} short fictional invoice descriptions written as natural-language
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
- Provide between {min_invoices} and {max_invoices} invoices.
- Each invoice_number must be unique. Amounts must be positive numbers (max 2 decimals).
- At least 3 different vendors must appear more than once (across different invoices) so totals per vendor are
  meaningful to compute.
- Request only the results named by the appended difficulty contract. Never invent additional KPIs.
- text_de and text_en must be 1-3 full sentences of natural prose that contain the invoice number, vendor name,
  date, and amount somewhere in the text - do not format them as a table or list."""

    return {
        'bulk_categorization': bulk_categorization,
        'plan_actual_deviation': plan_actual_deviation,
        'duplicate_payment_hunt': duplicate_payment_hunt,
        'invoice_extraction': invoice_extraction,
    }
