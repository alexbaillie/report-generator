#!/usr/bin/env bash
# Prove the *bundled* macOS Ollama runtime can actually run a model, and that the
# packaged backend can use it. Pulls a tiny model (tinyllama, ~640 MB) so the
# 5 GB real model isn't needed. Usage: ai_generation_check_macos.sh <path/to/App.app>
set -uo pipefail

APP="${1:?usage: ai_generation_check_macos.sh <path/to/PsychReportGen.app>}"
OLLAMA="$APP/Contents/Resources/ollama/ollama"
BACKEND="$APP/Contents/Resources/report_generator_backend/report_generator_backend"
TMP="${RUNNER_TEMP:-/tmp}"
export OLLAMA_HOST=127.0.0.1:11555
export OLLAMA_MODELS="$TMP/ollama-models"
mkdir -p "$OLLAMA_MODELS"

cleanup() { pkill -f "$APP/Contents" 2>/dev/null || true; }
trap cleanup EXIT

echo "--- start the bundled Ollama ---"
"$OLLAMA" serve > "$TMP/ollama-serve.log" 2>&1 &
for i in $(seq 1 60); do curl -fsS -m 2 "http://$OLLAMA_HOST/api/version" >/dev/null 2>&1 && break; sleep 1; done
curl -fsS "http://$OLLAMA_HOST/api/version" || { echo "FAIL: bundled Ollama did not start"; tail -n 40 "$TMP/ollama-serve.log"; exit 1; }
echo

echo "--- pull a tiny model with the bundled binary ---"
"$OLLAMA" pull tinyllama 2>&1 | tail -n 3

echo "--- generate directly with the bundled runtime ---"
curl -fsS -m 300 "http://$OLLAMA_HOST/api/generate" \
  -d '{"model":"tinyllama","prompt":"Say hello in five words.","stream":false,"options":{"num_predict":24}}' > "$TMP/direct.json" \
  || { echo "FAIL: generation through the bundled Ollama failed"; tail -n 60 "$TMP/ollama-serve.log"; exit 1; }
python3 -c "import json; d=json.load(open('$TMP/direct.json')); print('response:', repr(d.get('response'))); assert d.get('response','').strip()"

echo "--- generate through the packaged backend ---"
OLLAMA_BASE_URL="http://$OLLAMA_HOST" OLLAMA_MODEL=tinyllama "$BACKEND" > "$TMP/backend-ai.log" 2>&1 &
for i in $(seq 1 60); do curl -fsS -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 1; done
curl -fsS -m 300 -X POST http://127.0.0.1:8000/api/ai/generate-text \
  -H 'Content-Type: application/json' -d '{"prompt":"Write one short sentence about autumn.","context":""}' > "$TMP/backend.json" \
  || { echo "FAIL: backend could not generate"; tail -n 40 "$TMP/backend-ai.log"; exit 1; }
python3 -c "import json; d=json.load(open('$TMP/backend.json')); print('backend response:', repr(d.get('text'))); assert d.get('text','').strip()"
echo "AI GENERATION CHECK PASSED"
