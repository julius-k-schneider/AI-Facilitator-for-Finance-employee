# Django app image — used both for local development (via docker-compose, which
# overrides the command to runserver) and for production on Railway.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first for better layer caching.
# psycopg[binary] ships prebuilt wheels, so no system libpq / compiler is needed.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Production default: collect static, apply migrations, then serve with gunicorn.
# Railway provides $PORT; falls back to 8000 when run standalone.
# docker-compose overrides this command with runserver for local development.
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate --noinput && (python manage.py run_research_scheduler &) && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 3"]
