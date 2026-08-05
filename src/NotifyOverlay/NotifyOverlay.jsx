import { useEffect, useRef, useState } from 'react';
import './NotifyOverlay.css';

export default function NotifyOverlay() {
  const [running, setRunning] = useState(false);
  const [buffs, setBuffs] = useState([]);
  const [trackedCount, setTrackedCount] = useState(0);
  const [matchCount, setMatchCount] = useState(0);
  const [iconCount, setIconCount] = useState(0);
  const [threshold, setThreshold] = useState(30);
  const [pulse, setPulse] = useState(false);
  const prevCount = useRef(0);
  const thresholdRef = useRef(30);

  useEffect(() => {
    document.documentElement.classList.add('overlay-page');
    return () => document.documentElement.classList.remove('overlay-page');
  }, []);

  useEffect(() => {
    const offs = [];

    const applyThreshold = (value) => {
      if (typeof value !== 'number') return;
      thresholdRef.current = value;
      setThreshold(value);
    };

    const applyStatus = (s) => {
      if (!s) return;
      if (typeof s.running === 'boolean') setRunning(s.running);
      if (Array.isArray(s.renewals)) setBuffs(s.renewals);
      if (typeof s.matchCount === 'number') setMatchCount(s.matchCount);
      if (typeof s.trackedCount === 'number') setTrackedCount(s.trackedCount);
      else if (Array.isArray(s.buffs)) setTrackedCount(s.buffs.length);
      if (typeof s.iconCount === 'number') setIconCount(s.iconCount);
      applyThreshold(s.notifyThreshold);
    };

    if (window.electronAPI?.getStatus) {
      void window.electronAPI.getStatus().then(applyStatus);
    }

    if (window.electronAPI?.onStatusUpdated) {
      offs.push(window.electronAPI.onStatusUpdated(applyStatus));
    }

    if (window.electronAPI?.onBuffUpdate) {
      offs.push(
        window.electronAPI.onBuffUpdate((data) => {
          if (typeof data?.running === 'boolean') setRunning(data.running);
          if (typeof data?.matchCount === 'number') setMatchCount(data.matchCount);
          if (typeof data?.trackedCount === 'number') setTrackedCount(data.trackedCount);
          if (typeof data?.iconCount === 'number') setIconCount(data.iconCount);
          applyThreshold(data?.notifyThreshold);

          const limit = thresholdRef.current;
          const list = Array.isArray(data?.renewals)
            ? data.renewals
            : (Array.isArray(data?.buffs) ? data.buffs : [])
                .filter(
                  (b) =>
                    typeof b.remaining === 'number' &&
                    b.remaining > 0 &&
                    b.remaining <= limit,
                )
                .sort((a, b) => a.remaining - b.remaining);

          if (list.length > prevCount.current) {
            setPulse(true);
            window.setTimeout(() => setPulse(false), 600);
          }
          prevCount.current = list.length;
          setBuffs(list);
        }),
      );
    }

    return () => offs.forEach((off) => typeof off === 'function' && off());
  }, []);

  if (!running) {
    return null;
  }

  const criticalSec = Math.min(10, Math.max(1, Math.ceil(threshold / 3)));

  return (
    <div className={`panel-shell ${pulse ? 'pulse' : ''}`}>
      <header className="panel-header panel-drag">
        <div>
          <p className="brand">BuffCheck</p>
          <h1>갱신 필요</h1>
          <p className="panel-sub">
            등록 {iconCount} · 매칭 {matchCount} · 추적 {trackedCount} · ≤{threshold}초
          </p>
        </div>
        <span className="drag-hint" title="드래그해서 이동">⠿</span>
      </header>

      {buffs.length === 0 ? (
        <>
          <p className="ok">여유 — {threshold}초 이하 버프 없음</p>
          {matchCount === 0 && (
            <p className="idle-hint">등록 아이콘이 영역에서 안 보입니다</p>
          )}
          {matchCount > 0 && trackedCount === 0 && (
            <p className="idle-hint">아이콘 감지 — 임박 시간 대기 중</p>
          )}
          {trackedCount > 0 && (
            <p className="idle-hint">추적 {trackedCount}개 · 아직 임계 초과</p>
          )}
        </>
      ) : (
        <ul className="buff-list">
          {buffs.map((b) => (
            <li key={b.name} className={b.remaining <= criticalSec ? 'critical' : ''}>
              <span className="name">{b.name}</span>
              <span className="time">{Math.max(0, Math.round(b.remaining))}초</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
