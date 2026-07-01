#!/usr/bin/env bash
# run_all_tests.sh — Full-system test runner for Legate (Phase 6 / T6 gate).
#
# Runs every automated test suite in order and fails fast on the first error.
# Prerequisite: real credentials must be in .env (root) and backend/.env.
#
# Usage:
#   bash scripts/run_all_tests.sh
#
# To skip the docker build step (e.g. images are already current):
#   SKIP_BUILD=1 bash scripts/run_all_tests.sh
#
# ── §9 must-have regression test map ─────────────────────────────────────────
# B1  no-double-dispatch          → tests/e2e/test_12_checkin_lifecycle.py::test_b1_dispatch_runs_twice_sends_once
# B2  no-re-trigger               → tests/e2e/test_12_checkin_lifecycle.py::test_b2_grace_expiry_creates_exactly_one_trigger
# B4  unpause-on-confirm          → tests/e2e/test_12_checkin_lifecycle.py::test_b4_confirm_resets_pause_state_and_dispatch_resumes
# F1  login flow (Playwright)     → frontend/e2e/signup-verify-login.spec.ts
# S4  token single-use + expiry  → tests/e2e/test_15_security.py (S4 block)
# B9/B10 purge + nested storage  → tests/e2e/test_12_checkin_lifecycle.py::test_b9_b10_full_account_purge
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="docker compose -f $ROOT/docker-compose.yml"

log()  { echo ""; echo "▶  [run_all_tests] $*"; }
pass() { echo "✓  $*"; }
fail() { echo "✗  FAILED: $*"; exit 1; }

# ── Step 1 — Build images and bring the stack up ──────────────────────────────
log "Step 1/4 — Build images and start compose stack …"
if [ "${SKIP_BUILD:-0}" = "1" ]; then
  echo "   SKIP_BUILD=1 — skipping docker compose build"
else
  $COMPOSE build --no-cache || fail "docker compose build --no-cache"
fi

$COMPOSE up -d || fail "docker compose up -d"

# Wait up to 120 s for the API health check to pass.
log "Waiting for /health (timeout 120 s) …"
ELAPSED=0
until $COMPOSE exec -T api curl -fs http://localhost:8000/health | grep -q '"ok"'; do
  if [ $ELAPSED -ge 120 ]; then
    $COMPOSE logs --tail 50
    fail "/health never returned ok within 120 s"
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done
pass "Stack is healthy"

# ── Step 2 — Backend unit tests ───────────────────────────────────────────────
log "Step 2a/4 — Backend unit tests (no DB) …"
$COMPOSE exec -T api pytest tests/ -q --ignore=tests/e2e \
  || fail "Backend unit tests"
pass "Backend unit tests"

# ── Step 3 — Backend E2E tests (real Supabase, ~70 min on free tier) ──────────
log "Step 2b/4 — Backend E2E tests (suites 01–15, ~70 min) …"
$COMPOSE exec -T api pytest tests/e2e/ -q \
  || fail "Backend E2E tests"
pass "Backend E2E tests (125 tests)"

# ── Step 4 — Frontend lint + unit + build + Playwright ────────────────────────
log "Step 3/4 — Frontend lint …"
cd "$ROOT/frontend"
npm run lint || fail "npm run lint"
pass "Frontend lint"

log "Step 3/4 — Frontend unit tests …"
npm run test || fail "npm run test"
pass "Frontend unit tests"

log "Step 3/4 — Frontend build …"
npm run build || fail "npm run build"
pass "Frontend build"

log "Step 4/4 — Playwright E2E …"
npm run test:e2e || fail "Playwright E2E"
pass "Playwright E2E"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  ALL AUTOMATED SUITES PASSED"
echo "══════════════════════════════════════════════════════"
echo ""
echo "Remaining T6 manual steps:"
echo "  4. Lighthouse PWA audit (npm install -g @lhci/cli && lhci autorun --collect.url=http://localhost)"
echo "  5. Golden-path walkthrough (see PHASE_6_DOCKER_DELIVERABLE_FINAL_E2E.md §T6, step 5)"
