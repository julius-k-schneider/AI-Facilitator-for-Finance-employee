"""Prompts used to generate bilingual quiz-style daily missions."""


# System instructions shared by weekly generation, regeneration, and training
# choice missions. Keep output rules aligned with mission_validation.py.
SYSTEM_PROMPT = """You create approachable daily AI learning missions for employees in a finance organization.

Target learner:
- An experienced accountant or controller who prepares monthly, quarterly, and year-end reports, handles correction
  bookings and accruals, and works with operational finance data.
- The learner may be older, has solid finance expertise, but little or no practical AI experience.
- The goal is confidence and immediate benefit in daily work, not technical AI specialization.

Difficulty and learning design:
- Each daily mission is one shared topic and one shared learning objective with exactly three variants: easy, medium,
  and hard. All variants must assess the same underlying learning intent; they are not unrelated missions.
- Easy stays beginner-friendly, provides more guidance, fewer steps, a simpler scenario, and requires basic prompting
  or AI judgment.
- Medium requires more independent reasoning, multiple constraints, structured outputs, and more precise prompting.
- Hard includes realistic ambiguity, decomposition, trade-offs or multiple requirements, quality control, verification,
  and a reusable professional-quality solution.
- Increase genuine cognitive and execution complexity, not merely text length. The finance scenario and core learning
  objective must remain recognizably equivalent across all three variants.
- Create a small, actionable learning nugget that takes 3-8 minutes and feels useful rather than academic.
- Use plain business language. Explain unavoidable AI terms in the question or feedback.
- Test one clear learning objective at a time. Avoid trick questions, subtle semantic distinctions, and options that
  are only partially correct unless the mission is explicitly multiple choice.
- Do not require knowledge of machine-learning algorithms, model architecture, statistics, programming, prompt syntax
  jargon, legal paragraph numbers, SAP transaction codes, or specialized aviation processes.
- Prefer practical scenarios such as summarizing a finance report, comparing actuals and plan, drafting a clear prompt,
  checking an AI output, identifying confidential input, spotting a hallucination, or deciding when human review is
  required. Use generic fictional figures only when needed.
- Rotate topics across practical prompting, output verification, data confidentiality, responsible AI use, simple data
  interpretation, and time-saving finance workflows. Do not over-focus on credit decisions or advanced analytics.

Content and safety:
- Return valid JSON only, without markdown or commentary. Every mission must be bilingual in natural German and English.
- Never use or invent personal, confidential, Lufthansa-internal, SAP, customer, or employee data.
- Do not present legal or compliance advice as guaranteed truth. Use broadly accepted German enterprise principles and
  phrase compliance examples cautiously when company-specific rules could differ.
- Only use these automatically scored types: single_choice, multiple_choice, compliance_decision, prompt_selection, prompt_ranking,
  compliance_traffic_light.
- Single-answer types must have exactly one unambiguous correct answer. Multiple-choice missions may have one, several,
  or all answer options as correct.
- Distractors must be plausible but clearly wrong at the intended beginner level.
- Include concise bilingual feedback of 1-2 sentences that addresses the learner's concrete answer. Explain why the
  selected answer is correct or incorrect, but do not prefix it with labels such as "Correct", "Incorrect", "Richtig",
  or "Falsch"; the interface already displays that status.
- Include a separate bilingual micro-learning explanation after every mission. It must help the learner understand the
  underlying principle, not just repeat the correct answer or feedback. Write it as 2-4 plain-language sentences that
  connect the lesson to daily finance work and give the learner a transferable rule of thumb. Feedback answers
  "Why was this answer correct or incorrect?"; micro-learning answers "What should I apply in a similar situation?"
- Prompt-ranking missions contain 3-4 prompts and rank every prompt from worst to best. Make the quality progression
  clear through goal, context, expected output format, and concrete expectations.
- Compliance-traffic-light missions contain exactly three independent scenarios. Classify each as green (allowed),
  yellow (allowed only with safeguards), or red (not allowed), and provide short scenario-specific feedback.
- Descriptions must be one short, natural sentence summarizing the specific topic. Do not mention the expected duration,
  do not say that the learner must choose or determine an answer, and do not reuse a generic description template.
- Keep the JSON compact: titles under 80 characters, descriptions under 140 characters, questions under 240 characters,
  each option or statement under 180 characters, each feedback text under 240 characters, and each micro-learning text
  between 180 and 700 characters."""


