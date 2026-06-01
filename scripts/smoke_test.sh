#!/usr/bin/env bash
# L0/L1 acceptance + API smoke (API must be running on port 8000)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Store Intelligence Smoke Test ==="
echo "Target: $BASE_URL"
echo

check "health 200" "curl -sf '$BASE_URL/health' | grep -q '\"status\"'"
check "metrics 200" "curl -sf '$BASE_URL/metrics' | grep -q 'by_department'"
check "funnel 200" "curl -sf '$BASE_URL/funnel' | grep -q 'stages'"
check "anomalies 200" "curl -sf '$BASE_URL/anomalies' | grep -q 'anomalies'"
check "events 200" "curl -sf '$BASE_URL/events' | grep -q 'events'"

if [[ -f DESIGN.md && -f CHOICES.md ]]; then
  echo "PASS  DESIGN.md + CHOICES.md present"
else
  echo "FAIL  documentation files missing"
  FAIL=$((FAIL + 1))
fi

if ls events/*.jsonl >/dev/null 2>&1; then
  echo "PASS  events/*.jsonl exists"
else
  echo "WARN  no events/*.jsonl (run detection or add sample events)"
fi

echo
if [[ $FAIL -eq 0 ]]; then
  echo "All smoke checks passed."
  exit 0
else
  echo "$FAIL check(s) failed."
  exit 1
fi
