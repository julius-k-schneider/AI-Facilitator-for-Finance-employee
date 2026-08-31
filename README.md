# Fin.pilot

Django + PostgreSQL backend with a React/Vite frontend. Local development runs
the application and n8n as **separate Docker containers** (with Vite proxying
`/api` to Django).
In production they ship as **one service**: the root `Dockerfile` builds the
frontend and bundles it into the Django image, which serves both the API and the
SPA (via WhiteNoise) on a single origin.

## Project layout

```
.
├── Dockerfile              # prod image: builds frontend + bundles into Django
├── docker-compose.yml      # local stack: db, web, research-scheduler, n8n, frontend
├── .env                    # shared Compose secrets (gitignored)
├── .env.example            # template — copy to .env
├── docker/
│   └── n8n-init.sh         # bootstraps n8n credentials + workflows on first start
├── workflows/n8n/          # exported n8n workflows (generator, research collector/selector)
├── backend/
│   ├── Dockerfile          # local-dev app image (used by docker-compose)
│   ├── .env                # Django settings (gitignored)
│   ├── .env.example        # template — copy to .env
│   ├── .python-version     # pins Python 3.12
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/             # Django project (settings, urls, wsgi, asgi)
│   └── accounts/           # the application itself
│       ├── models.py       # Profile, Mission, GenerationRun, ResearchItem, ...
│       ├── views.py        # JSON API under /api/auth/
│       ├── urls.py
│       ├── n8n_internal_views.py  # service-only endpoints under /internal/n8n/
│       ├── admin.py
│       ├── migrations/
│       ├── prompts/        # all LLM prompts, grouped by request type
│       ├── services/       # generation planning, n8n contract, research, email, ...
│       └── management/commands/   # generate_weekly_missions, seed_*, run_research_scheduler
└── frontend/
    ├── Dockerfile          # frontend image for local Docker development
    ├── vite.config.js      # base '/static/' for prod build; dev /api proxy
    ├── package.json        # React/Vite dependencies and scripts
    ├── index.html
    └── src/
        ├── App.jsx         # routing, session bootstrap, login/logout
        ├── pages/          # one module per screen (+ pages/missions/ per mission type)
        ├── components/     # sidebar, login screen, shared learning views
        ├── services/       # fetch wrappers per API area
        ├── onboarding/     # onboarding flow and its content
        ├── i18n/           # de.json / en.json (the UI is fully bilingual)
        └── auth/           # role and permission constants
```

## Local development (standard: Docker)

Prerequisite: Docker Desktop (running). No local Python needed.

```bash
# From the repo root (PowerShell equivalents: Copy-Item ...):
cp backend/.env.example backend/.env
cp .env.example .env
# Replace the placeholder secrets in BOTH files (see Configuration below):
#   .env          -> the three N8N_* secrets and KICONNECT_API_KEY
#   backend/.env  -> KICONNECT_API_KEY and the same three N8N_* secrets
docker compose up --build
```

Compose starts five services: `db` (Postgres 16), `web` (Django, applies
migrations then runs the dev server with auto-reload), `research-scheduler` (a
long-running Django command that triggers the weekly research collection),
`n8n` (stores its state in the `n8n_data` volume) and `frontend` (Vite).

- App:   http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin
- Frontend: http://127.0.0.1:5173
- n8n: http://127.0.0.1:5678

Everyday use:

```bash
docker compose up -d             # start in background
docker compose logs -f web       # watch Django logs
docker compose down              # stop (data is kept)
docker compose down -v           # stop and wipe Postgres and n8n data
docker compose up --build        # rebuild images
```

**Code changes auto-reload** — the source is mounted into the container, so you
don't restart anything while editing `.py` files. You only rebuild (`--build`)
when dependencies in `requirements.txt` change.

### Create an admin user

```bash
docker compose exec web python manage.py createsuperuser
```

Then log in at http://127.0.0.1:8000/admin.

### Other management commands

