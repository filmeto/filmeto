#!/bin/bash
set -euo pipefail

payload="$(cat)"
command="$(printf '%s' "$payload" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("command") or "").strip())')"

if [[ -z "$command" ]]; then
  echo '{"permission":"allow"}'
  exit 0
fi

if [[ "$command" == *"ai_tdd_lint"* ]]; then
  echo '{"permission":"allow"}'
  exit 0
fi

if [[ "$command" =~ (^|[[:space:]])pytest([[:space:]]|$) ]] || [[ "$command" == *"python -m pytest"* ]]; then
  cat <<'EOF'
{"permission":"deny","user_message":"TDD lint: use bin/ai_tdd_lint red <tests> first (expect fail), then implement code, then run bin/ai_tdd_lint green <tests> (expect pass). Direct pytest is blocked for AI coding flow.","agent_message":"Blocked by TDD lint hook: run red/green through bin/ai_tdd_lint."}
EOF
  exit 0
fi

echo '{"permission":"allow"}'
exit 0

