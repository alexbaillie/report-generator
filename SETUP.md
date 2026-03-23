# Setup Guide - Psychological Report Generator

This guide will walk you through setting up the Psychological Report Generator on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.9 or higher**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Node.js 18 or higher**
   - Download from [nodejs.org](https://nodejs.org/)
   - Verify: `node --version` and `npm --version`

3. **Ollama**
   - Download from [ollama.ai](https://ollama.ai)
   - Install the TinyLLaMA model: `ollama pull tinyllama`
   - Verify Ollama is running: `ollama list`

Note:

- For development, you should install Ollama and `tinyllama` locally.
- For packaged desktop builds (Windows installer), the Ollama runtime is bundled with the app. If `tinyllama` is missing, the app will prompt the user to download it (requires internet) or import an offline models folder.

## Step 1: Backend Setup

### 1.1 Navigate to backend directory
```bash
cd backend
```

### 1.2 Create a virtual environment (recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Install Python dependencies
```bash
pip install -r requirements.txt
```

### 1.4 Initialize database and seed data
```bash
python seed_data.py
```

### 1.5 Start the backend server
```bash
python main.py
```

The backend API should now be running at `http://localhost:8000`

You can verify by visiting `http://localhost:8000` in your browser.

## Step 2: Frontend Setup

Open a new terminal window/tab (keep the backend running).

### 2.1 Navigate to frontend directory
```bash
cd frontend
```

### 2.2 Install Node dependencies
```bash
npm install
```

### 2.3 Start the development server
```bash
npm run dev
```

The frontend should now be running at `http://localhost:5173`

## Step 3: Run as Desktop App (Electron)

### 3.1 Start Electron in development mode
```bash
cd frontend
npm run electron:dev
```

This will:
1. Start the Vite development server
2. Wait for it to be ready
3. Launch the Electron desktop app

## Step 4: Verify Everything Works

1. **Check Ollama**: Ensure Ollama is running
   ```bash
   ollama list
   ```
   You should see `tinyllama` in the list.

2. **Check Backend**: Visit `http://localhost:8000/health`
   - Should return: `{"status": "healthy"}`

3. **Check Frontend**: The app should open automatically
   - You should see the home page with navigation

4. **Test the workflow**:
   - Go to Templates page - you should see 4 default templates
   - Go to Documents page - upload a test document
   - Go to New Report page - try generating a report

## Troubleshooting

### Ollama Connection Error
If you see "Could not connect to Ollama":
- Ensure Ollama is installed and running
- Check if it's accessible at `http://localhost:11434`
- Try: `ollama serve` to start the Ollama service

### Backend Port Already in Use
If port 8000 is already in use:
- Change the port in `backend/main.py` (line with `port=8000`)
- Update the API URL in `frontend/src/services/api.ts`

### Frontend Build Errors
If you encounter build errors:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Database Issues
To reset the database:
```bash
cd backend
rm -rf data/
python seed_data.py
```

## Building for Production

### Build the Desktop App

```bash
cd frontend
npm run build
npm run electron:build
```

The distributable will be created in `frontend/release/`

Note:

- In the current Electron build configuration, artifacts are written under `frontend/release/`.

### Supported Platforms
- **Windows**: Creates `.exe` installer
- **macOS**: Creates `.dmg` installer
- **Linux**: Creates `.AppImage`

## Running Tests

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Next Steps

1. **Customize Templates**: Go to the Templates page and modify or create new templates
2. **Upload Documents**: Add your session notes and test results
3. **Generate Reports**: Create your first psychological report
4. **Export Reports**: Download generated reports for use

## Security Notes

- All data is stored locally in `backend/data/`
- No internet connection is required for normal operation (internet is only used if a user explicitly chooses to download an AI model)
- Patient data never leaves your machine
- Consider encrypting the data directory for additional security

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the README.md for additional information
3. Check that all prerequisites are properly installed

## License

MIT License - See LICENSE file for details
