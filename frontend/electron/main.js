const { app, BrowserWindow, ipcMain, dialog, protocol } = require('electron');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const os = require('os');

const RENDERER_PROTOCOL = 'app';

protocol.registerSchemesAsPrivileged([
  {
    scheme: RENDERER_PROTOCOL,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);

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

function registerRendererProtocol() {
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    return;
  }

  const distDir = path.normalize(path.join(__dirname, '..', 'dist'));
  protocol.registerFileProtocol(RENDERER_PROTOCOL, (request, callback) => {
    try {
      const url = new URL(request.url);
      let pathname = decodeURIComponent(url.pathname || '');
      if (!pathname || pathname === '/') pathname = '/index.html';
      if (pathname.startsWith('/')) pathname = pathname.slice(1);

      const resolved = path.normalize(path.join(distDir, pathname));
      if (!resolved.startsWith(distDir)) {
        callback({ error: -6 });
        return;
      }

      callback({ path: resolved });
    } catch {
      callback({ error: -6 });
    }
  });
}

async function validateOllamaHasRequiredModels() {
  const tagsUrl = 'http://127.0.0.1:11434/api/tags';
  const tags = await httpGetJson(tagsUrl, 5000);
  const models = Array.isArray(tags?.models) ? tags.models : [];
  const hasTinyLlama = models.some((m) => {
    const name = (m && typeof m.name === 'string') ? m.name : '';
    return name.toLowerCase().startsWith('tinyllama');
  });

  if (!hasTinyLlama) {
    const msg = 'Ollama is running on 127.0.0.1:11434, but the required model "tinyllama" is not available. Close Ollama and restart PsychReportGen so it can start the bundled Ollama with the preloaded model.';
    logToFile(msg);
    if (mainWindow && !mainWindow.isDestroyed()) {
      showErrorInWindow(msg);
    }
    throw new Error(msg);
  }
}

// Backend process handle
let backendProcess = null;
let backendServerPid = null;
let didStartBackend = false;

// Ollama process handle
let ollamaProcess = null;
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

function safeMkdirpSync(dirPath) {
  try {
    fs.mkdirSync(dirPath, { recursive: true });
  } catch {
  }
}

function copyDirRecursiveSync(src, dest) {
  try {
    if (!fs.existsSync(src)) return;
    safeMkdirpSync(dest);
    fs.cpSync(src, dest, { recursive: true, force: true });
  } catch (e) {
    logToFile(`Failed to copy directory from ${src} to ${dest}: ${e && e.message ? e.message : String(e)}`);
  }
}

function httpOk(url, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(Boolean(res.statusCode && res.statusCode >= 200 && res.statusCode < 300));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error('timeout'));
      resolve(false);
    });
  });
}

function httpGetJson(url, timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      const { statusCode } = res;
      if (!statusCode || statusCode < 200 || statusCode >= 300) {
        res.resume();
        reject(new Error(`HTTP ${statusCode || 'unknown'}`));
        return;
      }

      let raw = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        raw += chunk;
      });
      res.on('end', () => {
        try {
          resolve(JSON.parse(raw));
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error('timeout'));
      reject(new Error('timeout'));
    });
  });
}

async function ensureOllamaModelStoreInstalled() {
  try {
    const srcModelStore = app.isPackaged
      ? path.join(process.resourcesPath, 'ollama_model_store')
      : path.join(__dirname, '..', '..', '..', 'ollama', 'model-store');

    const destModelsDir = path.join(app.getPath('userData'), 'ollama', 'models');
    safeMkdirpSync(destModelsDir);

    const hasManifests = fs.existsSync(path.join(destModelsDir, 'manifests'));
    const hasBlobs = fs.existsSync(path.join(destModelsDir, 'blobs'));
    if (hasManifests && hasBlobs) return destModelsDir;

    if (!fs.existsSync(srcModelStore)) {
      logToFile(`Ollama model store not found at: ${srcModelStore}`);
      return destModelsDir;
    }

    logToFile(`Installing Ollama model store from ${srcModelStore} to ${destModelsDir}`);
    copyDirRecursiveSync(srcModelStore, destModelsDir);
    return destModelsDir;
  } catch (e) {
    logToFile(`Failed to ensure Ollama model store: ${e && e.message ? e.message : String(e)}`);
    return path.join(app.getPath('userData'), 'ollama', 'models');
  }
}

