const { BrowserWindow, screen } = require('electron');
const path = require('path');
const { loadAppPage } = require('../loadAppPage');

let captureWin = null;

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
  loadAppPage(captureWin, 'capture-overlay');

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