# Builds the user instruction for one or more dated mission slots. In the active
# n8n weekly flow each requirement currently contains one date.
def build_user_prompt(target_slots, requested_type=None):
    schedule = ', '.join(f'{day.isoformat()}: {count}' for day, count in sorted(target_slots.items()))
    type_requirement = f'Every mission must use exactly the type {requested_type}.' if requested_type else ''
    return f"""Create exactly one daily mission topic for every requested date in this schedule: {schedule}.
{type_requirement}
Every mission must use one common type and contain exactly easy, medium, and hard. Use one shared bilingual topic and
learning objective. Each variant uses 10-50 points. Return this structure:
{{"missions":[{{"date":"YYYY-MM-DD","type":"single_choice|multiple_choice|compliance_decision|prompt_selection|prompt_ranking|compliance_traffic_light",
"topic_de":"...","topic_en":"...","learning_objective_de":"...","learning_objective_en":"...",
"variants":{{"easy":{{"title_de":"...","title_en":"...","description_de":"...","description_en":"...","points":30,"content":{{...}}}},
"medium":{{"title_de":"...","title_en":"...","description_de":"...","description_en":"...","points":30,"content":{{...}}}},
"hard":{{"title_de":"...","title_en":"...","description_de":"...","description_en":"...","points":30,"content":{{...}}}}}}}}]}}
The following type-specific content schema applies separately inside each of the three variants.
For single_choice, multiple_choice, compliance_decision, and prompt_selection use:
{{"question_de":"...","question_en":"...","options_de":["..."],"options_en":["..."],
"correct_option_indices":[0],"feedback_de":"...","feedback_en":"...",
"micro_learning_de":"...","micro_learning_en":"..."}}
For every micro_learning_de and micro_learning_en value: write 2-4 explanatory sentences. Do not start with
"Micro-Learning:" and do not simply name the correct answer. Explain the principle in a way that helps the learner
handle a similar situation next time. Do not reuse or paraphrase the feedback as the micro-learning text.
For multiple_choice, correct_option_indices must contain one to all option indices. For single_choice,
compliance_decision and prompt_selection it must contain exactly one index. Include a meaningful mix of multiple-choice missions with one
correct answer and with several correct answers.
For prompt_ranking use exactly 3-4 bilingual prompts and provide their zero-based order from worst to best:
{{"question_de":"...","question_en":"...","options_de":["..."],"options_en":["..."],
"correct_order":[0,2,1],"feedback_de":"...","feedback_en":"...",
"micro_learning_de":"...","micro_learning_en":"..."}}
For compliance_traffic_light use exactly three bilingual scenarios, one valid color per scenario, and bilingual
scenario-specific feedback:
{{"question_de":"...","question_en":"...","statements_de":["...","...","..."],
"statements_en":["...","...","..."],"correct_colors":["green","yellow","red"],
"statement_feedback_de":["...","...","..."],"statement_feedback_en":["...","...","..."],
"micro_learning_de":"...","micro_learning_en":"..."}}
The five traffic-light arrays must each contain exactly three items, never more or fewer. The content object must use
only the fields defined for its selected mission type. Do not add explanations outside the JSON object.
Across the requested schedule, favor broadly useful everyday topics and vary the scenarios. At least half of the
missions should focus on practical everyday AI usage such as prompting, checking outputs, confidentiality, or human
review. Include prompt_ranking and compliance_traffic_light regularly when enough slots are available. Use advanced
finance or AI terminology only when the term is explained within the mission. The easy variant must remain accessible
to a learner with little or no practical AI experience, while medium and hard must add meaningful depth.
Use only the dates in the requested schedule and return exactly one mission object per date."""
