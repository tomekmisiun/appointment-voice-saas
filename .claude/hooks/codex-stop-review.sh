#!/usr/bin/env bash
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

cd "$ROOT" || exit 0

STOP_HOOK_ACTIVE="$(
  python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())' 2>/dev/null || true
)"

if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
  exit 0
fi

if git diff --quiet --exit-code \
  && git diff --cached --quiet --exit-code \
  && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
  exit 0
fi

PROMPT="Jesteś read-only reviewerem. Uruchom 'git status --short',
'git diff --stat', 'git diff', 'git diff --cached' i
'git ls-files --others --exclude-standard', żeby zobaczyć niezacommitowane
zmiany, w tym staged i untracked. Oceń, czy zmiany są spójne, sensowne i nie
zawierają oczywistych błędów (bezpieczeństwo, brak tenant_id, logika w routach
zamiast services, brakujące testy, głupie/zbędne rzeczy).
Zacznij odpowiedź od jednego słowa: APPROVE (jeśli OK) albo FIX (jeśli są
braki). Po FIX wypisz zwięzłą listę konkretnych problemów. Nie modyfikuj
plików."

OUTPUT_FILE="$(mktemp)"
RAW_OUTPUT="$(
  timeout 150 codex exec -s read-only -a never \
    -c model_reasoning_effort=\"low\" \
    -m gpt-5.5 \
    --output-last-message "$OUTPUT_FILE" \
    "$PROMPT" 2>&1
)"
STATUS=$?
OUTPUT="$(cat "$OUTPUT_FILE" 2>/dev/null || true)"
rm -f "$OUTPUT_FILE"

if [[ $STATUS -eq 124 ]]; then
  OUTPUT="FIX
Codex review timed out after 150 seconds."
elif [[ $STATUS -ne 0 ]]; then
  OUTPUT="FIX
Codex review command failed with exit code $STATUS.

$RAW_OUTPUT"
elif [[ "$OUTPUT" != APPROVE* && "$OUTPUT" != FIX* ]]; then
  OUTPUT="FIX
Codex reviewer returned a non-standard verdict. Raw output:

${OUTPUT:-$RAW_OUTPUT}"
fi

REVIEW_OUTPUT="$OUTPUT" python3 - <<'PY'
import json
import os

message = "Codex read-only cross-review verdict:\n" + os.environ["REVIEW_OUTPUT"]
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": message,
    }
}))
PY
