# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Local-first Electron desktop app that generates psychological reports with a locally-run LLM (Ollama). Three cooperating processes: an **Electron shell** (`frontend/electron/main.js`), a **React/Vite renderer** (`frontend/src`), and a **FastAPI backend** (`backend/`) that talks to **Ollama**. No data leaves the machine; the only network use is optionally downloading an AI model.

## Commands

All commands are run from `backend/` or `frontend/` respectively (not the repo root).

### Backend (`backend/`)
```bash
pip install -r requirements.txt   # install deps
python seed_data.py               # create + seed data/reports.db with default templates
python main.py                    # run API on http://127.0.0.1:8000 (no --reload)
pytest                            # run all tests
pytest tests/test_api.py          # single file
pytest tests/test_api.py::test_health -q   # single test
```

### Frontend (`frontend/`)
```bash
npm install
npm run dev            # Vite dev server on http://localhost:5173
npm run electron:dev   # Vite + Electron together (NODE_ENV=development)
npm test               # Jest (ts-jest + jsdom)
npm test -- -t "name"  # single test by name
```

### Production build
```bash
# from frontend/
npm run electron:build   # tsc + vite build, then electron-builder → frontend/release/
```
`preelectron:build` runs `../build_exe.js`, a small cross-platform dispatcher that calls `build_exe.ps1` on Windows or `build_exe.sh` on macOS/Linux (keep the two build scripts in sync) to PyInstaller-bundle the backend into `dist/report_generator_backend/` (a one-folder build: executable + `_internal/`, not one-file — one-file re-extracts ~100MB to the temp dir on every launch) per `pyinstaller.spec`. `backend/data` is deliberately never bundled (it holds the dev database). electron-builder then bundles that plus a per-platform Ollama runtime as `extraResources` — `ollama/win`, `ollama/mac`, or `ollama/linux` depending on target (`electron/main.js`'s `getOllamaPlatformInfo()` resolves the same per-OS binary at runtime). Each of those `ollama/<platform>/` folders is a local, git-ignored drop location: download the matching Ollama release for that OS and place it there before building — nothing is bundled in the repo itself. Targets: Windows (NSIS + portable) is the primary, hand-tested target. macOS (dmg) is built and smoke-tested by `.github/workflows/build-macos.yml` on GitHub's macOS runners (see "macOS build" below); Linux (AppImage, x64 and arm64) is built and smoke-tested by `.github/workflows/build-linux.yml` (see "Linux build" below). App icons (`assets/icon.ico/.icns/.png`) don't exist yet for any platform (cosmetic gap; electron-builder falls back to a default).

### macOS build
There is no Mac to build on, so macOS is built **and tested** by `.github/workflows/build-macos.yml` on GitHub's macOS runners (Apple Silicon `macos-15`, Intel `macos-15-intel`). Per architecture it runs: backend tests → PyInstaller backend → smoke test of the *packaged backend* (`.github/scripts/smoke_test_backend.py`, usable locally on any OS) → bundled Ollama (`OLLAMA_VERSION`, the same release Windows ships) → electron-builder → `frontend/afterPack.js` ad-hoc signs the app → smoke test of the *packaged app* (`smoke_test_app_macos.sh`: launch, use, SIGTERM, nothing left running) → real inference with the bundled Ollama (`ai_generation_check_macos.sh`, tinyllama). Run it with `gh workflow run "Build macOS" --ref <branch>`; add `-f release_tag=vX.Y.Z` to attach the verified `PsychReportGen-<version>-mac-<arch>.dmg` files to that existing release (only reached if every check passed), otherwise take them from the run's artifacts.
- No Apple Developer ID: the app is ad-hoc signed, not notarized, so Gatekeeper rejects it until the user allows it (System Settings → Privacy & Security → Open Anyway, or `xattr -dr com.apple.quarantine /Applications/PsychReportGen.app`). The ad-hoc seal must stay *valid* (afterPack verifies it) or macOS says "damaged" with no way to open it.
- The app quits when its window closes on macOS too, and SIGTERM/SIGINT quit the whole app (they used to leave the app running and Ollama orphaned).
- `PSYCHREPORT_SKIP_MODEL_PROMPT=1` skips the "download the AI model?" dialog, which an automated test can't click (the backend only starts once it is answered).
- Intel: `cryptography` 49+ publishes no macOS x86_64 wheel, so `backend/requirements.txt` pins `<49` there; a source build links a mismatched OpenSSL into the packaged app and the backend fails to start.
- Not checkable in CI: Gatekeeper's actual prompt, GPU (Metal) inference speed, anything needing a signed-in desktop. Check on a physical Mac before relying on it.

### Linux build
Built and tested by `.github/workflows/build-linux.yml` on GitHub's Ubuntu 22.04 runners (x64 `ubuntu-22.04`, arm64 `ubuntu-22.04-arm`; built on 22.04 so the glibc requirement stays low). Same stages as macOS: backend tests → packaged-backend smoke test → bundled Ollama (`OLLAMA_VERSION`) → electron-builder (AppImage) → smoke test of the *packaged AppImage* under Xvfb (`smoke_test_app_linux.sh`, three ways: default, forced `--no-sandbox`, and FUSE-mounted the way real users run it) → real inference with the bundled Ollama (`ai_generation_check_linux.sh`). Same `release_tag` input attaches the verified AppImages to a release.
- Ollama's Linux release is `bin/ollama` + `lib/ollama/` (not flat like macOS) and ships as `.tar.zst`; `getOllamaPlatformInfo()` returns `bin/ollama` for Linux.
- `afterPack.js` replaces the Electron executable with a launcher (`psychreportgen` runs `psychreportgen-bin`): Chromium's sandbox stays ON where unprivileged user namespaces work and falls back to `--no-sandbox` where they don't (Ubuntu 23.10+ AppArmor blocks them, and an Electron app that can't sandbox refuses to start). `PSYCHREPORT_NO_SANDBOX=1` forces the fallback. The app only loads its own bundled pages and localhost.
- AppImages need FUSE 2 (`libfuse2`) to mount; without it, run with `--appimage-extract-and-run`. They're named `PsychReportGen-<version>-linux-x86_64.AppImage` / `-linux-arm64.AppImage` (arm64 is what `uname -m` calls `aarch64`).
- Size: x64 about 1.78 GB, arm64 about 1.87 GB, against GitHub's 2 GiB release-asset cap (the workflow fails clearly if it is exceeded). Most of it is Ollama's bundled CUDA libraries; if arm64 grows, trim `lib/ollama/cuda_v13`.
- Not checkable in CI: distros other than Ubuntu 22.04, real GPUs (NVIDIA CUDA is bundled; AMD ROCm is not), and AppArmor-restricted desktops (the fallback is exercised only by the forced override).

## Architecture

### Process model & startup order
- **Dev**: you start the backend (`python main.py`) and Vite (`npm run dev`) manually; `npm run electron:dev` launches Electron pointing at the Vite server. In dev, Electron does **not** spawn the backend or Ollama.
- **Packaged**: Electron's `app.whenReady` runs `startOllama()` (spawns bundled `ollama.exe serve`, ensures the model store, prompts to download/import the model if missing) then `startBackend()` (spawns the PyInstaller backend exe). It health-checks `:8000/health` and `:11434/api/tags`, shows a loading screen, and hard-kills both child processes on exit (`taskkill /f /t`). Single-instance lock prevents double-launch port collisions.

### Request flow
Renderer → `frontend/src/services/api.ts` (axios, base `http://127.0.0.1:8000/api`) → FastAPI routers in `backend/api/` → services → SQLite / Ollama.

Routers (mounted in `backend/main.py`): `reports` (`/api/reports`), `documents` (`/api/documents`), `templates` (`/api/templates`), `ai` (`/api/ai`). CORS is wide-open (`allow_origins=["*"]`) because Electron origins vary.

### Report generation is section-by-section, not one shot
1. The renderer calls `POST /api/reports/generate-section` once per section. `report_generator.generate_report_section` builds a per-section prompt from the template's `AI_use:` guidance (parsed out of `Template.content`), the selected documents' extracted text, and section inputs, then calls Ollama.
2. When all sections are ready, `POST /api/reports/generate` assembles the final report — `generate_report` simply concatenates the `additional_inputs` dict into markdown `# Section` blocks and persists a `Report` row. (No further LLM call at assembly time.)
3. `POST /api/ai/generate-text` is a separate free-form edit/generate endpoint (used by the editor) via `llm_service.generate_text_with_llm`.

### Ollama client & model configuration
`services/ollama_client.py` is the single place the model is configured for the backend: `OLLAMA_MODEL` env var, defaulting to `llama3.1:8b`. Electron's `REQUIRED_OLLAMA_MODEL` constant (`electron/main.js`) is the single place it's configured for the packaged app — it drives what `startOllama()` provisions (downloads/prompts for) *and* is passed to the backend as `OLLAMA_MODEL` when spawning it, so the two can't drift apart. (They used to: Electron provisioned `tinyllama` while the backend called `llama3.1:8b`, so a packaged install could prompt successfully yet still fail every generation request against a model that was never downloaded — fixed by making `REQUIRED_OLLAMA_MODEL` the one source of truth.) If you ever change the model, update `REQUIRED_OLLAMA_MODEL` — both provisioning and the backend env var follow from it.

### Data layer
SQLAlchemy models in `backend/database/models.py`: `Report`, `Document` (FK → report, holds extracted text), `Template` (`content` carries the prompt/structure incl. `AI_use:` lines; `is_default` flag). SQLite at `backend/data/reports.db` (git-ignored) in dev; in the packaged app (`sys.frozen`) `DATA_DIR` resolves instead to a persistent per-user folder (`%APPDATA%\PsychReportGen\data` on Windows) — see `_resolve_data_dir` in `database/db.py`. Never derive data paths from `__file__` elsewhere (import `DATA_DIR`); in a frozen build that points at read-only bundle files, not user data. On every startup, `main.py`'s lifespan runs `backup_database()`, **then** `init_db()`, **then** `seed_templates()` (idempotent, reads `seeds/*.json`) so a fresh install always has the default templates. Backups (`database/backup.py`) are rotating, content-hash-deduplicated online copies under `data/backups/` (keep 15); they skip empty/unchanged DBs and never fatal-fail startup. There are no migrations — schema is `create_all`; `scripts/update_template_schema.py` handles ad-hoc template data changes.

### Document processing
`services/document_processor.py` extracts text and tables. PDF text via PyPDF2, PDF tables via pdfplumber; `.docx` via python-docx. Legacy `.doc` is unsupported (returns a message). Failures return a bracketed `[Error ...]` string rather than raising.

### DOCX export: every report type exports, some with branded templates
`GET /api/reports/{id}/export-docx` → `services/docx_exporter.py`. Every report can export — `create_report_docx` picks a **profile** via `_select_profile(title)` and, if the title matches ASD/autism, Sunny Hill CDBC, or Psycho-Educational, unzips the matching `backend/templates/*.docx`, parses the report's markdown sections, and patches `word/document.xml` in place via lxml — matching section headings to that profile's `*_SECTION_TARGETS` and filling the front-page table/paragraphs via its front-page filler function. Anything else (Standard Intake, Neuropsych, ...) falls back to `_create_generic_report_docx`, which builds a plain `python-docx` document from scratch (title, patient/report-type line, front-page metadata as a field list, one heading per filled section) — no clinic letterhead, but every template is exportable. `has_branded_template(title)` tells you which path a title will take. Adding a new *branded* exportable report type means adding a template file + its target/label maps + a profile entry in `_select_profile`; no work is needed to make a new template merely exportable — the generic fallback already covers it.

### Score reports: tables and graphs per test
Each entry under "Tests Administered" in `NewReportPage` can take an uploaded Word/PDF score report and/or pasted tables. `POST /api/score-reports/extract` (`api/score_reports.py` → `services/score_report_extractor.py`) returns every table and graph in document order (a temp file, deleted immediately — score reports carry client identifiers); the user ticks what to keep, and the choices travel as `test_results` on `POST /api/reports/generate`. They are stored in the `report_test_results` table (JSON payload, new table so `create_all` adds it to existing DBs — never put them in `Report.content`) and `GET /api/reports/{id}/export-docx` hands them to `create_report_docx(..., test_results=...)`. `services/docx_test_results.py` then finds each test's block in the Word template (heading + description + *blank score tables* + sometimes an "(insert … graph here)" placeholder), replaces the blank tables/placeholder with the uploaded content, and leaves the block's other text alone; a test with no block in that template gets its own labelled block before the summary/recommendations. Test names are matched loosely (`WIAT-IV` ↔ `WIAT-III`, `ABAS-III` ↔ `ABAS-3`). Known limits: native Word charts and vector-drawn PDF graphs can't be imported (the upload says so); PDF tables are only detected when they have ruling lines; PDF/Word import quality depends on the file, so Word is preferred.

**Two ways a test's tables reach the Word file** (`mode` on each test group, stored in the `report_test_results` payload; default `fill`):
- `fill` — `services/score_fill.py` reads the score report's tables into records (a table counts when its header row has a percentile rank plus a scaled/standard/composite score) and writes them into the *blank cells of the template's own tables*, so the clinic template's look never changes. Matching is deliberately strict because a wrong number in a clinical table is worse than a blank: a template row takes values only from a score-report row with the same code (`SI`, `VCI`, `FSIQ`; `LNS`≡`LN`) or the exact same name; a column is filled only from the same kind of score (scaled ↔ scaled, standard/composite/index ↔ standard); existing cell text is never overwritten; `-` (not administered) puts "Not assessed" in the row's first score cell (rest blank; pending the clinic's final rule for blank sections); two score-report rows with the same code but different values leave that row blank; tables with merged cells are skipped. Cells copy the paragraph mark's run properties, so font/size match the template. Graphs still replace the template's "(insert … graph here)" placeholder (or follow its last table); uploaded tables that aren't score tables are inserted after the template's tables. If *nothing* could be filled it falls back to `insert`.
- `insert` — the template's blank tables are replaced by the uploaded tables, rebuilt faithfully by `docx_test_results._build_table` (merged cells, relative column widths, title row bolded/centred rather than shaded as the header, real header row shaded and repeated).
`create_report_docx(..., fill_report=[])` collects a per-test account (`result`: filled/replaced/added, plus `filled`, `not_administered`, `not_in_report`, `not_in_template`, `ambiguous`, `unfilled_columns`); `GET /api/reports/{id}/export-docx` returns it as the `X-Score-Fill` JSON header (exposed through CORS) and `ReportDetailPage` shows it after a download so a human checks what stayed blank. The extractor returns `merges` (`[row, col, rowspan, colspan]`), `widths`, and marks pictures before the first table `suggested: false` (cover art/logos start unticked). Tested with fake numbers only (`tests/test_score_fill.py`); never commit a real score report.

## Conventions
- Backend imports are rooted at `backend/` (e.g. `from services.ollama_client import ...`), so run Python commands from inside `backend/`.
- All services are `async`; blocking work (DOCX build) is offloaded with `run_in_threadpool`.
- Timestamps use timezone-aware UTC (`datetime.now(timezone.utc)`).
- Frontend tests use ts-jest (`jest.config.js`), separate from the Vite/tsc build pipeline.

## Git
The main branch for PRs is **`backup`**, not `main`/`master`. `gh` CLI is installed and authenticated.
