const { autoUpdater } = require('electron-updater');
const { app } = require('electron');

let latestUpdate = {
  status: 'idle',
  currentVersion: app.getVersion(),
  version: null,
  releaseNotes: null,
  progress: null,
  error: null,
};

let broadcast = () => {};

function getUpdateStatus() {
  return {
    ...latestUpdate,
    currentVersion: app.getVersion(),
  };
}

function emitUpdate() {
  broadcast({ type: 'update-status', update: getUpdateStatus() });
}

function setupAutoUpdater(onBroadcast) {
  broadcast = typeof onBroadcast === 'function' ? onBroadcast : () => {};
  latestUpdate.currentVersion = app.getVersion();

  if (!app.isPackaged) {
    latestUpdate.status = 'dev';
    emitUpdate();
    return;
  }

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'checking',
      error: null,
    };
    emitUpdate();
  });

  autoUpdater.on('update-available', (info) => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'available',
      version: info.version,
      releaseNotes: info.releaseNotes || null,
      error: null,
    };
    emitUpdate();
  });

  autoUpdater.on('update-not-available', () => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'up-to-date',
      version: null,
      error: null,
    };
    emitUpdate();
  });

  autoUpdater.on('download-progress', (progress) => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'downloading',
      progress: {
        percent: progress.percent,
        transferred: progress.transferred,
        total: progress.total,
      },
    };
    emitUpdate();
  });

  autoUpdater.on('update-downloaded', (info) => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'ready',
      version: info.version,
      releaseNotes: info.releaseNotes || latestUpdate.releaseNotes,
      progress: null,
      error: null,
    };
    emitUpdate();
  });

  autoUpdater.on('error', (err) => {
    latestUpdate = {
      ...getUpdateStatus(),
      status: 'error',
      error: err?.message || String(err),
    };
    emitUpdate();
  });

  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((err) => {
      latestUpdate = {
        ...getUpdateStatus(),
        status: 'error',
        error: err?.message || String(err),
      };
      emitUpdate();
    });
  }, 2500);
}

function checkForUpdates() {
  if (!app.isPackaged) {
    latestUpdate.status = 'dev';
    emitUpdate();
    return Promise.resolve(getUpdateStatus());
  }
  return autoUpdater.checkForUpdates().then(() => getUpdateStatus());
}

function quitAndInstall() {
  if (latestUpdate.status === 'ready') {
    autoUpdater.quitAndInstall(false, true);
  }
}

module.exports = {
  setupAutoUpdater,
  checkForUpdates,
  quitAndInstall,
  getUpdateStatus,
};