async function startOllama() {
  const ollamaTagsUrl = 'http://127.0.0.1:11434/api/tags';

  const alreadyUp = await httpOk(ollamaTagsUrl, 1200);
  if (alreadyUp) {
    try {
      await validateOllamaHasRequiredModels();
      logToFile('Ollama already running on 127.0.0.1:11434; reusing existing instance.');
      return;
    } catch (e) {
      const msg = `Ollama is running but could not validate models: ${e && e.message ? e.message : String(e)}`;
      logToFile(msg);
      throw e;
    }
  }

  const destModelsDir = await ensureOllamaModelStoreInstalled();

  if (process.platform !== 'win32') {
    logToFile('Ollama bundling not configured for this platform; skipping Ollama startup.');
    return;
  }

  const ollamaDir = app.isPackaged
    ? path.join(process.resourcesPath, 'ollama')
    : path.join(__dirname, '..', '..', '..', 'ollama', 'win');
  const ollamaExePath = path.join(ollamaDir, 'ollama.exe');

  if (!fs.existsSync(ollamaExePath)) {
    logToFile(`Bundled Ollama binary not found at: ${ollamaExePath}`);
    return;
  }

  logToFile(`Starting Ollama from: ${ollamaExePath}`);
  ollamaProcess = spawn(
    ollamaExePath,
    ['serve'],
    {
      cwd: ollamaDir,
      detached: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: {
        ...process.env,
        OLLAMA_HOST: '127.0.0.1:11434',
        OLLAMA_MODELS: destModelsDir,
      },
    }
  );

  if (ollamaProcess && ollamaProcess.pid) {
    logToFile(`Ollama process spawned with PID: ${ollamaProcess.pid}`);
  }

  if (ollamaProcess?.stdout) {
    ollamaProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) logToFile(`[OLLAMA] ${output}`);
    });
  }

  if (ollamaProcess?.stderr) {
    ollamaProcess.stderr.on('data', (data) => {
      const output = data.toString().trim();
      if (output) logToFile(`[OLLAMA STDERR] ${output}`);
    });
  }

  if (ollamaProcess) {
    ollamaProcess.on('error', (error) => {
      logToFile(`Ollama process error: ${error.message}`);
    });

    ollamaProcess.on('close', (code, signal) => {
      logToFile(`Ollama process exited with code ${code}${signal ? `, signal: ${signal}` : ''}`);
      ollamaProcess = null;
    });
  }

  const timeoutMs = 60000;
  const intervalMs = 500;
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ok = await httpOk(ollamaTagsUrl, 1500);
    if (ok) {
      await validateOllamaHasRequiredModels();
      logToFile('Ollama is ready');
      return;
    }

    if (!ollamaProcess) {
      const okAfterExit = await httpOk(ollamaTagsUrl, 800);
      if (okAfterExit) {
        await validateOllamaHasRequiredModels();
        logToFile('Ollama is ready');
        return;
      }
      break;
    }

    await new Promise((r) => setTimeout(r, intervalMs));
  }

  logToFile(`Ollama did not become ready within ${timeoutMs / 1000}s.`);
}

// Helper function to get system command path
function getSystemCommandPath(command) {
  const systemRoot = process.env.SystemRoot || 'C:\\Windows';
  const system32 = path.join(systemRoot, 'System32');
  
  // Try multiple possible locations
  const possiblePaths = [
    path.join(system32, 'cmd.exe'),
    path.join(systemRoot, 'SysWOW64', 'cmd.exe'),
    'C:\\Windows\\System32\\cmd.exe',
    'C:\\Windows\\SysWOW64\\cmd.exe',
    'cmd.exe'  // Last resort
  ];
  
  // Return the first path that exists
  for (const p of possiblePaths) {
    try {
      fs.accessSync(p, fs.constants.X_OK);
      return p;
    } catch (e) {
      // Continue to next path
    }
  }
  
  // Fallback to just 'cmd' if nothing else works
  return 'cmd.exe';
}