Run any `manage.py` command inside the container:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell
docker compose exec web python manage.py generate_weekly_missions
docker compose exec web python manage.py seed_placeholder_missions --start-date 2026-08-24 --end-date 2026-08-27
docker compose exec web python manage.py send_daily_mission_reminders
```

`seed_placeholder_missions` creates idempotent review placeholders on unoccupied
weekdays. Weekly generation then skips those dates, which is useful when testing
the generation workflow with only one open day.

### AI mission review workflow

Mission generation is asynchronous and orchestrated by n8n. Django creates the
week plan and versioned generator requirements, while n8n runs the generator,
calls Django's deterministic validation endpoint, performs a separate AI review
and optional repair, then returns the passed result through a callback. Only
Django writes missions to the database and places them in human review.

There are two `.env` files and they serve different purposes. Never put any of
these values in Vite or frontend environment files:

- **`backend/.env`** is loaded by Django (via `env_file` into the `web` and
  `research-scheduler` containers). It holds everything in the Configuration
  table below.
- **`.env` in the repository root** is read by Compose itself, purely for
  `${VAR}` substitution in `docker-compose.yml`. Compose only needs seven values
  from it; the rest of the file is ignored.

```env
# .env — the only entries Compose actually substitutes
N8N_SERVICE_SECRET=separate-outbound-secret        # required
N8N_CALLBACK_SECRET=separate-callback-secret       # required
N8N_ENCRYPTION_KEY=separate-n8n-encryption-key     # required
KICONNECT_API_KEY=...                              # passed into the n8n container
KICONNECT_BASE_URL=https://chat.kiconnect.nrw/api/v1
KICONNECT_MODEL=...
KICONNECT_CHAT_COMPLETIONS_PATH=/chat/completions
```

Compose aborts with a message if one of the three `N8N_*` secrets is missing.
The `KICONNECT_*` values in the root file are what the n8n generator and reviewer
nodes call; the copies in `backend/.env` are what Django's own assistant and chat
replies use. Both files ship as full copies of the same template, so the
duplication is expected — the two sides simply read different subsets.

Compose injects `http://n8n:5678/webhook/mission-generation` into Django. In the
other direction, n8n receives `DJANGO_INTERNAL_BASE_URL=http://web:8000`; use it
as the base for validation and callback HTTP Request nodes. Both names resolve
only inside the shared Compose network. KICOnnect settings in Django are still
used by interactive assistant/chat replies, but no active mission-generation
endpoint calls KICOnnect directly.

The first start of the `n8n_data` volume bootstraps the n8n instance itself:
`docker/n8n-init.sh` imports the two Header-Auth credentials (their values come
from the root `.env`, so no secret is committed), imports the exports from
`workflows/n8n/` and publishes all four workflows — the three the mission
generation calls by webhook, plus the research collector. The separate
`research-scheduler` Compose service runs `manage.py run_research_scheduler`,
which polls the local database and invokes the collector only when research is
actually due; the default is Monday at 07:00 Europe/Berlin, configurable on the
Research page. No manual import or credential setup in the n8n editor is
needed. To bootstrap
again after editing the exports, remove the marker and restart:

```bash
docker compose exec n8n rm /home/node/.n8n/.bootstrapped
docker compose restart n8n
```

Re-importing overwrites workflow changes made in the n8n editor, so export them
back to `workflows/n8n/` first.

Generate review proposals for the next calendar week with:

```bash
docker compose exec web python manage.py generate_weekly_missions
# Replace existing AI review drafts, while preserving published missions:
docker compose exec web python manage.py generate_weekly_missions --force
```

The command requires at least one user with the `content_creator` or `admin`
role and starts a `GenerationRun`. Generated missions appear in the existing
review UI only after n8n has returned a passed AI review and Django has validated
the complete payload again.

To reduce repeated content, Django adds a compact history of recent review and
published missions to every weekly generator request. Task challenge types that
have never been used, or were used least recently, are preferred. Django also
performs a conservative text-similarity check during n8n validation and again
before storing a completed batch. Broad topics may recur, but near-identical
learning objectives, scenarios, and questions are rejected and enter the
existing n8n repair path.

If a weekly run still has failed requirements after its bounded repair attempts,
Django automatically starts one full follow-up generation for only those missing
days. Successful missions from the first run remain in review and are included
in the follow-up history. The follow-up is limited to one attempt, so persistent
model or validation failures cannot create an unbounded retry loop.

The webhook receives a versioned object with `generation_run_id`,
`generation_kind`, `requirements`, `research_context`, `review_policy`, and the
two relative Django service
endpoints. Each requirement contains the exact generator messages and generation
parameters derived from the existing mission prompts. Django sends
`N8N_SERVICE_SECRET` as `X-N8N-Service-Secret` and the run UUID as the
`Idempotency-Key` header.

n8n validates one generated result with:

```text
POST /internal/n8n/validate-mission/
X-N8N-Callback-Secret: <N8N_CALLBACK_SECRET>
{"generation_run_id":"...","requirement_id":"...","result":{...}}
```

Progress and completion use:

```text
POST /internal/n8n/generation-callback/
X-N8N-Callback-Secret: <N8N_CALLBACK_SECRET>
{"generation_run_id":"...","status":"reviewing","n8n_execution_id":"..."}
```

A completed callback additionally supplies one result for every requirement and
an overall passed review:

```json
{
  "generation_run_id": "...",
  "status": "completed",
  "n8n_execution_id": "...",
  "results": [{"requirement_id": "...", "payload": {}}],
  "review_report": {"verdict": "pass", "score": 0.9, "issues": []},
  "research_context": []
}
```

Task-mission results use `variants` instead of `payload`, keyed by `easy`,
`medium`, and `hard`. Django treats callbacks idempotently and revalidates the
entire completed result before storing anything.

### Weekly mission email reminders

Publishing or approving a mission does not send an email. The only automatic
email workflow is the weekly reminder described below.

To remind users who have not completed all published missions for the current
week, run:

```bash
docker compose exec web python manage.py send_daily_mission_reminders
```

