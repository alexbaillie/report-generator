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
`preelectron:build` first runs `../build_exe.ps1` (PowerShell), which PyInstaller-bundles the backend into `dist/report_generator_backend/` per `pyinstaller.spec`. electron-builder then bundles that plus a Windows Ollama runtime (`ollama/win`) as `extraResources`. Windows-focused (NSIS + portable); mac/linux targets are configured but the Ollama bundle is win32-only.

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

### Ollama client & the model gotcha
`services/ollama_client.py` is the single place the model is configured: `OLLAMA_MODEL` env var, **defaulting to `llama3.1:8b`**. Note the mismatch to be aware of: the README/SETUP docs and the Electron model-provisioning code (`REQUIRED_OLLAMA_MODEL`) reference `tinyllama`, and the packaged app only guarantees `tinyllama` is present. Electron starts the backend with `OLLAMA_BASE_URL` set but **not** `OLLAMA_MODEL`, so a packaged build defaults to `llama3.1:8b` unless overridden. Set `OLLAMA_MODEL` explicitly to match whatever model is actually installed.

### Data layer
SQLAlchemy models in `backend/database/models.py`: `Report`, `Document` (FK → report, holds extracted text), `Template` (`content` carries the prompt/structure incl. `AI_use:` lines; `is_default` flag). SQLite at `backend/data/reports.db` (git-ignored). On every startup, `main.py`'s lifespan runs `backup_database()` **then** `init_db()`. Backups (`database/backup.py`) are rotating, content-hash-deduplicated online copies under `data/backups/` (keep 15); they skip empty/unchanged DBs and never fatal-fail startup. There are no migrations — schema is `create_all`; `scripts/update_template_schema.py` handles ad-hoc template data changes.

### Document processing
`services/document_processor.py` extracts text and tables. PDF text via PyPDF2, PDF tables via pdfplumber; `.docx` via python-docx. Legacy `.doc` is unsupported (returns a message). Failures return a bracketed `[Error ...]` string rather than raising.

### DOCX export: every report type exports, some with branded templates
`GET /api/reports/{id}/export-docx` → `services/docx_exporter.py`. Every report can export — `create_report_docx` picks a **profile** via `_select_profile(title)` and, if the title matches ASD/autism, Sunny Hill CDBC, or Psycho-Educational, unzips the matching `backend/templates/*.docx`, parses the report's markdown sections, and patches `word/document.xml` in place via lxml — matching section headings to that profile's `*_SECTION_TARGETS` and filling the front-page table/paragraphs via its front-page filler function. Anything else (Standard Intake, Neuropsych, ...) falls back to `_create_generic_report_docx`, which builds a plain `python-docx` document from scratch (title, patient/report-type line, front-page metadata as a field list, one heading per filled section) — no clinic letterhead, but every template is exportable. `has_branded_template(title)` tells you which path a title will take. Adding a new *branded* exportable report type means adding a template file + its target/label maps + a profile entry in `_select_profile`; no work is needed to make a new template merely exportable — the generic fallback already covers it.

## Conventions
- Backend imports are rooted at `backend/` (e.g. `from services.ollama_client import ...`), so run Python commands from inside `backend/`.
- All services are `async`; blocking work (DOCX build) is offloaded with `run_in_threadpool`.
- Timestamps use timezone-aware UTC (`datetime.now(timezone.utc)`).
- Frontend tests use ts-jest (`jest.config.js`), separate from the Vite/tsc build pipeline.

## Git
The main branch for PRs is **`backup`**, not `main`/`master`. `gh` CLI is installed and authenticated.
