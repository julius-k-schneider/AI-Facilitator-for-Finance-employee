# AI-Facilitator-for-Finance-employee

Django + PostgreSQL backend with a React/Vite frontend. Local development runs
the application and n8n as **separate Docker containers** (with Vite proxying
`/api` to Django).
On [Railway](https://railway.app) they ship as **one service**: the root
`Dockerfile` builds the frontend and bundles it into the Django image, which
serves both the API and the SPA (via WhiteNoise) on a single origin.

## Project layout

```
.
├── Dockerfile              # Railway prod image: builds frontend + bundles into Django
├── railway.json            # Railway: build from the root Dockerfile
├── docker-compose.yml      # local stack: Django + Postgres + Vite + n8n
├── backend/
│   ├── Dockerfile          # local-dev app image (used by docker-compose)
│   ├── .dockerignore
│   ├── .env                # local secrets (gitignored)
│   ├── .env.example        # template — copy to .env
│   ├── .python-version     # pins Python 3.12
│   ├── requirements.txt
│   ├── manage.py
│   └── config/             # Django project (settings, urls, wsgi, asgi)
└── frontend/
    ├── Dockerfile          # frontend image for local Docker development
    ├── vite.config.js      # base '/static/' for prod build; dev /api proxy
    ├── package.json        # React/Vite dependencies and scripts
    ├── index.html
    └── src/                # React app (App.jsx, pages, services, assets)
```

## Local development (standard: Docker)

Prerequisite: Docker Desktop (running). No local Python needed.

```bash
# From the repo root (PowerShell equivalents: Copy-Item ...):
cp backend/.env.example backend/.env
cp .env.example .env
# Replace the three n8n placeholder secrets in .env, then:
docker compose up --build
```

The `web` container applies migrations and starts the dev server with auto-reload,
`db` is Postgres 16, and n8n stores its local state in the `n8n_data` volume.

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

Configure the shared secrets in the repository-root `.env` (copied from
`.env.example`) and the Django connection settings in `backend/.env`. Never put
these values in Vite or frontend environment files:

```env
# .env (read by Compose and injected into Django and n8n)
N8N_SERVICE_SECRET=separate-outbound-secret
N8N_CALLBACK_SECRET=separate-callback-secret
N8N_ENCRYPTION_KEY=separate-n8n-encryption-key

# backend/.env
N8N_MISSION_GENERATION_URL=http://n8n:5678/webhook/mission-generation
N8N_RESEARCH_COLLECTOR_URL=http://n8n:5678/webhook/ai-finance-research-collector-run
N8N_REQUEST_TIMEOUT=10
N8N_WORKFLOW_VERSION=v1
```

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
generation calls by webhook, plus the research collector. A lightweight Django
scheduler waits for the configurable weekly time and invokes the collector only
when research is actually due; the default is Monday at 07:00 Europe/Berlin. No
manual import or credential setup in the n8n editor is needed. To bootstrap
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

Schedule this command externally on Fridays at 12:00, for example with Railway
Cron or a server cron job. The command also skips non-Fridays, so an accidentally
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
in `backend/.env`; the three shared n8n secrets live in the root `.env` so Compose
can inject identical values into both services.

| Variable        | Purpose                        | Local default                           |
|-----------------|--------------------------------|-----------------------------------------|
| `SECRET_KEY`    | Django secret key              | dev placeholder (override in prod)      |
| `DEBUG`         | Debug mode                     | `True`                                  |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts  | `localhost,127.0.0.1`                   |
| `DATABASE_URL`  | Postgres connection string     | `postgres://app:app@localhost:5432/app` |
| `KICONNECT_API_KEY` | Server-side Uni API key | no default |
| `KICONNECT_BASE_URL` | Uni API base URL | `https://chat.kiconnect.nrw/api/v1` |
| `KICONNECT_MODEL` | Model used for interactive assistant/chat replies | no default |
| `N8N_MISSION_GENERATION_URL` | n8n webhook for generation runs | `http://n8n:5678/webhook/mission-generation` in Compose |
| `N8N_SERVICE_SECRET` | Django-to-n8n service credential | required in root `.env` |
| `N8N_CALLBACK_SECRET` | n8n-to-Django callback credential | required in root `.env` |
| `N8N_ENCRYPTION_KEY` | Encrypts n8n credentials at rest | required in root `.env` |
| `DJANGO_INTERNAL_BASE_URL` | Django base URL used by n8n nodes | `http://web:8000` in Compose |
| `N8N_REQUEST_TIMEOUT` | Timeout for starting a workflow | `10` seconds |
| `N8N_WORKFLOW_VERSION` | Version included in the workflow contract | `v1` |
| `MISSION_TASK_DAYS_PER_WEEK` | Task-style days in a generated workweek | `2` |

Generate a production `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

## Deploy to Railway

The whole app runs as **one service**. The root `Dockerfile` builds the frontend
and bundles it into the Django image (no Nixpacks), so a single container serves
both the API and the SPA.

1. **Create the project**: Railway dashboard → *New Project* → *Deploy from GitHub repo*.
2. **Leave the root directory empty** (repo root). Railway reads the root
   `railway.json` and builds the root `Dockerfile`. Do **not** set it to `backend`.
3. **Add Postgres**: project → *New* → *Database* → *Add PostgreSQL*. Railway injects
   `DATABASE_URL` into the service automatically.
4. **Set service variables** (Service → *Variables*):
   - `SECRET_KEY` = a generated value (see command above)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` is optional; the app already trusts Railway's
     `RAILWAY_PUBLIC_DOMAIN` automatically.
   - n8n variables described above, optional `KICONNECT_*` values for interactive
     chat features, and the `EMAIL_*` variables for reminders.
   - Optional: `SECURE_HSTS_SECONDS` (e.g. `31536000`) once the site is HTTPS-only.
5. **Deploy.** The container's start command runs `collectstatic`, then `migrate`,
   then `gunicorn` (see the root `Dockerfile`). The built SPA and Django static
   files are served by WhiteNoise under `/static/`.
6. **Expose it**: Service → *Settings* → *Networking* → *Generate Domain*. Create the
   first admin user via the service shell: `python manage.py createsuperuser`.
7. **Schedule the cron commands** (optional): add Railway Cron jobs for
   `generate_weekly_missions` (weekly) and `send_daily_mission_reminders`
   (Fridays at 12:00).

### How prod differs from local

- Frontend and backend are **one origin** in prod (Django serves the built SPA);
  locally they are two containers and Vite proxies `/api` to Django.
- `DATABASE_URL` comes from the Railway Postgres plugin (not Docker compose).
- The container runs `gunicorn` (prod) instead of `runserver` (dev auto-reload).
- `DEBUG=False` enables secure cookies, SSL redirect, and SSL-required DB
  connections (see the bottom of `backend/config/settings.py`).
- Static files (SPA + admin) are collected at startup and served by WhiteNoise.
