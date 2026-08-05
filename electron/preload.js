const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  confirmRegion: (rect) => ipcRenderer.send('region-selected', rect),
  openRegionPicker: () => ipcRenderer.invoke('open-region-picker'),
  cancelRegionPicker: () => ipcRenderer.send('cancel-region-picker'),
  getStatus: () => ipcRenderer.invoke('get-status'),
  startMonitor: () => ipcRenderer.invoke('start-monitor'),
  stopMonitor: () => ipcRenderer.invoke('stop-monitor'),
  setNotifyThreshold: (seconds) =>
    ipcRenderer.invoke('set-notify-threshold', seconds),
  getPatchNotes: () => ipcRenderer.invoke('get-patch-notes'),
  getUpdateStatus: () => ipcRenderer.invoke('get-update-status'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  quitAndInstall: () => ipcRenderer.invoke('quit-and-install'),
  onBuffUpdate: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('buff-update', handler);
    return () => ipcRenderer.removeListener('buff-update', handler);
  },
  onStatusUpdated: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('status-updated', handler);
    return () => ipcRenderer.removeListener('status-updated', handler);
  },
  onUpdateStatus: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('update-status', handler);
    return () => ipcRenderer.removeListener('update-status', handler);
  },
});
