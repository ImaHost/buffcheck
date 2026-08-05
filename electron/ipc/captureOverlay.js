const { BrowserWindow, screen } = require('electron');
const path = require('path');

let captureWin = null;

function getDevUrl(hash) {
  return `http://localhost:5173/#/${hash}`;
}

function getProdUrl(hash) {
  return `file://${path.join(__dirname, '..', 'dist', 'index.html')}#/${hash}`;
}

function loadOverlay(win, hash) {
  const isDev = !require('electron').app.isPackaged;
  win.loadURL(isDev ? getDevUrl(hash) : getProdUrl(hash));
}

function createCaptureOverlay() {
  if (captureWin && !captureWin.isDestroyed()) {
    captureWin.show();
    captureWin.focus();
    return captureWin;
  }

  const { width, height, x, y } = screen.getPrimaryDisplay().bounds;

  captureWin = new BrowserWindow({
    width,
    height,
    x,
    y,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    fullscreen: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  captureWin.setAlwaysOnTop(true, 'screen-saver');
  loadOverlay(captureWin, 'capture-overlay');

  captureWin.on('closed', () => {
    captureWin = null;
  });

  return captureWin;
}

function hideCaptureOverlay() {
  if (captureWin && !captureWin.isDestroyed()) {
    captureWin.hide();
  }
}

function destroyCaptureOverlay() {
  if (captureWin && !captureWin.isDestroyed()) {
    captureWin.destroy();
    captureWin = null;
  }
}

module.exports = {
  createCaptureOverlay,
  hideCaptureOverlay,
  destroyCaptureOverlay,
  getCaptureWin: () => captureWin,
};
