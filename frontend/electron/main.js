const { app, BrowserWindow } = require('electron');
const path = require('path');

let mainWindow;

function loadDevServer(mainWindow) {
  let port = 5173;
  const maxPort = 5180;
  const tryLoad = () => {
    mainWindow.loadURL(`http://localhost:${port}`);
  };
  const checkTitle = () => {
    const title = mainWindow.getTitle();
    if (title === 'Psychological Report Generator') {
      mainWindow.show();
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
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