// Start the backend process
function startBackend(envOverrides = {}) {
  try {
    backendServerPid = null;
    didStartBackend = false;
    // In development, use the repo-root dist output
    // In production, use the packaged resources directory
    const backendDir = (process.env.NODE_ENV === 'development')
      ? path.join(__dirname, '..', '..', '..', 'dist', 'report_generator_backend')
      : path.join(process.resourcesPath, 'report_generator_backend');

    const backendExePath = path.join(backendDir, 'report_generator_backend.exe');
    const backendBatPath = path.join(backendDir, 'run_backend.bat');
    const backendUnixPath = path.join(backendDir, 'report_generator_backend');

    const isWindows = process.platform === 'win32';

    const hasWindowsLauncher = fs.existsSync(backendExePath) || fs.existsSync(backendBatPath);
    const hasUnixLauncher = fs.existsSync(backendUnixPath);

    if ((isWindows && !hasWindowsLauncher) || (!isWindows && !hasUnixLauncher)) {
      const expected = isWindows
        ? `${backendExePath} or ${backendBatPath}`
        : backendUnixPath;
      const msg = `Backend launcher not found. Expected: ${expected}`;
      logToFile(msg);
      if (mainWindow && !mainWindow.isDestroyed()) {
        showErrorInWindow(msg);
      }
      return;
    }

    if (!isWindows) {
      try {
        fs.chmodSync(backendUnixPath, 0o755);
      } catch (e) {
        logToFile(`Failed to chmod backend binary (${backendUnixPath}): ${e && e.message ? e.message : String(e)}`);
      }

      logToFile(`Starting backend binary from: ${backendUnixPath}`);
      backendProcess = spawn(
        backendUnixPath,
        [],
        {
          cwd: backendDir,
          detached: false,
          stdio: ['ignore', 'pipe', 'pipe'],
          env: { ...process.env, ...envOverrides },
        }
      );
    } else if (fs.existsSync(backendExePath)) {
      logToFile(`Starting backend exe from: ${backendExePath}`);

      backendProcess = spawn(
        backendExePath,
        [],
        {
          cwd: backendDir,
          detached: false,
          stdio: ['ignore', 'pipe', 'pipe'],
          windowsHide: true,
          env: { ...process.env, ...envOverrides },
        }
      );
    } else {
      const cmdPath = getSystemCommandPath('cmd.exe');
      logToFile(`Starting backend bat from: ${backendBatPath}`);
      logToFile(`Using command processor at: ${cmdPath}`);

      backendProcess = spawn(
        cmdPath,
        ['/c', backendBatPath],
        {
          cwd: backendDir,
          detached: false,
          stdio: ['ignore', 'pipe', 'pipe'],
          shell: false,
          windowsHide: true,
          env: { ...process.env, ...envOverrides },
        }
      );
    }

    if (backendProcess && backendProcess.pid) {
      logToFile(`Backend process spawned with PID: ${backendProcess.pid}`);
      didStartBackend = true;
    }

    // Wait for backend to actually be reachable
    waitForBackendReady();

    // Log backend output
    backendProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      logToFile(`[BACKEND] ${output}`);

      const pidMatch = output.match(/Started server process \[(\d+)\]/);
      if (pidMatch && pidMatch[1]) {
        backendServerPid = Number(pidMatch[1]);
        if (!Number.isNaN(backendServerPid)) {
          logToFile(`Detected backend server PID: ${backendServerPid}`);
        } else {
          backendServerPid = null;
        }
      }
      
      // Check if backend is ready
      if (output.includes('Uvicorn running on') || output.includes('Application startup complete')) {
        if (mainWindow && !mainWindow.isDestroyed()) {
          handleBackendReady();
          mainWindow.webContents.send('backend-ready');
        }
      }
    });

    backendProcess.stderr.on('data', (data) => {
      const errorOutput = data.toString().trim();
      logToFile(`[BACKEND STDERR] ${errorOutput}`);

      // Capture the actual Uvicorn server process PID so we can reliably stop it on app exit.
      // Example: "INFO:     Started server process [2692]"
      const pidMatch = errorOutput.match(/Started server process \[(\d+)\]/);
      if (pidMatch && pidMatch[1]) {
        backendServerPid = Number(pidMatch[1]);
        if (!Number.isNaN(backendServerPid)) {
          logToFile(`Detected backend server PID: ${backendServerPid}`);
        } else {
          backendServerPid = null;
        }
      }

      // Uvicorn and other libraries often write non-fatal logs to stderr.
      // Only surface an in-app error for likely-fatal patterns.
      const looksFatal = /\b(traceback|exception|fatal|critical|error)\b/i.test(errorOutput);
      if (looksFatal && mainWindow && !mainWindow.isDestroyed()) {
        showErrorInWindow(`Backend error: ${errorOutput}`);
      }
    });

    backendProcess.on('error', (error) => {
      const errorMsg = `Backend process error: ${error.message}\n` +
                     `Working Directory: ${backendDir}`;
      logToFile(errorMsg);
      console.error(errorMsg);
      
      if (mainWindow && !mainWindow.isDestroyed()) {
        showErrorInWindow(`Failed to start backend: ${error.message}\n\nCheck the log file for more details.`);
      }
    });

    backendProcess.on('close', (code, signal) => {
      const exitMsg = `Backend process exited with code ${code}${signal ? `, signal: ${signal}` : ''}`;
      logToFile(exitMsg);
      
      if (code !== 0 && code !== null) {
        console.error(exitMsg);
        if (mainWindow && !mainWindow.isDestroyed()) {
          showErrorInWindow(`Backend process exited with code ${code}. Check the log file for details.`);
        }
      }
      
      backendProcess = null;
    });

    // Ensure process is killed when app exits
    const cleanup = () => {
      if (backendProcess) {
        logToFile('Terminating backend process...');
        if (process.platform === 'win32') {
          spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
        } else {
          backendProcess.kill();
        }
      }

      if (process.platform === 'win32' && backendServerPid) {
        spawn('taskkill', ['/pid', String(backendServerPid), '/f', '/t']);
      }
    };
    
    process.on('exit', cleanup);
    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

  } catch (error) {
    logToFile(`Failed to start backend: ${error.message}`);
  }
}

