#!/bin/sh
set -e

echo "Waiting for PostgreSQL database connection..."
python - << 'EOF'
import os
import sys
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection

max_attempts = 60
for attempt in range(1, max_attempts + 1):
    try:
        connection.ensure_connection()
        print("Database connection established successfully.")
        sys.exit(0)
    except Exception as err:
        print(f"Waiting for database (attempt {attempt}/{max_attempts}): {err}")
        time.sleep(1)

print("ERROR: Could not connect to database after maximum attempts.")
sys.exit(1)
EOF

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting demo data loading in the background..."
python manage.py load_demo_data &

echo "Starting Gunicorn on port ${PORT:-8000} with 1 worker, 4 threads, timeout 120..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 4 \
    --timeout 120

