const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

// Backend process handle
let backendProcess = null;
const logStream = fs.createWriteStream(
  path.join(os.homedir(), 'report-generator-backend.log'),
  { flags: 'a' }
);

// Log function with timestamp
function logToFile(message) {
  const timestamp = new Date().toISOString();
  logStream.write(`[${timestamp}] ${message}\n`);
}

// Start the backend process
function startBackend() {
  try {
    // In development, use the local path
    // In production, look in the resources directory
    let backendPath;
    if (process.env.NODE_ENV === 'development') {
      backendPath = path.join(__dirname, '..', '..', 'dist', 'report_generator_backend', 'run_backend.bat');
    } else {
      backendPath = path.join(process.resourcesPath, '..', 'dist', 'report_generator_backend', 'run_backend.bat');
    }
    
    logToFile(`Starting backend from: ${backendPath}`);
    
    backendProcess = spawn(backendPath, [], {
      cwd: path.dirname(backendPath),
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true  // Use shell to ensure .bat files work correctly
    });

    // Log backend output
    backendProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      logToFile(`[BACKEND] ${output}`);
      
      // Check if backend is ready
      if (output.includes('Uvicorn running on') || output.includes('Application startup complete')) {
        mainWindow.webContents.send('backend-ready');
      }
    });

    backendProcess.stderr.on('data', (data) => {
      logToFile(`[BACKEND ERROR] ${data}`);
    });

    backendProcess.on('error', (error) => {
      logToFile(`Backend process error: ${error.message}`);
    });

    backendProcess.on('close', (code) => {
      logToFile(`Backend process exited with code ${code}`);
      backendProcess = null;
    });

    // Ensure process is killed when app exits
    process.on('exit', () => {
      if (backendProcess) {
        backendProcess.kill();
      }
    });

  } catch (error) {
    logToFile(`Failed to start backend: ${error.message}`);
  }
}

// Stop the backend process
function stopBackend() {
  if (backendProcess) {
    logToFile('Stopping backend process...');
    // Use taskkill on Windows to ensure child processes are also terminated
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      backendProcess.kill();
    }
    backendProcess = null;
  }
}

let mainWindow;
let isBackendReady = false;

function loadDevServer(mainWindow) {
  let port = 5173;
  const maxPort = 5180;
  
  const tryLoad = () => {
    mainWindow.loadURL(`http://localhost:${port}`);
  };
  
  const checkTitle = () => {
    const title = mainWindow.getTitle();
    if (title === 'Psychological Report Generator') {
      if (isBackendReady || process.env.NODE_ENV === 'development') {
        mainWindow.show();
      } else {
        // Wait for backend to be ready
        const checkBackend = setInterval(() => {
          if (isBackendReady) {
            clearInterval(checkBackend);
            mainWindow.show();
          }
        }, 1000);
      }
    } else {
      port++;
      if (port <= maxPort) {
        tryLoad();
      } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
        mainWindow.show();
      }
    }
  };
  
  mainWindow.webContents.on('dom-ready', checkTitle);
  
  // Start the backend before loading the frontend
  if (process.env.NODE_ENV !== 'development') {
    startBackend();
  }
  
  tryLoad();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#1e293b',
    show: false,
  });

  // Load the app
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    loadDevServer(mainWindow);
    mainWindow.webContents.openDevTools();
  } else {
    // In production, show a loading screen while waiting for backend
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    
    mainWindow.webContents.on('did-finish-load', () => {
      if (!isBackendReady) {
        // Show loading screen
        mainWindow.webContents.executeJavaScript(`
          document.body.innerHTML = '<div style="display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial, sans-serif; color: #e2e8f0; background: #1e293b;">\
            <div style="text-align: center; padding: 2rem; background: #1e293b; border-radius: 0.5rem;">\
              <h1 style="font-size: 1.5rem; margin-bottom: 1rem;">Starting Application...</h1>\
              <p>Please wait while we prepare the application.</p>\
              <div style="margin-top: 1.5rem; color: #94a3b8;">\
                <div class="spinner" style="width: 2rem; height: 2rem; border: 0.25rem solid rgba(255, 255, 255, 0.1); border-left-color: #60a5fa; border-radius: 50%; margin: 0 auto; animation: spin 1s linear infinite;"></div>\
                <style>@keyframes spin { to { transform: rotate(360deg); } }</style>\
              </div>\
            </div>\
          </div>';
        `);
      }
    });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();
  
  // Start the backend when in production
  if (process.env.NODE_ENV !== 'development') {
    startBackend();
  }
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle app quit
app.on('will-quit', () => {
  stopBackend();
  logToFile('Application is quitting');
  logStream.end();
});

// Handle backend ready event
ipcMain.on('backend-ready', () => {
  isBackendReady = true;
  logToFile('Backend is ready');
  if (mainWindow) {
    // Reload the window to show the actual app
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    mainWindow.show();
  }
});

// Handle backend errors
ipcMain.on('backend-error', (event, error) => {
  logToFile(`Frontend reported backend error: ${error}`);
  if (mainWindow) {
    mainWindow.webContents.executeJavaScript(`
      document.body.innerHTML = '<div style="padding: 2rem; color: #fecaca; background: #7f1d1d; font-family: Arial, sans-serif;">\
        <h1 style="color: #fca5a5; margin-bottom: 1rem;">Backend Error</h1>\
        <p>Failed to start the application backend. Please check the log file at: ${path.join(os.homedir(), 'report-generator-backend.log')}</p>\
        <p>Error details: ${error}</p>\
        <button onclick="window.location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #ef4444; color: white; border: none; border-radius: 0.25rem; cursor: pointer;">\
          Retry\
        </button>\
      </div>';
    `);
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
