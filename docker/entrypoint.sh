#!/usr/bin/env sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "→ PostgreSQL ($DB_HOST:$DB_PORT) kutilmoqda..."
until python -c "import socket,os,sys; s=socket.socket(); s.settimeout(2); s.connect((os.environ.get('DB_HOST','db'), int(os.environ.get('DB_PORT','5432')))); s.close()" 2>/dev/null; do
  sleep 1
done
echo "→ PostgreSQL tayyor."

# Migratsiya/collectstatic/webhook faqat bitta joyda (web) ishlaydi
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "→ Migratsiyalar..."
  python manage.py migrate --noinput

  echo "→ Statik fayllar..."
  python manage.py collectstatic --noinput

  echo "→ Davriy vazifalar (django-q)..."
  python manage.py setup_periodic_tasks || true

  # Bot polling rejimida ishlaydi ('bot' servisi) — webhook o'rnatilmaydi.

  if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "→ Superuser tekshiruvi..."
    python manage.py createsuperuser --noinput 2>/dev/null || echo "  (superuser allaqachon mavjud)"
  fi
fi

exec "$@"
