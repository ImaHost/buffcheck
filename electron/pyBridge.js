const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');
const fs = require('fs');
const { app } = require('electron');

let pyProcess = null;

function copyDirSync(src, dst) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dst, { recursive: true });
  for (const name of fs.readdirSync(src)) {
    const from = path.join(src, name);
    const to = path.join(dst, name);
    const stat = fs.statSync(from);
    if (stat.isDirectory()) copyDirSync(from, to);
    else fs.copyFileSync(from, to);
  }
}

/** 설치본: 쓰기 가능한 userData 에 icons/db 시드 */
function ensureUserData() {
  const userRoot = path.join(app.getPath('userData'), 'data');
  const marker = path.join(userRoot, '.seeded-v1');
  const resources = process.resourcesPath;
  fs.mkdirSync(userRoot, { recursive: true });

  if (!fs.existsSync(marker)) {
    const srcIcons = path.join(resources, 'buff_icons');
    const dstIcons = path.join(userRoot, 'buff_icons');
    if (fs.existsSync(srcIcons)) copyDirSync(srcIcons, dstIcons);
    else fs.mkdirSync(dstIcons, { recursive: true });

    const srcDb = path.join(resources, 'icons.db');
    const dstDb = path.join(userRoot, 'icons.db');
    if (fs.existsSync(srcDb) && !fs.existsSync(dstDb)) {
      fs.copyFileSync(srcDb, dstDb);
    }
    fs.writeFileSync(marker, new Date().toISOString(), 'utf8');
  }

  fs.mkdirSync(path.join(userRoot, 'buff_icons'), { recursive: true });
  return userRoot;
}

function getResourcesRoot() {
  if (app.isPackaged) return process.resourcesPath;
  return path.join(__dirname, '..');
}

function getDataRoot() {
  if (app.isPackaged) return ensureUserData();
  return path.join(__dirname, '..');
}

function resolvePythonCommand() {
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH;
  if (process.platform === 'win32') return 'py';
  return 'python3';
}

function resolveBackendLaunch(resourcesRoot, dataRoot) {
  if (app.isPackaged) {
    const exeName =
      process.platform === 'win32' ? 'buffcheck-backend.exe' : 'buffcheck-backend';
    const exePath = path.join(resourcesRoot, exeName);
    if (fs.existsSync(exePath)) {
      return { command: exePath, args: [], cwd: dataRoot };
    }
  }
  return {
    command: resolvePythonCommand(),
    args: ['backend/main.py'],
    cwd: path.join(__dirname, '..'),
  };
}

function buildEnv(resourcesRoot, dataRoot) {
  const env = {
    ...process.env,
    BUFFCHECK_ROOT: dataRoot,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  };

  const bundledTess = path.join(
    resourcesRoot,
    'tesseract',
    process.platform === 'win32' ? 'tesseract.exe' : 'tesseract',
  );
  if (fs.existsSync(bundledTess)) {
    env.TESSERACT_CMD = bundledTess;
    env.PATH = `${path.dirname(bundledTess)}${path.delimiter}${env.PATH || ''}`;
  }

  const tessdata = path.join(resourcesRoot, 'tessdata');
  if (fs.existsSync(tessdata)) {
    env.TESSDATA_PREFIX = tessdata;
  }

  return env;
}

function startPythonBackend(onData) {
  const resourcesRoot = getResourcesRoot();
  const dataRoot = getDataRoot();
  const launch = resolveBackendLaunch(resourcesRoot, dataRoot);
  const env = buildEnv(resourcesRoot, dataRoot);

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
  getProjectRoot: getDataRoot,
  getResourcesRoot,
  getDataRoot,
};