// Stop the backend process
function isPidAlive(pid) {
  if (!pid || typeof pid !== 'number') return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function stopBackendSync() {
  try {
    if (process.platform !== 'win32') {
      stopBackend();
      return;
    }

    const pidsToKill = [];
    if (backendProcess && backendProcess.pid) pidsToKill.push(backendProcess.pid);
    if (backendServerPid && backendServerPid !== backendProcess?.pid) pidsToKill.push(backendServerPid);

    for (const pid of pidsToKill) {
      spawnSync('taskkill', ['/pid', String(pid), '/f', '/t'], { stdio: 'ignore', windowsHide: true });
    }

    if (didStartBackend) {
      spawnSync('taskkill', ['/im', 'report_generator_backend.exe', '/f', '/t'], { stdio: 'ignore', windowsHide: true });
    }

    const start = Date.now();
    const timeoutMs = 4000;
    while (Date.now() - start < timeoutMs) {
      if (!isPidAlive(backendServerPid) && !isPidAlive(backendProcess?.pid)) {
        break;
      }
      spawnSync('powershell', ['-NoProfile', '-Command', 'Start-Sleep -Milliseconds 150'], { stdio: 'ignore', windowsHide: true });
    }
  } finally {
    backendProcess = null;
    backendServerPid = null;
    didStartBackend = false;
  }
}

function stopOllama() {
  if (ollamaProcess) {
    logToFile('Stopping Ollama process...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(ollamaProcess.pid), '/f', '/t']);
    } else {
      ollamaProcess.kill();
    }
    ollamaProcess = null;
  }
}

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

  // In some packaging modes, the launcher process can exit and leave the Uvicorn server process running.
  // Always attempt to kill the server PID if we saw it.
  if (process.platform === 'win32' && backendServerPid) {
    logToFile(`Stopping backend server process PID: ${backendServerPid}`);
    spawn('taskkill', ['/pid', String(backendServerPid), '/f', '/t']);
    backendServerPid = null;
  }

  if (process.platform === 'win32' && didStartBackend) {
    spawn('taskkill', ['/im', 'report_generator_backend.exe', '/f', '/t']);
    didStartBackend = false;
  }
}

