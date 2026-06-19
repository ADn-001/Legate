#!/usr/bin/env bash
# Phase 1 E2E — proves the stack builds, serves, proxies, migrates, and reaches Supabase.
# Requires real Supabase/Resend credentials in ./.env.
set -euo pipefail

docker compose down -v --remove-orphans
docker compose build --no-cache
docker compose up -d

BASE="localhost:${NGINX_PORT:-80}"

# wait for health
for i in $(seq 1 30); do curl -fs "$BASE/health" && break; sleep 2; done

fail() { echo "FAIL: $1"; docker compose logs --tail 50; exit 1; }

curl -fs "$BASE/health" | grep -q '"ok"'                    || fail "health"
curl -fs "$BASE/" | grep -qi '<div id="root">'              || fail "SPA served"
curl -fs "$BASE/api/openapi.json" | grep -q '"Legate API"'  || fail "API proxied"
curl -fs "$BASE/api/docs" >/dev/null                        || fail "swagger"

# real signup through the proxy (real Supabase call)
# Override the full address with E2E_EMAIL, or just the domain with E2E_TEST_DOMAIN.
EMAIL="${E2E_EMAIL:-e2e+$(date +%s)@${E2E_TEST_DOMAIN:?set E2E_TEST_DOMAIN or E2E_EMAIL}}"
# SignupRequest is zero-knowledge: client supplies wrapped CEK material.
# Random base64 of the correct sizes stands in for WebCrypto output.
ENC_CEK=$(openssl rand -base64 48 | tr -d '\n')   # 32-byte CEK + 16-byte GCM tag
CEK_IV=$(openssl rand -base64 12 | tr -d '\n')
SALT=$(openssl rand -base64 16 | tr -d '\n')
SIGNUP_RESP=$(curl -fs -X POST "$BASE/api/auth/signup" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Phase1-e2e-pass!9\",\"encrypted_cek\":\"$ENC_CEK\",\"cek_iv\":\"$CEK_IV\",\"pbkdf2_salt\":\"$SALT\"}") \
  || fail "signup via proxy (HTTP error)"
echo "$SIGNUP_RESP" | grep -qi 'user\|id\|email'             || fail "signup via proxy (unexpected response: $SIGNUP_RESP)"

# worker/beat alive
docker compose ps --format json | grep -q '"worker".*running' || fail "worker"
docker compose logs beat --tail 20 | grep -qi 'beat'          || fail "beat"

echo "PHASE 1 E2E: PASS"
