const { BrowserWindow, screen } = require('electron');
const path = require('path');

let notifyWin = null;

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

function createNotifyOverlay() {
  if (notifyWin && !notifyWin.isDestroyed()) {
    notifyWin.show();
    return notifyWin;
  }

  const display = screen.getPrimaryDisplay();
  const work = display.workArea;

  notifyWin = new BrowserWindow({
    width: 300,
    height: 340,
    x: work.x + 16,
    y: work.y + 16,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    // 드래그하려면 포커스/마우스 이벤트가 필요
    focusable: true,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  notifyWin.setAlwaysOnTop(true, 'screen-saver');
  // 클릭 통과 제거 — 헤더를 드래그해 위치를 옮길 수 있음
  notifyWin.setIgnoreMouseEvents(false);
  loadOverlay(notifyWin, 'notify-overlay');

  notifyWin.on('closed', () => {
    notifyWin = null;
  });

  return notifyWin;
}

function showNotifyOverlay() {
  const win = createNotifyOverlay();
  if (win && !win.isDestroyed()) {
    win.setIgnoreMouseEvents(false);
    win.show();
  }
}

function hideNotifyOverlay() {
  if (notifyWin && !notifyWin.isDestroyed()) {
    notifyWin.hide();
  }
}

function sendBuffUpdate(data) {
  if (notifyWin && !notifyWin.isDestroyed()) {
    notifyWin.webContents.send('buff-update', data);
  }
}

function sendStatus(status) {
  if (notifyWin && !notifyWin.isDestroyed()) {
    notifyWin.webContents.send('status-updated', status);
  }
}

function destroyNotifyOverlay() {
  if (notifyWin && !notifyWin.isDestroyed()) {
    notifyWin.destroy();
    notifyWin = null;
  }
}

module.exports = {
  createNotifyOverlay,
  showNotifyOverlay,
  hideNotifyOverlay,
  sendBuffUpdate,
  sendStatus,
  destroyNotifyOverlay,
  getNotifyWin: () => notifyWin,
};