let mainWindow;
let isBackendReady = false;

// Enforce single-instance behavior (prevents double-launch port collisions)
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function handleBackendReady() {
  if (isBackendReady) return;
  isBackendReady = true;
  logToFile('Backend is ready');

  if (mainWindow && !mainWindow.isDestroyed()) {
    // Reload the window to show the actual app
    if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    } else {
      mainWindow.loadURL(`${RENDERER_PROTOCOL}://./`);
    }
    mainWindow.show();
  }
}

function waitForBackendReady() {
  const url = 'http://127.0.0.1:8000/health';
  const timeoutMs = 60000;
  const intervalMs = 500;
  const start = Date.now();

  const tryOnce = () => {
    const req = http.get(url, (res) => {
      // Drain response
      res.resume();

      if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
        handleBackendReady();
        return;
      }
    });

    req.on('error', () => {
      // Backend not ready yet
    });

    req.setTimeout(2000, () => {
      req.destroy(new Error('health check timeout'));
    });
  };

  const timer = setInterval(() => {
    if (isBackendReady) {
      clearInterval(timer);
      return;
    }

    if (Date.now() - start > timeoutMs) {
      clearInterval(timer);
      const msg = `Backend did not become ready within ${timeoutMs / 1000}s.`;
      logToFile(msg);
      if (mainWindow && !mainWindow.isDestroyed()) {
        showErrorInWindow(msg);
      }
      return;
    }

    tryOnce();
  }, intervalMs);

  // Try immediately too
  tryOnce();
}

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
    // ERR_ABORTED (-3) is commonly triggered by interrupted navigations (e.g., a second loadFile)
    // and is not a real failure.
    if (errorCode === -3) {
      logToFile(`Navigation aborted for ${validatedURL}: ${errorDescription} (Code: ${errorCode})`);
      return;
    }

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

  // Only open DevTools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
    logToFile('Developer Tools opened for debugging');
  }

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
    logToFile(`Platform: ${process.platform} ${process.arch}`);
    logToFile(`SystemRoot: ${process.env.SystemRoot || 'Not set'}`);
    logToFile(`PATH: ${process.env.PATH || 'Not set'}`);
    
    // Only open DevTools in development
    if (process.env.NODE_ENV === 'development') {
      mainWindow.webContents.openDevTools();
    }
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

      mainWindow.loadURL(`${RENDERER_PROTOCOL}://./`).catch(error => {
        if (error && typeof error.message === 'string' && error.message.includes('ERR_ABORTED')) {
          logToFile(`Navigation aborted while loading index.html: ${error.message}`);
          return;
        }
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
  registerRendererProtocol();
  createWindow();
  
  // Start Ollama + backend when in production
  if (process.env.NODE_ENV !== 'development') {
    (async () => {
      logToFile('Starting Ollama + backend processes...');
      await startOllama();
      startBackend({ OLLAMA_BASE_URL: 'http://127.0.0.1:11434' });
    })().catch((e) => {
      logToFile(`Failed to start Ollama/backend: ${e && e.message ? e.message : String(e)}`);
      startBackend({ OLLAMA_BASE_URL: 'http://127.0.0.1:11434' });
    });
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
  stopBackendSync();
  stopOllama();
  
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
  stopOllama();
  
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
    if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    } else {
      mainWindow.loadURL(`${RENDERER_PROTOCOL}://./`);
    }
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
