const fs = require('fs');
const path = require('path');
const { app } = require('electron');
const { getProjectRoot } = require('./pyBridge');

function patchNotesPath() {
  if (app.isPackaged) {
    return path.join(getProjectRoot(), 'PATCHNOTES.md');
  }
  return path.join(__dirname, '..', 'PATCHNOTES.md');
}

function readPatchNotes() {
  const file = patchNotesPath();
  try {
    if (!fs.existsSync(file)) {
      return { ok: false, text: '패치노트 파일이 없습니다.', path: file };
    }
    return {
      ok: true,
      text: fs.readFileSync(file, 'utf8'),
      path: file,
      version: app.getVersion(),
    };
  } catch (err) {
    return { ok: false, text: err.message || String(err), path: file };
  }
}

module.exports = { readPatchNotes, patchNotesPath };
