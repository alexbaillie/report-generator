# Developer Handover: Psychological Report Generator (PsychReportGen)

## What the app does

PsychReportGen is a local-first (offline) desktop application for drafting psychological reports.

At a high level it provides:

- Report templates stored locally.
- Document upload (PDF/DOCX) and text extraction.
- AI-assisted text generation and section drafting using a local LLM.
- Local persistence of reports/documents/templates in SQLite.

The desktop app is an Electron shell that starts:

- A React UI (packaged into the Electron app).
- A local FastAPI backend server bound to `127.0.0.1:8000`.
- A local Ollama server (bundled runtime) bound to `127.0.0.1:11434`.

All communication is local HTTP.

## Current technical stack

### Frontend

- React 18 + TypeScript
- Vite (dev server + production build)
- TailwindCSS
- Axios for API calls

Key files:

- `frontend/src/services/api.ts`
  - Axios client pointed at `http://127.0.0.1:8000/api`.
- `frontend/src/pages/*`
  - UI pages for templates, documents, report creation, and editor.

### Desktop packaging / orchestration

- Electron (`frontend/electron/main.js`)
- electron-builder (`frontend/package.json` `build` section)

Responsibilities of `frontend/electron/main.js`:

- Register a custom `app://` protocol for loading the packaged React build.
- Start bundled Ollama (if needed). If the required model (`llama3.1:8b`) is missing, prompt the user to:
  - download it (requires internet), or
  - import an offline models folder, or
  - continue without AI.
- Start the bundled FastAPI backend executable.
- Poll `http://127.0.0.1:8000/health` and only then display the “real” UI.
- Log backend / Ollama stdout + stderr to a logfile in the user home directory.

### Backend

- Python FastAPI + Uvicorn
- SQLAlchemy ORM
- SQLite database stored under `backend/data/reports.db`

Key files:

- `backend/main.py`
  - FastAPI app, routers, `/health` endpoint.
- `backend/api/*`
  - API routers.
- `backend/services/*`
  - AI integration (`ollama_client.py`, `llm_service.py`)
  - Report generation (`report_generator.py`)
  - Document processing (PDF/DOCX extraction)
- `backend/database/*`
  - DB engine/session and SQLAlchemy models.

### AI

- Ollama, accessed via HTTP at `OLLAMA_BASE_URL` (defaults to `http://127.0.0.1:11434`).
- Current model used by the backend: `llama3.1:8b`.

Key files:

- `backend/services/ollama_client.py`
  - `OLLAMA_BASE_URL` is controlled via environment variable.
- `backend/services/llm_service.py`
  - Builds the instruction prompt and calls `generate_text()`.
- `backend/services/report_generator.py`
  - Generates per-section content via Ollama.

## Repository layout (important parts)

- `backend/`
  - FastAPI app + services + sqlite database.
- `frontend/`
  - React UI + Electron main process.
- `build_exe.ps1`
  - Builds a standalone backend executable via PyInstaller.
- `pyinstaller.spec`
  - PyInstaller spec (includes DB and some data folders).
- `ollama/`
  - Staging directory used at build time for bundling the Ollama runtime + model store.
  - This directory is intentionally ignored (large binaries/models). Only `.gitkeep` files are committed.
  - Current release approach:
    - `ollama/win` (Ollama runtime) is bundled into the Electron app.
    - `ollama/model-store` (models) is not bundled into the installer by default to keep NSIS installs reliable.

## How the app starts (runtime flow)

1. User launches the packaged Electron app.
2. Electron creates the BrowserWindow and shows a loading screen until backend is ready.
3. Electron uses a per-user writable model directory: `app.getPath('userData')/ollama/models`.
4. Electron starts Ollama (`ollama.exe serve`) unless an Ollama already exists on `127.0.0.1:11434`.
   - If Ollama is up but `llama3.1:8b` is missing, the user is prompted to download/import/skip.
