const { app, globalShortcut, ipcMain, BrowserWindow } = require('electron');
const {
  createCaptureOverlay,
  hideCaptureOverlay,
  destroyCaptureOverlay,
} = require('./ipc/captureOverlay');
const {
  createNotifyOverlay,
  showNotifyOverlay,
  hideNotifyOverlay,
  sendBuffUpdate,
  destroyNotifyOverlay,
} = require('./ipc/notifyOverlay');
const {
  createControlWindow,
  destroyControlWindow,
} = require('./ipc/controlWindow');
const { startPythonBackend, sendCommand, stopPythonBackend } = require('./pyBridge');
const {
  setupAutoUpdater,
  checkForUpdates,
  quitAndInstall,
  getUpdateStatus,
} = require('./updater');
const { readPatchNotes } = require('./patchNotes');

const monitorStatus = {
  running: false,
  region: null,
  iconCount: 0,
  matchCount: 0,
  trackedCount: 0,
  notifyThreshold: 30,
  buffs: [],
  detections: [],
  renewals: [],
  lastError: null,
};

function clampThreshold(value) {
  const n = Math.round(Number(value));
  if (!Number.isFinite(n)) return 30;
  return Math.min(60, Math.max(1, n));
}

function computeRenewals(buffs, threshold) {
  return (Array.isArray(buffs) ? buffs : [])
    .filter(
      (b) =>
        typeof b.remaining === 'number' &&
        b.remaining > 0 &&
        b.remaining <= threshold,
    )
    .slice()
    .sort((a, b) => a.remaining - b.remaining);
}

function pushBuffUpdate() {
  sendBuffUpdate({
    buffs: monitorStatus.buffs,
    renewals: monitorStatus.renewals,
    detections: monitorStatus.detections,
    running: monitorStatus.running,
    matchCount: monitorStatus.matchCount,
    trackedCount: monitorStatus.trackedCount,
    iconCount: monitorStatus.iconCount,
    notifyThreshold: monitorStatus.notifyThreshold,
  });
}

function broadcastStatus() {
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed()) {
      win.webContents.send('status-updated', { ...monitorStatus });
    }
  }
}

function setError(message) {
  monitorStatus.lastError = message;
  monitorStatus.running = false;
  hideNotifyOverlay();
  broadcastStatus();
}

app.whenReady().then(() => {
  createControlWindow();
  createNotifyOverlay();

  setupAutoUpdater((payload) => {
    for (const win of BrowserWindow.getAllWindows()) {
      if (!win.isDestroyed()) {
        win.webContents.send('update-status', payload.update || getUpdateStatus());
      }
    }
  });

  startPythonBackend((frameData) => {
    if (frameData?.type === 'error') {
      setError(frameData.message || '백엔드 오류');
      return;
    }

    if (frameData?.type === 'status') {
      if (typeof frameData.running === 'boolean') {
        monitorStatus.running = frameData.running;
      }
      if (typeof frameData.iconCount === 'number') {
        monitorStatus.iconCount = frameData.iconCount;
      }
      if (typeof frameData.notifyThreshold === 'number') {
        monitorStatus.notifyThreshold = clampThreshold(frameData.notifyThreshold);
      }
      if (frameData.running === false) {
        monitorStatus.renewals = [];
        monitorStatus.buffs = [];
        monitorStatus.detections = [];
        monitorStatus.matchCount = 0;
        monitorStatus.trackedCount = 0;
        hideNotifyOverlay();
        sendBuffUpdate({
          buffs: [],
          renewals: [],
          running: false,
          notifyThreshold: monitorStatus.notifyThreshold,
        });
      }
      broadcastStatus();
      return;
    }

    const list = Array.isArray(frameData?.buffs) ? frameData.buffs : [];
    const threshold = monitorStatus.notifyThreshold;
    const renewals = computeRenewals(list, threshold);

    monitorStatus.buffs = list;
    monitorStatus.renewals = renewals;
    monitorStatus.detections = Array.isArray(frameData?.detections)
      ? frameData.detections
      : [];
    if (typeof frameData?.matchCount === 'number') {
      monitorStatus.matchCount = frameData.matchCount;
    }
    if (typeof frameData?.trackedCount === 'number') {
      monitorStatus.trackedCount = frameData.trackedCount;
    } else {
      monitorStatus.trackedCount = list.length;
    }
    monitorStatus.lastError = null;

    pushBuffUpdate();
    broadcastStatus();
  });

  const registered = globalShortcut.register('F8', () => {
    createCaptureOverlay();
  });

  if (!registered) {
    console.error('F8 글로벌 단축키 등록 실패 (다른 프로그램과 충돌 가능)');
  }

  ipcMain.handle('get-status', () => ({
    ...monitorStatus,
    appVersion: app.getVersion(),
  }));

  ipcMain.handle('get-patch-notes', () => readPatchNotes());

  ipcMain.handle('get-update-status', () => getUpdateStatus());

  ipcMain.handle('check-for-updates', async () => {
    try {
      return await checkForUpdates();
    } catch (err) {
      return {
        ...getUpdateStatus(),
        status: 'error',
        error: err?.message || String(err),
      };
    }
  });

  ipcMain.handle('quit-and-install', () => {
    quitAndInstall();
    return { ok: true };
  });

  ipcMain.handle('open-region-picker', () => {
    createCaptureOverlay();
  });

  ipcMain.on('cancel-region-picker', () => {
    hideCaptureOverlay();
  });

  ipcMain.handle('set-notify-threshold', (_event, seconds) => {
    const n = clampThreshold(seconds);
    monitorStatus.notifyThreshold = n;
    sendCommand({ type: 'set_notify_threshold', seconds: n });
    monitorStatus.renewals = computeRenewals(monitorStatus.buffs, n);
    pushBuffUpdate();
    broadcastStatus();
    return { ok: true, notifyThreshold: n };
  });

  ipcMain.handle('start-monitor', () => {
    if (!monitorStatus.region) {
      monitorStatus.lastError = '먼저 감시 영역을 지정하세요.';
      broadcastStatus();
      return { ok: false, error: monitorStatus.lastError };
    }
    monitorStatus.lastError = null;
    sendCommand({
      type: 'set_notify_threshold',
      seconds: monitorStatus.notifyThreshold,
    });
    sendCommand({ type: 'start' });
    monitorStatus.running = true;
    showNotifyOverlay();
    sendBuffUpdate({
      buffs: [],
      renewals: [],
      running: true,
      matchCount: 0,
      trackedCount: 0,
      iconCount: monitorStatus.iconCount,
      notifyThreshold: monitorStatus.notifyThreshold,
    });
    broadcastStatus();
    return { ok: true };
  });

  ipcMain.handle('stop-monitor', () => {
    sendCommand({ type: 'stop' });
    monitorStatus.running = false;
    monitorStatus.renewals = [];
    monitorStatus.matchCount = 0;
    monitorStatus.trackedCount = 0;
    hideNotifyOverlay();
    sendBuffUpdate({
      buffs: [],
      renewals: [],
      running: false,
      notifyThreshold: monitorStatus.notifyThreshold,
    });
    broadcastStatus();
    return { ok: true };
  });

  ipcMain.on('region-selected', (_event, rect) => {
    const region = {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    };
    monitorStatus.region = region;
    monitorStatus.lastError = null;
    sendCommand({
      type: 'set_region',
      ...region,
    });
    hideCaptureOverlay();
    broadcastStatus();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  stopPythonBackend();
  destroyCaptureOverlay();
  destroyNotifyOverlay();
  destroyControlWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
