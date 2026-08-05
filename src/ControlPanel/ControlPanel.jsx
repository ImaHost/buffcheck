import { useEffect, useState } from 'react';
import './ControlPanel.css';

const emptyStatus = {
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
  appVersion: '1.0.0',
};

function formatThreshold(sec) {
  if (sec >= 60) return '1분';
  return `${sec}초`;
}

function updateLabel(update) {
  switch (update?.status) {
    case 'checking':
      return '업데이트 확인 중…';
    case 'available':
      return `새 버전 ${update.version} 발견 — 다운로드 중…`;
    case 'downloading':
      return `업데이트 다운로드 ${Math.round(update.progress?.percent || 0)}%`;
    case 'ready':
      return `v${update.version} 준비됨 — 재시작 시 설치`;
    case 'up-to-date':
      return '최신 버전입니다';
    case 'dev':
      return '개발 모드 — 자동 업데이트 비활성';
    case 'error':
      return `업데이트 오류: ${update.error || '알 수 없음'}`;
    default:
      return '업데이트 대기';
  }
}

export default function ControlPanel() {
  const [status, setStatus] = useState(emptyStatus);
  const [message, setMessage] = useState(null);
  const [logs, setLogs] = useState([]);
  const [threshold, setThreshold] = useState(30);
  const [rightTab, setRightTab] = useState('logs');
  const [patchNotes, setPatchNotes] = useState('');
  const [update, setUpdate] = useState({ status: 'idle' });

  useEffect(() => {
    if (!window.electronAPI?.getStatus) return undefined;

    void window.electronAPI.getStatus().then((s) => {
      setStatus(s);
      if (typeof s?.notifyThreshold === 'number') setThreshold(s.notifyThreshold);
    });
    void window.electronAPI.getPatchNotes?.().then((res) => {
      if (res?.text) setPatchNotes(res.text);
    });
    void window.electronAPI.getUpdateStatus?.().then((u) => {
      if (u) setUpdate(u);
    });

    const offs = [];
    if (window.electronAPI.onStatusUpdated) {
      offs.push(
        window.electronAPI.onStatusUpdated((s) => {
          setStatus(s);
          if (typeof s?.notifyThreshold === 'number') setThreshold(s.notifyThreshold);
          const dets = Array.isArray(s?.detections) ? s.detections : [];
          const ocrDets = dets.filter((d) => d.cropMode && d.cropMode !== 'local');
          if (!ocrDets.length) return;

          const stamp = new Date().toLocaleTimeString();
          const lines = ocrDets.map((d) => {
            if (d.ocrOk && typeof d.remaining === 'number') {
              return `[${stamp}] ${d.name} → ${Math.round(d.remaining)}초 (raw: ${d.ocrRaw || '—'})`;
            }
            const keep =
              typeof d.remaining === 'number'
                ? ` · 로컬 ${Math.round(d.remaining)}초`
                : '';
            return `[${stamp}] ${d.name} → OCR 스킵${keep} | raw: ${d.ocrRaw || '없음'}`;
          });

          setLogs((prev) => {
            const body = (line) => line.replace(/^\[[^\]]+\]\s*/, '');
            const newBodies = lines.map(body).join('|');
            const oldBodies = prev.slice(0, lines.length).map(body).join('|');
            if (newBodies === oldBodies) return prev;
            return [...lines, ...prev].slice(0, 80);
          });
        }),
      );
    }
    if (window.electronAPI.onUpdateStatus) {
      offs.push(window.electronAPI.onUpdateStatus((u) => setUpdate(u || { status: 'idle' })));
    }
    return () => offs.forEach((off) => typeof off === 'function' && off());
  }, []);

  const region = status.region;
  const regionLabel = region
    ? `${region.width}×${region.height} @ (${region.x}, ${region.y})`
    : '아직 지정되지 않음';

  const pickRegion = async () => {
    setMessage(null);
    if (!window.electronAPI?.openRegionPicker) {
      setMessage('Electron 환경에서만 영역 지정이 가능합니다.');
      return;
    }
    await window.electronAPI.openRegionPicker();
    setMessage('화면에서 버프창을 드래그하세요. Esc로 취소할 수 있습니다.');
  };

  const onThresholdChange = async (value) => {
    const n = Math.min(60, Math.max(1, Number(value) || 30));
    setThreshold(n);
    if (window.electronAPI?.setNotifyThreshold) {
      await window.electronAPI.setNotifyThreshold(n);
    }
  };

  const toggleMonitor = async () => {
    setMessage(null);
    if (!window.electronAPI) return;

    if (status.running) {
      await window.electronAPI.stopMonitor();
      setMessage('감시를 중지했습니다.');
      return;
    }

    if (window.electronAPI.setNotifyThreshold) {
      await window.electronAPI.setNotifyThreshold(threshold);
    }
    const result = await window.electronAPI.startMonitor();
    if (!result?.ok) {
      setMessage(result?.error || '감시를 시작하지 못했습니다.');
      return;
    }
    setLogs([]);
    setMessage('감시 중 — 오른쪽 OCR 로그를 확인하세요.');
  };

  const detections = Array.isArray(status.detections) ? status.detections : [];
  const buffs = Array.isArray(status.buffs) ? status.buffs : [];
  const renewals = Array.isArray(status.renewals) ? status.renewals : [];
  const iconCount = status.iconCount ?? 0;
  const matchCount = status.matchCount ?? 0;
  const trackedCount = status.trackedCount ?? 0;
  const appVersion = status.appVersion || update.currentVersion || '1.0.0';

  return (
    <div className="control-root">
      <div className="settings-shell">
        <header className="hero">
          <p className="eyebrow">Mabinogi Companion</p>
          <h1>BuffCheck</h1>
          <p className="lede">
            등록 아이콘을 인식하고, 남은 시간이 설정한 임계값 이하인 버프만
            갱신 목록에 표시합니다. · v{appVersion}
          </p>
        </header>

        <div className={`update-bar status-${update.status || 'idle'}`}>
          <span>{updateLabel(update)}</span>
          <div className="update-actions">
            <button
              type="button"
              className="btn ghost tiny"
              onClick={() => void window.electronAPI?.checkForUpdates?.()}
            >
              업데이트 확인
            </button>
            {update.status === 'ready' && (
              <button
                type="button"
                className="btn primary tiny"
                onClick={() => void window.electronAPI?.quitAndInstall?.()}
              >
                지금 재시작
              </button>
            )}
          </div>
        </div>

        <div className="stats-bar">
          <div className="stat">
            <span className="stat-label">등록 버프</span>
            <strong>{iconCount}</strong>
          </div>
          <div className="stat">
            <span className="stat-label">영역 매칭</span>
            <strong>{matchCount}</strong>
          </div>
          <div className="stat">
            <span className="stat-label">추적 중</span>
            <strong>{trackedCount}</strong>
          </div>
          <div className="stat">
            <span className="stat-label">갱신 임박</span>
            <strong>{renewals.length}</strong>
          </div>
        </div>

        <main className="layout">
          <section className="controls">
            <div className="field">
              <label>감시 영역</label>
              <div className="row">
                <span className="mono">{regionLabel}</span>
                <button type="button" className="btn ghost" onClick={() => void pickRegion()}>
                  영역 지정
                </button>
              </div>
              <span className="hint">
                오른쪽 버프 리스트(아이콘+이름+시간) 전체를 드래그 · <kbd>F8</kbd>
              </span>
            </div>

            <div className="field">
              <label>
                갱신 알림 임계 · <span className="mono">{formatThreshold(threshold)}</span>
              </label>
              <div className="threshold-row">
                <span className="hint-inline">1초</span>
                <input
                  type="range"
                  min={1}
                  max={60}
                  step={1}
                  value={threshold}
                  onChange={(e) => void onThresholdChange(e.target.value)}
                />
                <span className="hint-inline">1분</span>
              </div>
              <span className="hint">
                남은 시간이 이 값 이하일 때만 오버레이 갱신 목록에 표시됩니다.
              </span>
            </div>

            <div className="actions">
              <button
                type="button"
                className={`btn primary ${status.running ? 'danger' : ''}`}
                onClick={() => void toggleMonitor()}
              >
                {status.running ? '감시 중지' : '감시 시작'}
              </button>
            </div>

            {status.lastError && <p className="error">오류: {status.lastError}</p>}
            {message && <p className="state on">{message}</p>}
            {!message && (
              <p className={`state ${status.running ? 'on' : region ? 'ready' : ''}`}>
                {status.running
                  ? `감시 중 — 등록 ${iconCount}개 중 ${matchCount}개 매칭 · 추적 ${trackedCount} · 임박 ${renewals.length}`
                  : region
                    ? `영역 준비됨 — 등록 버프 ${iconCount}개`
                    : '대기 중'}
              </p>
            )}

            {status.running && (
              <div className="field live">
                <label>실시간 인식</label>
                {detections.length === 0 && buffs.length === 0 ? (
                  <p className="hint">아직 등록 아이콘이 영역에 안 보입니다.</p>
                ) : (
                  <ul className="live-list">
                    {(detections.length ? detections : buffs).map((b) => (
                      <li key={b.name}>
                        <div className="live-main">
                          <strong>{b.name}</strong>
                          <span>
                            {typeof b.remaining === 'number'
                              ? `${Math.max(0, Math.round(b.remaining))}초`
                              : b.cropMode === 'local'
                                ? '임박 대기'
                                : '시간 미잠금'}
                          </span>
                        </div>
                        <div className="live-meta">
                          {b.ocrRaw ? `raw: ${b.ocrRaw}` : ''}
                          {b.ocrError ? ` · ${b.ocrError}` : ''}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>

          <aside className="log-panel">
            <div className="log-header">
              <div className="tab-row">
                <button
                  type="button"
                  className={`tab ${rightTab === 'logs' ? 'active' : ''}`}
                  onClick={() => setRightTab('logs')}
                >
                  OCR 로그
                </button>
                <button
                  type="button"
                  className={`tab ${rightTab === 'notes' ? 'active' : ''}`}
                  onClick={() => setRightTab('notes')}
                >
                  패치노트
                </button>
              </div>
              {rightTab === 'logs' ? (
                <button
                  type="button"
                  className="btn ghost tiny"
                  onClick={() => setLogs([])}
                  disabled={logs.length === 0}
                >
                  지우기
                </button>
              ) : null}
            </div>
            {rightTab === 'logs' ? (
              <pre className="log-box">
                {logs.length === 0
                  ? '감시 시작 후 OCR 검증 결과가 여기에 쌓입니다.'
                  : logs.join('\n')}
              </pre>
            ) : (
              <pre className="log-box notes-box">
                {patchNotes || '패치노트를 불러오는 중…'}
              </pre>
            )}
          </aside>
        </main>
      </div>
    </div>
  );
}
