#!/bin/sh
set -e

# Pre-resolve the DB hostname to avoid Docker DNS flakiness.
# asyncpg with NullPool resolves the hostname on every new connection.
# Caching the result in /etc/hosts makes resolution instant and reliable.
if [ -n "$DATABASE_URL" ]; then
  DB_HOST=$(python3 -c "
import os, urllib.parse as u
raw = os.environ.get('DATABASE_URL', '')
for prefix in ('postgresql+asyncpg://', 'postgresql://'):
    if raw.startswith(prefix):
        raw = 'postgresql://' + raw[len(prefix):]
        break
try:
    print(u.urlparse(raw).hostname or '')
except Exception:
    print('')
" 2>/dev/null || true)

  if [ -n "$DB_HOST" ]; then
    i=0
    while [ $i -lt 15 ]; do
      IP=$(getent hosts "$DB_HOST" 2>/dev/null | awk '{print $1}' | head -1)
      if [ -n "$IP" ]; then
        echo "$IP $DB_HOST" >> /etc/hosts
        echo "[entrypoint] Pre-resolved $DB_HOST -> $IP"
        break
      fi
      echo "[entrypoint] DNS not ready for $DB_HOST, retry $i/15 ..."
      i=$((i + 1))
      sleep 2
    done
  fi
fi

alembic upgrade head
# --proxy-headers + --forwarded-allow-ips: trust X-Forwarded-For from nginx so
# rate limiting keys on the real client IP, not the proxy container IP (P1).
# The api container is only reachable via the compose network, so "*" is safe.
# UVICORN_WORKERS: default 2; set to 1 in .env on low-RAM hosts (≤1 GB).
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"
