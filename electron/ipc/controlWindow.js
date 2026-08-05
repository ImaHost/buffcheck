const { BrowserWindow } = require('electron');
const path = require('path');
const { loadAppPage } = require('../loadAppPage');

let controlWin = null;

function createControlWindow() {
  if (controlWin && !controlWin.isDestroyed()) {
    controlWin.show();
    controlWin.focus();
    return controlWin;
  }

  controlWin = new BrowserWindow({
    width: 960,
    height: 700,
    minWidth: 820,
    minHeight: 560,
    resizable: true,
    maximizable: false,
    title: 'BuffCheck',
    backgroundColor: '#0f1a14',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  controlWin.setMenuBarVisibility(false);
  loadAppPage(controlWin, 'control');

  controlWin.on('closed', () => {
    controlWin = null;
    const { app } = require('electron');
    if (!app.isQuitting) {
      app.quit();
    }
  });

  return controlWin;
}

function destroyControlWindow() {
  if (controlWin && !controlWin.isDestroyed()) {
    controlWin.destroy();
    controlWin = null;
  }
}

module.exports = {
  createControlWindow,
  destroyControlWindow,
  getControlWin: () => controlWin,
};
