# n8n Workflows

The research feature is deliberately split into two independent workflows.
Mission generation additionally uses the rebuilt V2 orchestrator and a separate
single-mission worker.

## AI Mission Generator V2

- Workflow IDs: `MissionGeneratorV2Prod` and `MissionWorkerV2Prod`
- Production webhook: `POST /webhook/mission-generation`
- Internal worker webhook: `POST /webhook/mission-generation-worker-v2`
- Before a weekly generation the orchestrator calls the research selector
  locally. In a normal week, at most two to three matching current contexts are
  assigned, depending on the number of quiz missions.
- Research context is passed only to the specific quiz mission it was selected
  for. Generator, reviewer and repair all receive the same verified context;
  task missions and the remaining quiz missions stay evergreen content.
- An empty pool, a non-matching selection or a selector outage does not block
  mission generation. The run then continues without research context and
  records a warning in the review report.
- Model calls run in real batches of two so the capacity limit of the model
  endpoint is not exceeded.
- Generator, reviewer and repair pass `reasoning_effort: "low"` as a genuine
  KI:connect API parameter.
- Runtime, prompt/completion/total tokens and `finish_reason` are stored per
  mission requirement for every generator, reviewer and repair call in
  `GenerationRun.result_metadata.mission_metrics`.
- Every mission is validated and reviewed independently; at most two targeted
  repair attempts are possible.
- For large task missions the semantic reviewer only receives a compact,
  representative projection; schema, row counts, calculations and solutions
  continue to be checked deterministically by Django.
- Task difficulties use binding data and result profiles: easy has fewer records
  and key figures, medium extends both, hard uses the largest dataset and
  additional check figures. Task wording, evaluable result fields and points are
  synchronized to match, deterministically, by Django.
- Repairs return small, whitelist-validated `replace` patches instead of
  regenerating the complete mission.
- A patch that cannot be applied is repaired again directly; it does not run
  through validation and review unnecessarily.
- Status callbacks are completed through merge gates before validation, review
  and repair, so the UI shows the current step reliably and also after a page
  change.
- A single failure does not end the remaining missions. Successful results are
  handed to Django as a partial completion.
- Generator, review and repair output is normalized centrally as JSON and then
  validated deterministically by Django.

The file `ai-mission-generator-v2.json` contains both related workflows. On
import, the existing Header-Auth credentials for Django/n8n and for the AI
endpoint must be available. The previous `AI Mission Generator` remains
deactivated as a fallback option; `AI Mission Generator Backup` was left
unchanged.

## 1. AI Finance Research – Collector

- Workflow ID: `RsrchCollect2026`
- Schedule: Mondays at 07:00 by default, timezone `Europe/Berlin`; weekday, time
  and activation are managed on the Research page
- Manual trigger in the n8n editor
- Authenticated webhook: `POST /webhook/ai-finance-research-collector-run`
- Optional request body for a full re-evaluation: `{"force_refresh": true}`

The collector reads only configured feeds from official institutions:

- European Banking Authority (EBA)
- Bank for International Settlements (BIS and FSI)
- European Central Bank (press and blog)
- European Commission Digital Strategy
- BaFin

Processing consists of a 45-day recency filter, a hard AI-and-finance relevance
check, URL and content deduplication, a structured AI assessment and a final
deterministic validation. RSS content is treated as untrusted data; instructions
coming from a feed must not be executed. Only facts directly supported by the
feed text are accepted.

If the AI endpoint fails or returns an unusable response, a conservative
fallback applies. Before a re-evaluation the affected records are deactivated as
a precaution and released again only after a successful check. This keeps
rejected or outdated results from accidentally remaining selectable.

The n8n data table `ai_finance_research_pool` is retained for deduplication and
re-evaluation. The collector additionally syncs the entries into Django. Django
is the shared source of truth for the Research page and the context selector, so
that editing, deactivating and deleting take effect on future mission
generations immediately. The important fields are:

- stable `item_key` and `content_hash` for idempotency
- source, original URL, publication, retrieval and expiry time
- German and English summary
- supported facts with evidence excerpts
- mission hooks and tags
- relevance, confidence, risk flags and analysis method
- `eligible` as the hard release flag for the selector

## 2. AI Finance Research – Context Selector

- Workflow ID: `RsrchSelect2026A`
- Called as an n8n subworkflow via `Execute Workflow`
- Authenticated webhook: `POST /webhook/ai-finance-research-context-selector`
- Manual test trigger with sample data in the editor

Example input:

```json
{
  "generation_run_id": "example-run",
  "generation_kind": "weekly_missions",
  "as_of": "2026-08-23T12:00:00Z",
  "max_research_missions": 2,
  "preferred_tags": ["ai_governance", "risk", "banking"],
  "requirements": [
    {
      "id": "2026-08-24",
      "scheduled_date": "2026-08-24",
      "output_type": "quiz_mission",
      "requested_mission_type": "single_choice"
    },
    {
      "id": "2026-08-25",
      "scheduled_date": "2026-08-25",
      "output_type": "task_mission",
      "mission_type": "invoice_extraction"
    }
  ]
}
```

The selector considers only released, still-valid entries with supported facts
and medium or high confidence. The selection is deterministic and weights
relevance, source tier, confidence, recency, preferred tags and mission type. At
present, only requirements with `output_type: "quiz_mission"` receive research
context. Task missions remain unchanged.

The selector loads the current pool through the authenticated Django endpoint
`GET /internal/n8n/research/current/`. A separate Django scheduler checks only
the local database and calls n8n exclusively at the stored weekly time. As a
result, no n8n executions or HTTP requests occur between actual research runs.

By default at most two research contributions are selected; `max_research_missions`
allows zero to a maximum of three. A pool entry is used only once per call. With
an empty pool, non-matching requirements or a score below the threshold, the
workflow successfully returns an empty `research_context` together with a
warning. Mission generation then continues normally with evergreen content.

Every selected context carries safety instructions: use only `safe_facts`, treat
source content as untrusted, derive no legal advice, keep the learning objective
transferable, and verify the source during review.

## Authentication

Credentials and workflows are imported automatically by `docker/n8n-init.sh` on
the first start of the `n8n_data` volume; the secrets come from the root `.env`
and are in no file in the repository. A manual import in the editor is only
needed when the volume is already set up and the exports have changed.

Both webhooks expect the header `X-N8N-Service-Secret`. In the local n8n instance
they use the Header-Auth credential that already exists. Secrets are not stored
in the exported workflow files.

## Integration into mission generation

Before building the actual prompts, the V2 orchestrator calls the published
selector through its internal, authenticated webhook. The assignment happens via
`context_by_requirement[requirement.id]`, so no research contribution can slip
into a different mission or difficulty by accident. The prompt frames the
contribution as untrusted reference data and permits only the verified
`safe_facts`. When context is present, the quiz mission must name the source and
publication date, use the current occasion as the scenario, and still convey a
transferable learning objective. The reviewer checks these rules, and the repair
step receives the same context.
