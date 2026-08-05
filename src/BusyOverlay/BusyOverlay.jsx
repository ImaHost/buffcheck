import { useEffect, useState } from 'react';
import './BusyOverlay.css';

export default function BusyOverlay() {
  const [message, setMessage] = useState('자동등록중...');

  useEffect(() => {
    document.documentElement.classList.add('overlay-page');
    return () => document.documentElement.classList.remove('overlay-page');
  }, []);

  useEffect(() => {
    if (!window.electronAPI?.onBusyMessage) return undefined;
    return window.electronAPI.onBusyMessage((data) => {
      if (data?.message) setMessage(String(data.message));
    });
  }, []);

  return (
    <div className="busy-root">
      <div className="busy-card">
        <div className="busy-spinner" aria-hidden />
        <p className="busy-text">{message}</p>
        <p className="busy-sub">아이콘을 추출·등록하는 중입니다</p>
      </div>
    </div>
  );
}
