# Psychological Report Generator

A local-first desktop application for generating psychological reports using local AI.

## Features

- 📝 Generate psychological reports from session notes and test results
- 🔒 Local-first (offline by default) with local storage
- 🤖 AI-powered report generation using Meta's Llama 3.1 8B, run locally with Ollama
- 📄 Document upload and processing
- 💾 Local SQLite database (encryption is planned)
- 🎨 Modern UI built with React and TailwindCSS

## Tech Stack

- **Frontend**: React + TailwindCSS + TypeScript
- **Desktop**: Electron
- **Backend**: FastAPI (Python)
- **Database**: SQLite (encryption planned)
- **AI**: Ollama running Meta's Llama 3.1 8B (`llama3.1:8b`) on the user's own computer
- **Testing**: Jest, React Testing Library, Pytest

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Ollama installed locally (recommended for development)

## Installation

### 1. Install Ollama and the Llama 3.1 8B model (development)

```bash
# Install Ollama from https://ollama.ai
# Then pull the model
ollama pull llama3.1:8b
```

For packaged desktop builds (Windows and macOS), the Ollama runtime is bundled with the app. If the model is missing, the app prompts the user to download `llama3.1:8b` (about 4.9 GB, one time, requires internet) or import an offline models folder. If Ollama is already running on the computer with the model installed, the app uses that instead. See [AI model](#ai-model).

### 2. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Install Node dependencies

```bash
cd frontend
npm install
```

## AI model

Reports are written by **Meta's Llama 3.1 8B** (`llama3.1:8b`, 4-bit quantised), run locally through [Ollama](https://ollama.com). Nothing is sent to a cloud service.

- **Download:** about 4.9 GB, one time. After that the app works fully offline.
- **Memory:** about 6 GB of free memory (RAM, or GPU memory) while it is generating.
- **Speed:** a GPU, or an Apple Silicon Mac, makes generation much faster. A computer with no GPU still works but is noticeably slower, and so are Intel Macs.
- **Where the model is set:** once per context, so the two can't drift apart. `REQUIRED_OLLAMA_MODEL` in `frontend/electron/main.js` drives the packaged app (it provisions the model and passes it to the backend as `OLLAMA_MODEL`). When running the backend directly in development, set the `OLLAMA_MODEL` environment variable; it defaults to `llama3.1:8b`.
- **Output is a draft.** AI-generated text must be reviewed by a licensed clinician before use.

## Development

### Start the backend server

```bash
cd backend
python main.py
```

### Start the frontend development server

```bash
cd frontend
npm run dev
```

### Start Electron in development mode

```bash
cd frontend
npm run electron:dev
```

## Building for Production

```bash
cd frontend
npm run build
npm run electron:build
```

This will create distributable packages in the `frontend/release` directory.

## Project Structure

```
psychological-report-generator/
├── backend/                 # FastAPI backend
│   ├── api/                # API routes
│   ├── database/           # Database models and utilities
│   ├── services/           # Business logic
│   ├── tests/              # Pytest tests
│   └── main.py             # Entry point
├── frontend/               # React + Electron frontend
│   ├── public/             # Static assets
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── utils/          # Utilities
│   │   └── App.tsx         # Main app component
│   ├── electron/           # Electron main process
│   └── tests/              # Jest tests
└── README.md
```

## Security

- All data is stored locally in a SQLite database (encryption is planned)
- No internet connection is required for normal operation (internet is only used if a user explicitly chooses to download an AI model)
- Patient data never leaves your machine

## License

Copyright © 2025. All Rights Reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without express written permission from the copyright holder.
