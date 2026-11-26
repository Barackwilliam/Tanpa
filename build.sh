#!/usr/bin/env bash
# Render build step: install, collect static files, migrate the Supabase database.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# First admin account (set DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD in Render).
# Safe to run on every deploy: it is skipped once the user exists.
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --no-input || echo "Superuser already exists, skipping."
fi

# Real starter content only (logo photos -> gallery, 4th conference). Idempotent.
if [[ "${RUN_SEED:-true}" == "true" ]]; then
  python manage.py seed_demo
fi
