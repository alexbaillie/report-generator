#!/usr/bin/env bash
# Launch the *packaged* macOS app the way a user would, check it works end to end,
# quit it, and confirm it left nothing running. Usage: smoke_test_app_macos.sh <path/to/App.app>
set -uo pipefail

APP="${1:?usage: smoke_test_app_macos.sh <path/to/PsychReportGen.app>}"
LOG="$HOME/report-generator-backend.log"
DATA_DIR="$HOME/Library/Application Support/PsychReportGen/data"
OUT="${RUNNER_TEMP:-/tmp}/app.out"
failed=0

fail() { echo "FAIL: $*"; failed=1; }

dump_logs() {
  echo "================ app log ($LOG) ================"; tail -n 80 "$LOG" 2>/dev/null || echo "(no log)"
  echo "================ app stdout/stderr ================"; tail -n 40 "$OUT" 2>/dev/null || echo "(none)"
}

rm -f "$LOG"
rm -rf "$HOME/Library/Application Support/PsychReportGen"

# Nobody is there to click the "download the AI model?" dialog; the backend starts after it.
export PSYCHREPORT_SKIP_MODEL_PROMPT=1
"$APP/Contents/MacOS/PsychReportGen" > "$OUT" 2>&1 &
APP_PID=$!
echo "launched app, pid $APP_PID"

echo "--- waiting for the backend (the app starts it) ---"
healthy=0
for i in $(seq 1 180); do
  if curl -fsS -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then healthy=1; break; fi
  if ! kill -0 "$APP_PID" 2>/dev/null; then fail "the app exited before the backend became healthy"; break; fi
  sleep 1
done
if [ "$healthy" != 1 ]; then fail "backend never became healthy"; dump_logs; exit 1; fi
echo "backend healthy after ~${i}s"

echo "--- bundled Ollama started by the app? ---"
if curl -fsS -m 5 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "PASS bundled Ollama is serving on :11434 ($(curl -fsS -m 5 http://127.0.0.1:11434/api/version))"
else
  fail "bundled Ollama is not serving on :11434"
fi

echo "--- feature smoke test against the packaged app ---"
python3 .github/scripts/smoke_test_backend.py --base http://127.0.0.1:8000 || failed=1

echo "--- data lives in the per-user folder ---"
if [ -f "$DATA_DIR/reports.db" ]; then echo "PASS database is in $DATA_DIR"; else fail "no database at $DATA_DIR"; fi

echo "--- quit the app, then check nothing is left running ---"
kill -TERM "$APP_PID" 2>/dev/null || true
for i in $(seq 1 30); do kill -0 "$APP_PID" 2>/dev/null || break; sleep 1; done
if kill -0 "$APP_PID" 2>/dev/null; then fail "the app did not quit within 30s of SIGTERM"; kill -KILL "$APP_PID" 2>/dev/null || true; fi
sleep 3
left=$(pgrep -fl "$APP/Contents" || true)
if [ -n "$left" ]; then fail "processes left running after quit:"; echo "$left"; pkill -f "$APP/Contents" || true; else echo "PASS nothing left running after quit"; fi
if curl -fsS -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then fail "backend still answering on :8000 after quit"; fi

[ "$failed" = 0 ] || { dump_logs; echo "SMOKE TEST FAILED"; exit 1; }
echo "ALL APP CHECKS PASSED"
