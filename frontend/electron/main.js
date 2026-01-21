const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

// Global uncaught exception handler
process.on('uncaughtException', (error) => {
  const errorMsg = `Uncaught Exception: ${error}\n${error.stack}`;
  console.error(errorMsg);
  logToFile(errorMsg);
  
  if (mainWindow) {
    showErrorInWindow(`Application Error: ${error.message}`);
  } else {
    dialog.showErrorBox('Application Error', `An unexpected error occurred: ${error.message}\n\nCheck the log file for more details.`);
  }
});

// Backend process handle
let backendProcess = null;
const logStream = fs.createWriteStream(
  path.join(os.homedir(), 'report-generator-backend.log'),
  { flags: 'a' }
);

// Check if log stream is writable
function isLogStreamWritable() {
  return logStream && !logStream.destroyed && !logStream.writableEnded;
}

// Log function with timestamp and error handling
function logToFile(message) {
  try {
    if (isLogStreamWritable()) {
      const timestamp = new Date().toISOString();
      logStream.write(`[${timestamp}] ${message}\n`, (error) => {
        if (error) {
          console.error('Failed to write to log file:', error);
        }
      });
    }
  } catch (error) {
    console.error('Logging error:', error);
  }
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
  logToFile('Creating main window...');
  
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
    show: true, // Show window immediately
    title: 'PsychReportGen',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Window event logging
  mainWindow.on('show', () => {
    logToFile('Window shown');
  });

  mainWindow.on('focus', () => {
    logToFile('Window focused');
  });

  mainWindow.on('maximize', () => {
    logToFile('Window maximized');
  });

  mainWindow.on('minimize', () => {
    logToFile('Window minimized');
  });

  mainWindow.on('restore', () => {
    logToFile('Window restored');
    mainWindow.focus();
  });

  mainWindow.on('closed', () => {
    logToFile('Window closed');
    mainWindow = null;
  });

  // Error handling for failed page loads
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    const errorMsg = `Failed to load ${validatedURL}: ${errorDescription} (Code: ${errorCode}, Main Frame: ${isMainFrame})`;
    console.error(errorMsg);
    logToFile(errorMsg);
    
    if (isMainFrame) {
      showErrorInWindow(`Failed to load page: ${validatedURL}\n\n${errorDescription} (${errorCode})`);
    }
  });
  
  // Handle renderer process crashes
  mainWindow.webContents.on('render-process-gone', (event, details) => {
    const errorMsg = `Renderer process crashed: ${JSON.stringify(details, null, 2)}`;
    console.error(errorMsg);
    logToFile(errorMsg);
    
    showErrorInWindow(
      'Application Error',
      'The application window has crashed. Please restart the application.\n\n' +
      `Reason: ${details.reason || 'unknown'}\n` +
      `Exit code: ${details.exitCode || 'unknown'}`
    );
  });
  
  // Enable DevTools in production for debugging
  mainWindow.webContents.openDevTools();
  logToFile('Developer Tools opened for debugging');

  // Log when the window is ready to show
  mainWindow.once('ready-to-show', () => {
    logToFile('Window ready to show');
    mainWindow.show();
    mainWindow.focus();
    
    // Additional debug information
    logToFile(`App version: ${app.getVersion()}`);
    logToFile(`Electron version: ${process.versions.electron}`);
    logToFile(`Chrome version: ${process.versions.chrome}`);
    logToFile(`Node version: ${process.versions.node}`);
  });

  // Load the app
  const loadApp = () => {
    if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
      logToFile('Loading development server...');
      loadDevServer(mainWindow);
      mainWindow.webContents.openDevTools();
    } else {
      const indexPath = path.join(__dirname, '../dist/index.html');
      logToFile(`Loading production build from: ${indexPath}`);
      
      // Verify file exists in production
      if (!fs.existsSync(indexPath)) {
        const errorMsg = `Production build not found at: ${indexPath}`;
        logToFile(errorMsg);
        showErrorInWindow(errorMsg);
        return;
      }

      mainWindow.loadFile(indexPath).catch(error => {
        const errorMsg = `Failed to load index.html: ${error.message}`;
        logToFile(errorMsg);
        showErrorInWindow(errorMsg);
      });
      
      mainWindow.webContents.on('did-finish-load', () => {
        logToFile('Main window content loaded');
        if (!isBackendReady) {
          logToFile('Backend not ready, showing loading screen');
          showLoadingScreen();
        }
      });
    }
  };

  loadApp();
}

// Helper function to show errors in the window
function showErrorInWindow(message) {
  if (!mainWindow) return;
  
  mainWindow.webContents.executeJavaScript(`
    document.body.innerHTML = '<div style="padding: 2rem; color: #fecaca; background: #7f1d1d; font-family: Arial, sans-serif; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">\
      <h1 style="color: #fca5a5; margin-bottom: 1rem; font-size: 1.5rem;">Application Error</h1>\
      <div style="background: #991b1b; padding: 1rem; border-radius: 0.25rem; margin: 1rem 0; max-width: 600px; overflow: auto;">\
        <pre style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-family: monospace;">${message.replace(/[\\'"`]/g, '\\$&')}</pre>\
      </div>\
      <p style="margin-top: 1rem;">Please check the log file at: ${path.join(os.homedir(), 'report-generator-backend.log')}</p>\
      <button onclick="window.location.reload()" style="margin-top: 1.5rem; padding: 0.5rem 1.5rem; background: #ef4444; color: white; border: none; border-radius: 0.25rem; cursor: pointer; font-size: 1rem;">\
        Reload Application\
      </button>\
    </div>';
  `);
}

// Helper function to show loading screen
function showLoadingScreen() {
  if (!mainWindow) return;
  
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

app.whenReady().then(() => {
  logToFile('App is ready');
  createWindow();
  
  // Start the backend when in production
  if (process.env.NODE_ENV !== 'development') {
    logToFile('Starting backend process...');
  }
  // Always start backend in production, even if logging fails
  if (process.env.NODE_ENV !== 'development') {
    startBackend();
  }

  // On macOS it's common to re-create a window when the dock icon is clicked
  app.on('activate', () => {
    logToFile('App activated');
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}).catch(error => {
  const errorMsg = `Failed to start application: ${error.message}`;
  logToFile(errorMsg);
  console.error(errorMsg);
});

app.on('window-all-closed', () => {
  logToFile('All windows closed');
  stopBackend();
  
  // On macOS it's common for applications to stay open until the user quits explicitly
  if (process.platform !== 'darwin') {
    logToFile('Quitting application');
    app.quit();
  } else {
    logToFile('App remains active (macOS)');
  }
});

// Handle app quit
let isQuitting = false;

app.on('before-quit', () => {
  if (!isQuitting) {
    isQuitting = true;
    logToFile('Application is about to quit');
  }
});

app.on('will-quit', (event) => {
  logToFile('Application will quit');
  stopBackend();
  
  // Close log stream if it's still open
  if (isLogStreamWritable()) {
    logStream.end(() => {
      console.log('Log stream closed');
    });
  }
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
