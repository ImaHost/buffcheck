const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');
const fs = require('fs');
const { app } = require('electron');

let pyProcess = null;

function getProjectRoot() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return path.join(__dirname, '..');
}

function resolvePythonCommand() {
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH;
  if (process.platform === 'win32') return 'py';
  return 'python3';
}

function resolveBackendLaunch(root) {
  if (app.isPackaged) {
    const exeName =
      process.platform === 'win32' ? 'buffcheck-backend.exe' : 'buffcheck-backend';
    const exePath = path.join(root, exeName);
    if (fs.existsSync(exePath)) {
      return { command: exePath, args: [], cwd: root };
    }
  }
  return {
    command: resolvePythonCommand(),
    args: ['backend/main.py'],
    cwd: app.isPackaged ? root : path.join(__dirname, '..'),
  };
}

function buildEnv(root) {
  const env = {
    ...process.env,
    BUFFCHECK_ROOT: root,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  };

  const bundledTess = path.join(
    root,
    'tesseract',
    process.platform === 'win32' ? 'tesseract.exe' : 'tesseract',
  );
  if (fs.existsSync(bundledTess)) {
    env.TESSERACT_CMD = bundledTess;
    env.PATH = `${path.dirname(bundledTess)}${path.delimiter}${env.PATH || ''}`;
  }

  const tessdata = path.join(root, 'tessdata');
  if (fs.existsSync(tessdata)) {
    env.TESSDATA_PREFIX = tessdata;
  }

  return env;
}

function startPythonBackend(onData) {
  const root = getProjectRoot();
  const launch = resolveBackendLaunch(root);
  const env = buildEnv(root);

  pyProcess = spawn(launch.command, launch.args, {
    cwd: launch.cwd,
    env,
  });

  pyProcess.stdout.setEncoding('utf8');
  const rl = readline.createInterface({ input: pyProcess.stdout });
  rl.on('line', (line) => {
    try {
      const data = JSON.parse(line);
      onData(data);
    } catch (e) {
      console.error('Python 출력 파싱 실패:', line);
    }
  });

  pyProcess.stderr.on('data', (data) => {
    console.error('Python stderr:', data.toString());
  });

  pyProcess.on('error', (err) => {
    console.error('Python 실행 실패:', err);
    onData({
      type: 'error',
      message: `백엔드를 시작하지 못했습니다: ${err.message}`,
    });
  });

  pyProcess.on('exit', (code) => {
    console.log('Python 프로세스 종료:', code);
    pyProcess = null;
  });

  return pyProcess;
}

function sendCommand(cmd) {
  if (pyProcess && pyProcess.stdin.writable) {
    pyProcess.stdin.write(JSON.stringify(cmd) + '\n');
  }
}

function stopPythonBackend() {
  if (pyProcess) {
    pyProcess.kill();
    pyProcess = null;
  }
}

module.exports = {
  startPythonBackend,
  sendCommand,
  stopPythonBackend,
  getProjectRoot,
};
