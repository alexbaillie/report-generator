#!/usr/bin/env bash
# Launch the *packaged* Linux app (the AppImage, or its unpacked launcher) the way a
# user would, check it end to end, quit it, and confirm nothing is left running.
#   smoke_test_app_linux.sh <AppImage-or-launcher> [label]
# Env: USE_FUSE=1 runs the AppImage normally (mounted via FUSE) instead of
# extract-and-run; PSYCHREPORT_NO_SANDBOX=1 is passed through to the launcher.
set -uo pipefail

LAUNCH="${1:?usage: smoke_test_app_linux.sh <AppImage-or-launcher> [label]}"
LABEL="${2:-app}"
LOG="$HOME/report-generator-backend.log"
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/PsychReportGen"
OUT="${RUNNER_TEMP:-/tmp}/app-$LABEL.out"
failed=0

fail() { echo "FAIL: $*"; failed=1; }
dump_logs() {
  echo "================ app log ($LOG) ================"; tail -n 80 "$LOG" 2>/dev/null || echo "(no log)"
  echo "================ app stdout/stderr ================"; tail -n 60 "$OUT" 2>/dev/null || echo "(none)"
}
leftovers() { pgrep -fl 'psychreportgen-bin|resources/report_generator_backend|resources/ollama/bin/ollama' || true; }

echo "############ smoke test [$LABEL] ############"
rm -f "$LOG"
rm -rf "$HOME/.config/PsychReportGen" "$DATA_ROOT"

# Electron needs a display; a virtual one does for CI.
Xvfb :99 -screen 0 1280x800x24 >/dev/null 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
export DISPLAY=:99
sleep 2

# Nobody is there to click the "download the AI model?" dialog; the backend starts after it.
export PSYCHREPORT_SKIP_MODEL_PROMPT=1
[ "${USE_FUSE:-0}" = "1" ] || export APPIMAGE_EXTRACT_AND_RUN=1

"$LAUNCH" > "$OUT" 2>&1 &
LAUNCH_PID=$!
echo "launched $LAUNCH (pid $LAUNCH_PID)"

echo "--- waiting for the backend (the app starts it) ---"
healthy=0
for i in $(seq 1 180); do
  if curl -fsS -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then healthy=1; break; fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null && [ -z "$(leftovers)" ]; then fail "the app exited before the backend became healthy"; break; fi
  sleep 1
done
if [ "$healthy" != 1 ]; then fail "backend never became healthy"; dump_logs; exit 1; fi
echo "backend healthy after ~${i}s"

MAIN_PID="$(pgrep -o -f 'psychreportgen-bin' || true)"
echo "Electron main process: ${MAIN_PID:-not found}"
if [ -n "$MAIN_PID" ]; then
  CMDLINE="$(tr '\0' ' ' < "/proc/$MAIN_PID/cmdline")"
  if [ "${PSYCHREPORT_NO_SANDBOX:-}" = "1" ]; then
    case "$CMDLINE" in *--no-sandbox*) echo "PASS forced sandbox fallback was applied";; *) fail "PSYCHREPORT_NO_SANDBOX=1 but --no-sandbox is missing from: $CMDLINE";; esac
  else
    case "$CMDLINE" in *--no-sandbox*) echo "NOTE the launcher fell back to --no-sandbox (this machine can't create the Chromium sandbox)";; *) echo "PASS the Chromium sandbox stays ON where it can work";; esac
  fi
fi

echo "--- bundled Ollama started by the app? ---"
if curl -fsS -m 5 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "PASS bundled Ollama is serving on :11434 ($(curl -fsS -m 5 http://127.0.0.1:11434/api/version))"
else
  fail "bundled Ollama is not serving on :11434"
fi

echo "--- feature smoke test against the packaged app ---"
python3 .github/scripts/smoke_test_backend.py --base http://127.0.0.1:8000 || failed=1

echo "--- data lives in the per-user folder ---"
if [ -f "$DATA_ROOT/data/reports.db" ]; then echo "PASS database is in $DATA_ROOT/data"; else fail "no database at $DATA_ROOT/data"; fi

echo "--- quit the app, then check nothing is left running ---"
if [ -n "$MAIN_PID" ]; then kill -TERM "$MAIN_PID" 2>/dev/null || true; else kill -TERM "$LAUNCH_PID" 2>/dev/null || true; fi
for i in $(seq 1 30); do [ -z "$(leftovers)" ] && break; sleep 1; done
sleep 2
left="$(leftovers)"
if [ -n "$left" ]; then fail "processes left running after quit:"; echo "$left"; pkill -f 'psychreportgen-bin|resources/report_generator_backend|resources/ollama/bin/ollama' || true; else echo "PASS nothing left running after quit"; fi
if curl -fsS -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then fail "backend still answering on :8000 after quit"; fi
if curl -fsS -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then fail "Ollama still answering on :11434 after quit"; fi

[ "$failed" = 0 ] || { dump_logs; echo "SMOKE TEST [$LABEL] FAILED"; exit 1; }
echo "ALL APP CHECKS PASSED [$LABEL]"