5. Electron starts the backend (`report_generator_backend.exe`) with `OLLAMA_BASE_URL` and `OLLAMA_MODEL` set (both derived from the same `REQUIRED_OLLAMA_MODEL` constant used to provision the model in step 4, so they can't drift apart).
6. Electron polls `/health` and, once ready, loads the packaged React app.

## Development workflow

### Prerequisites

- Node.js 18+
- Python 3.9+

### Backend (dev)

- Install dependencies:
  - `pip install -r backend/requirements.txt`
- Run backend:
  - `python backend/main.py`

The backend listens on `http://127.0.0.1:8000`.

### Frontend (dev)

- Install dependencies:
  - `cd frontend && npm install`
- Run Vite dev server:
  - `npm run dev`

### Electron (dev)

- From `frontend/`:
  - `npm run electron:dev`

This starts Vite and then launches Electron.

## Production build workflow

### Build backend exe (PyInstaller)

The Electron build runs this automatically via the `preelectron:build` script:

- `report-generator/build_exe.ps1` runs PyInstaller using `pyinstaller.spec`.
- The output ends up under `dist/report_generator_backend/`.

### Prepare bundled Ollama inputs

Before running `npm run electron:build`, populate this staging directory:

- `ollama/win/`
  - Must contain `ollama.exe`.

Optional (recommended for air-gapped clinics as a separate artifact, not bundled in the installer by default):

- `ollama/model-store/`
  - A copy of an Ollama model cache, typically copied from:
    - `C:\Users\<you>\.ollama\models\`
  - Must include the `llama3.1:8b` model under `manifests/` and the referenced blobs under `blobs/`.
  - This can be distributed as an offline “models pack” folder/zip and imported by the app on first run.

These staging directories are ignored by git to avoid committing large binaries.

### Package Electron app

From `frontend/`:

- `npm run electron:build`

Outputs go to:

- `frontend/release/win-unpacked/` (unpacked app folder, best for debugging)
- `frontend/release/PsychReportGen-<version>-Setup.exe` (Windows installer)
- `frontend/release/PsychReportGen-<version>-Portable.exe` (portable exe)

electron-builder bundles extra resources into the app:

- `dist/report_generator_backend` -> `resources/report_generator_backend`
- `ollama/win` -> `resources/ollama`

By default, the model store is not bundled into the installer to avoid multi-GB NSIS payload/extraction failures. Instead, the app prompts the user to download `llama3.1:8b` (internet) or import an offline models folder.

## Logs and debugging

### Log location

Electron writes logs here:

- `C:\Users\<user>\report-generator-backend.log`

This includes:

- `[BACKEND]` and `[BACKEND STDERR]` lines
- `[OLLAMA]` and `[OLLAMA STDERR]` lines

### Common warnings/errors

- FastAPI deprecation warning:
  - `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.`
  - This is non-fatal; backend still starts.

- Ollama bind error:
  - `listen tcp 127.0.0.1:11434: bind: Only one usage ...`
  - Means something is already using port 11434 (often an existing Ollama).
  - The Electron main process tries to reuse the existing Ollama if it has `llama3.1:8b`.

### Useful local checks

- Backend:
  - `http://127.0.0.1:8000/health`
- Ollama:
  - `http://127.0.0.1:11434/api/tags`

## API overview (backend)

Base URL (from frontend): `http://127.0.0.1:8000/api`

- Reports
  - `POST /reports/generate`
  - `POST /reports/generate-section`
  - `GET /reports/`
  - `GET /reports/{id}`
  - `DELETE /reports/{id}`

- Documents
  - `POST /documents/upload`
  - `GET /documents/`
  - `GET /documents/{id}`
  - `DELETE /documents/{id}`

- Templates
  - `POST /templates/`
  - `GET /templates/`
  - `GET /templates/{id}`
  - `PUT /templates/{id}`
  - `DELETE /templates/{id}`

- AI
  - `POST /ai/generate-text`

## Security / privacy notes

- The app is designed to run locally.
- The backend binds to `127.0.0.1` and is not intended to be reachable over LAN.
- Patient data should never leave the machine.

Note: some docs mention “encrypted SQLite”; current implementation uses plain SQLite via SQLAlchemy. If encryption is required, prioritize adding SQLCipher.

## Recommended improvements / roadmap (for a new maintainer)

### High priority

- Replace `@app.on_event("startup")` with FastAPI lifespan handlers to remove deprecation warning.
- Implement actual at-rest encryption for the database (SQLCipher) if this is a product requirement.
- Make ports configurable (8000/11434) with auto-selection when occupied, and ensure frontend uses runtime-discovered backend URL.
- Improve Ollama/model management:
  - A settings screen showing model status and installed models.
  - Optional: ability to import an offline “model pack” zip (current implementation supports importing a models folder from the startup prompt).

### Product / UX

- Add export features (DOCX/PDF) for generated reports.
- Add template variables and a robust template editor.
- Add autosave/version history for reports.

### Backend / reliability

- Add structured logging and clearer error mapping to frontend.
- Add migrations (Alembic) for database schema evolution.
- Add test coverage around document parsing and report generation.

### Build/release

- Document a repeatable release pipeline (CI) including:
  - bundling the Ollama runtime (`ollama/win`), and
  - shipping the installer without the model store (`ollama/model-store`) to avoid multi-GB NSIS payload/extraction failures.
- If fully-offline installs are a requirement, provide a separate offline “models pack” artifact (zip/folder) that can be imported on first run.
- Consider code signing for Windows builds.

## Notes about existing documentation

- `README.md` and `SETUP.md` are oriented to local development.
- `ARCHITECTURE.md` provides a broad architecture overview; this handover doc fills in practical build/release details and current caveats.
