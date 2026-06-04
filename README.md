# AI-Facilitator-for-Finance-employee

Django + PostgreSQL backend. The standard local workflow runs **everything in
Docker** (Django + Postgres) and deploys to [Railway](https://railway.app), which
builds the same `Dockerfile` and provides managed Postgres.

## Project layout

```
.
├── docker-compose.yml      # local stack: web (Django) + db (Postgres)
└── backend/
    ├── Dockerfile          # app image (local dev + Railway prod)
    ├── .dockerignore
    ├── .env                # local secrets (gitignored)
    ├── .env.example        # template — copy to .env
    ├── .python-version     # pins Python 3.12
    ├── railway.json        # Railway: build from Dockerfile
    ├── requirements.txt
    ├── manage.py
    └── config/             # Django project (settings, urls, wsgi, asgi)
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
```

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

Generate a production `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

## Deploy to Railway

Railway builds the **same `backend/Dockerfile`** (no Nixpacks), so prod matches local.

1. **Create the project**: Railway dashboard → *New Project* → *Deploy from GitHub repo*.
2. **Set the root directory**: Service → *Settings* → *Root Directory* = `backend`
   (where the `Dockerfile` and `railway.json` live).
3. **Add Postgres**: project → *New* → *Database* → *Add PostgreSQL*. Railway injects
   `DATABASE_URL` into the service automatically.
4. **Set service variables** (Service → *Variables*):
   - `SECRET_KEY` = a generated value (see command above)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` is optional; the app already trusts Railway's
     `RAILWAY_PUBLIC_DOMAIN` automatically.
   - Optional: `SECURE_HSTS_SECONDS` (e.g. `31536000`) once the site is HTTPS-only.
5. **Deploy.** The container's start command runs `collectstatic`, then `migrate`,
   then `gunicorn` (see `backend/Dockerfile`). Static files are served by WhiteNoise.
6. **Expose it**: Service → *Settings* → *Networking* → *Generate Domain*. Create the
   first admin user via the service shell: `python manage.py createsuperuser`.

### How prod differs from local

- `DATABASE_URL` comes from the Railway Postgres plugin (not Docker compose).
- The container runs `gunicorn` (prod) instead of `runserver` (dev auto-reload).
- `DEBUG=False` enables secure cookies, SSL redirect, and SSL-required DB
  connections (see the bottom of `backend/config/settings.py`).
- Static files are collected at startup and served by WhiteNoise.
