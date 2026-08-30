# syntax=docker/dockerfile:1.6
#
# Single-service production image: builds the Vite/React frontend and bundles it
# into the Django app, which serves both the API and the SPA (via WhiteNoise) on
# one origin.
#
# Local development still uses docker-compose.yml (separate containers).

# ─── Stage 1: build the Vite/React frontend ────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Django runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg[binary] ships prebuilt wheels, so no system libpq / compiler is needed.
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Backend source.
COPY backend/ ./backend/

# Built frontend from stage 1 — Django serves this via WhiteNoise.
COPY --from=frontend /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

EXPOSE 8000

# collectstatic + migrate run at startup (not build time) because settings.py
# requires DATABASE_URL, which is only available in the running container.
# Honours $PORT when the host provides one; falls back to 8000.
CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate --noinput && (python manage.py run_research_scheduler &) && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"