Schedule this command externally on Fridays at 12:00, for example with a server
cron job or the scheduler of the hosting platform. The command also skips non-Fridays, so an accidentally
daily schedule will not send daily reminder emails. It records one reminder per
user and Friday, so reruns do not send duplicate reminders. Each email lists only
the missions that are still missing for that user.

Useful local checks:

```bash
docker compose exec web python manage.py send_daily_mission_reminders --dry-run
docker compose exec web python manage.py send_daily_mission_reminders --date 2026-06-19
```

### Adaptive mission difficulty

Each generated weekday now contains one learning topic with `easy`, `medium`,
and `hard` variants. A persisted assignment maps the user's skill level to the
variant (`beginner` → `easy`, `advanced` → `medium`, `pro` → `hard`) when the
mission is first opened, so a same-day level change cannot unlock another
variant. Admins configure the global progression window and thresholds in User
management or Django admin.

The manual mission creator uses the same model: authors enter one bilingual
topic and learning objective, then complete separate `easy`, `medium`, and
`hard` editors. New manual missions are rejected unless all three variants are
valid; editing a legacy single-variant mission seeds all three editors from the
existing content so it can be migrated without losing text.

Migration `0011_skill_difficulty_progression` gives existing users the safe
`beginner` default. Existing missions and attempts remain available but are left
without an invented difficulty; consequently, legacy attempts are preserved but
do not enter a difficulty-specific leaderboard or automatic progression window.

## Alternative: native venv (no Docker for the app)

Faster IDE/debugger integration; only Postgres runs in Docker.

```bash
docker compose up -d db                 # just the database
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver              # http://127.0.0.1:8000
```

(`backend/.env` points `DATABASE_URL` at `localhost:5432`, which is what the venv
workflow uses. The Docker `web` service overrides it to the `db` host internally.)

## Configuration

Configuration is read from environment variables. Locally, Django settings live
in `backend/.env`; the root `.env` supplies the values Compose substitutes into
`docker-compose.yml` (see the split described above).

Most variables are exposed through `config/settings.py` and read via
`django.conf.settings`. Five are read directly from the environment in
application code and therefore do **not** appear in `settings.py` — they are
marked accordingly.

| Variable        | Purpose                        | Local default                           |
|-----------------|--------------------------------|-----------------------------------------|
| `SECRET_KEY`    | Django secret key              | dev placeholder (override in prod)      |
| `DEBUG`         | Debug mode                     | `False` (the example `.env` sets `True`) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts  | `localhost,127.0.0.1`                   |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins (with scheme) trusted for CSRF | `https://` of every non-local `ALLOWED_HOSTS` entry |
| `DATABASE_URL`  | Postgres connection string     | `postgres://app:app@localhost:5432/app` |
| `TIME_ZONE`     | Django time zone               | `Europe/Berlin`                         |
| `INITIAL_ADMIN_EMAIL` | Email that gets the admin role on first registration; without it the first registered user becomes admin | no default — *read directly from the environment* |
| `KICONNECT_API_KEY` | Server-side Uni API key | no default — *read directly from the environment* |
| `KICONNECT_BASE_URL` | Uni API base URL | `https://chat.kiconnect.nrw/api/v1` — *read directly* |
| `KICONNECT_MODEL` | Model used for interactive assistant/chat replies | no default — *read directly* |
| `KICONNECT_CHAT_COMPLETIONS_PATH` | OpenAI-compatible completions path | `/chat/completions` — *read directly* |
| `N8N_MISSION_GENERATION_URL` | n8n webhook for generation runs | `http://n8n:5678/webhook/mission-generation` in Compose |
| `N8N_RESEARCH_COLLECTOR_URL` | n8n webhook for the research collector | `http://n8n:5678/webhook/ai-finance-research-collector-run` in Compose |
| `N8N_SERVICE_SECRET` | Django-to-n8n service credential | required in root `.env` |
| `N8N_CALLBACK_SECRET` | n8n-to-Django callback credential | required in root `.env` |
| `N8N_ENCRYPTION_KEY` | Encrypts n8n credentials at rest (used by the n8n container only, not by Django) | required in root `.env` |
| `DJANGO_INTERNAL_BASE_URL` | Django base URL used by n8n nodes | `http://web:8000` in Compose |
| `N8N_REQUEST_TIMEOUT` | Timeout for starting a workflow | `10` seconds |
| `N8N_WORKFLOW_VERSION` | Version included in the workflow contract | `v1` |
| `MISSION_TASK_DAYS_PER_WEEK` | Task-style days in a generated workweek | `2` |
| `RESEARCH_SCHEDULER_POLL_SECONDS` | Poll interval of the `research-scheduler` service | `30` seconds |
| `EMAIL_BACKEND` | Django email backend | console backend when `DEBUG`, otherwise SMTP |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP settings for the weekly reminder | see `backend/.env.example` |
| `SECURE_SSL_REDIRECT` | Redirect to HTTPS (only applied when `DEBUG=False`) | `True` |
| `SECURE_HSTS_SECONDS` | HSTS max-age (only applied when `DEBUG=False`) | `0` (disabled) |

Generate a production `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

