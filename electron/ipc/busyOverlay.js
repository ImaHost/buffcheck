const { BrowserWindow, screen } = require('electron');
const path = require('path');
const { loadAppPage } = require('../loadAppPage');

let busyWin = null;

function createBusyOverlay(message = '자동등록중...') {
  if (busyWin && !busyWin.isDestroyed()) {
    busyWin.webContents.send('busy-message', { message });
    busyWin.show();
    busyWin.focus();
    return busyWin;
  }

  const display = screen.getPrimaryDisplay();
  const { width, height, x, y } = display.bounds;

  busyWin = new BrowserWindow({
    width,
    height,
    x,
    y,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focusable: true,
    hasShadow: false,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  busyWin.setAlwaysOnTop(true, 'screen-saver');
  busyWin.setIgnoreMouseEvents(false);
  loadAppPage(busyWin, 'busy-overlay');

  busyWin.webContents.once('did-finish-load', () => {
    if (busyWin && !busyWin.isDestroyed()) {
      busyWin.webContents.send('busy-message', { message });
    }
  });

  busyWin.on('closed', () => {
    busyWin = null;
  });

  return busyWin;
}

function showBusyOverlay(message = '자동등록중...') {
  const win = createBusyOverlay(message);
  if (win && !win.isDestroyed()) {
    win.show();
    win.focus();
    win.webContents.send('busy-message', { message });
  }
  return win;
}

function hideBusyOverlay() {
  if (busyWin && !busyWin.isDestroyed()) {
    busyWin.hide();
  }
}

function destroyBusyOverlay() {
  if (busyWin && !busyWin.isDestroyed()) {
    busyWin.destroy();
    busyWin = null;
  }
}

module.exports = {
  showBusyOverlay,
  hideBusyOverlay,
  destroyBusyOverlay,
  getBusyWin: () => busyWin,
};
