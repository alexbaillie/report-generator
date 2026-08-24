# Psychological Report Generator

A local-first desktop application for generating psychological reports using local AI.

## Features

- 📝 Generate psychological reports from session notes and test results
- 🔒 Local-first (offline by default) with local storage
- 🤖 AI-powered report generation using Ollama (Llama 3.1 8B)
- 📄 Document upload and processing
- 💾 Local SQLite database (encryption is planned)
- 🎨 Modern UI built with React and TailwindCSS

## Tech Stack

- **Frontend**: React + TailwindCSS + TypeScript
- **Desktop**: Electron
- **Backend**: FastAPI (Python)
- **Database**: SQLite (encryption planned)
- **AI**: Ollama (Llama 3.1 8B model)
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

For packaged desktop builds (the Windows installer), the Ollama runtime is bundled with the app. If the model is missing, the app will prompt the user to download `llama3.1:8b` (requires internet) or import an offline models folder.

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
