# Psychological Report Generator

A fully offline desktop application for generating psychological reports using local AI.

## Features

- 📝 Generate psychological reports from session notes and test results
- 🔒 Fully offline and secure with encrypted local storage
- 🤖 AI-powered report generation using Ollama (TinyLLaMA)
- 📄 Document upload and processing
- 💾 Local SQLite database with encryption
- 🎨 Modern UI built with React and TailwindCSS

## Tech Stack

- **Frontend**: React + TailwindCSS + TypeScript
- **Desktop**: Electron
- **Backend**: FastAPI (Python)
- **Database**: SQLite with encryption
- **AI**: Ollama (TinyLLaMA model)
- **Testing**: Jest, React Testing Library, Pytest

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Ollama installed locally

## Installation

### 1. Install Ollama and TinyLLaMA model

```bash
# Install Ollama from https://ollama.ai
# Then pull the TinyLLaMA model
ollama pull tinyllama
```

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

This will create distributable packages in the `frontend/dist` directory.

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

- All data is stored locally in an encrypted SQLite database
- No internet connection required after initial setup
- Patient data never leaves your machine

## License

Copyright © 2025. All Rights Reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without express written permission from the copyright holder.
