const { app } = require('electron');
const path = require('path');

/**
 * 패키징 시 __dirname 이 electron/ipc 아래라 ../dist 로는 UI를 못 찾음.
 * app.getAppPath() + loadFile 로 통일.
 */
function loadAppPage(win, routeHash) {
  const hash = String(routeHash || 'control').replace(/^#\/?/, '');
  if (!app.isPackaged) {
    win.loadURL(`http://localhost:5173/#/${hash}`);
    return;
  }
  const html = path.join(app.getAppPath(), 'dist', 'index.html');
  win.loadFile(html, { hash: `/${hash}` });
}

module.exports = { loadAppPage };
