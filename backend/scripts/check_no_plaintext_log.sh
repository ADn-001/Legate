#!/usr/bin/env bash
# NFR-09 / R-03 (Phase 5 T6): Assert that delivery and cleanup worker code
# never logs plaintext capsule content, CEK bytes, or wrapping keys.
#
# Run this in CI (or locally) after any change to the worker tasks:
#   bash backend/scripts/check_no_plaintext_log.sh
#
# Exit code 0 = clean.  Non-zero = violation found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
WORKER_DIR="$BACKEND_DIR/app/worker/tasks"
EMAIL_DIR="$BACKEND_DIR/app/core"

# Patterns that must NOT appear in any logger call or print statement
# in the delivery/cleanup/email paths.
FORBIDDEN_LOG_PATTERNS=(
    'logger\.[a-z]*.*\bcek\b'
    'logger\.[a-z]*.*\bplaintext\b'
    'logger\.[a-z]*.*\bwrapping_key\b'
    'print(.*\bcek\b'
    'print(.*\bplaintext\b'
    'print(.*\bwrapping_key\b'
)

FAILED=0

for pattern in "${FORBIDDEN_LOG_PATTERNS[@]}"; do
    results=$(grep -rn -E "$pattern" \
        "$WORKER_DIR/delivery_tasks.py" \
        "$WORKER_DIR/cleanup_tasks.py" \
        "$EMAIL_DIR/email.py" \
        2>/dev/null || true)
    if [[ -n "$results" ]]; then
        echo "FAIL: potential plaintext logging detected (pattern: $pattern):"
        echo "$results"
        FAILED=1
    fi
done

if [[ $FAILED -eq 0 ]]; then
    echo "OK: no plaintext logging violations found in delivery/cleanup/email paths."
fi

exit $FAILED
