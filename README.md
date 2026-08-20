# AI-Facilitator-for-Finance-employee

Django + PostgreSQL backend with a React/Vite frontend. Local development runs
the two as **separate Docker containers** (with Vite proxying `/api` to Django).
On [Railway](https://railway.app) they ship as **one service**: the root
`Dockerfile` builds the frontend and bundles it into the Django image, which
serves both the API and the SPA (via WhiteNoise) on a single origin.

## Project layout

```
.
├── Dockerfile              # Railway prod image: builds frontend + bundles into Django
├── railway.json            # Railway: build from the root Dockerfile
├── docker-compose.yml      # local stack: web (Django) + db (Postgres) + frontend (Vite)
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
# From the repo root. .env already exists; if not: cp backend/.env.example backend/.env
docker compose up --build        # first run (builds the image)
```

That's it — the `web` container applies migrations and starts the dev server with
auto-reload, `db` is Postgres 16.

- App:   http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin
- Frontend: http://127.0.0.1:5173

Everyday use:

```bash
docker compose up -d             # start in background (no rebuild needed)
docker compose logs -f web       # watch Django logs
docker compose down              # stop (data is kept)
docker compose down -v           # stop and wipe the database
docker compose up --build        # rebuild after changing requirements.txt
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
docker compose exec web python manage.py send_daily_mission_reminders
```

### AI mission review workflow

Weekly mission generation runs only in Django. Configure the Uni API in
`backend/.env`; never place these values in Vite or frontend environment files:

```env
KICONNECT_API_KEY=your-key
KICONNECT_BASE_URL=https://chat.kiconnect.nrw/api/v1
KICONNECT_MODEL=your-model
KICONNECT_CHAT_COMPLETIONS_PATH=/chat/completions
```

Generate review proposals for the next calendar week with:

```bash
docker compose exec web python manage.py generate_weekly_missions
# Replace existing AI review drafts, while preserving published missions:
docker compose exec web python manage.py generate_weekly_missions --force
```

The command requires at least one user with the `content_creator` or `admin`
role. Generated missions remain in review until a content creator approves them
on the Missions page.

### Weekly mission email reminders

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

All config is read from environment variables (loaded from `backend/.env` locally
via `python-dotenv`):

| Variable        | Purpose                        | Local default                           |
|-----------------|--------------------------------|-----------------------------------------|
| `SECRET_KEY`    | Django secret key              | dev placeholder (override in prod)      |
| `DEBUG`         | Debug mode                     | `True`                                  |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts  | `localhost,127.0.0.1`                   |
| `DATABASE_URL`  | Postgres connection string     | `postgres://app:app@localhost:5432/app` |
| `KICONNECT_API_KEY` | Server-side Uni API key | no default |
| `KICONNECT_BASE_URL` | Uni API base URL | `https://chat.kiconnect.nrw/api/v1` |
| `KICONNECT_MODEL` | Model used for mission generation | no default |

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
   - Uni API keys for mission generation: `KICONNECT_API_KEY` (+ optional
     `KICONNECT_*` overrides) and the `EMAIL_*` variables for reminders.
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
