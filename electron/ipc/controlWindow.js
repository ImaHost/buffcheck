const { BrowserWindow } = require('electron');
const path = require('path');

let controlWin = null;

function getDevUrl(hash) {
  return `http://localhost:5173/#/${hash}`;
}

function getProdUrl(hash) {
  return `file://${path.join(__dirname, '..', 'dist', 'index.html')}#/${hash}`;
}

function loadPage(win, hash) {
  const isDev = !require('electron').app.isPackaged;
  win.loadURL(isDev ? getDevUrl(hash) : getProdUrl(hash));
}

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
  loadPage(controlWin, 'control');

  controlWin.on('closed', () => {
    controlWin = null;
    // 알림 오버레이가 남아 있어도 컨트롤 창이 닫히면 앱 종료
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
