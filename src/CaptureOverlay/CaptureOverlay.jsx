import { useCallback, useEffect, useState } from 'react';
import './CaptureOverlay.css';

export default function CaptureOverlay() {
  const [start, setStart] = useState(null);
  const [rect, setRect] = useState(null);

  useEffect(() => {
    document.documentElement.classList.add('overlay-page');
    return () => document.documentElement.classList.remove('overlay-page');
  }, []);

  const onKey = useCallback((e) => {
    if (e.key === 'Escape') {
      window.electronAPI?.cancelRegionPicker?.();
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onKey]);

  const handlePointerDown = (e) => {
    const x = e.clientX;
    const y = e.clientY;
    setStart({ x, y });
    setRect({ x, y, width: 0, height: 0 });
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!start) return;
    setRect({
      x: Math.min(start.x, e.clientX),
      y: Math.min(start.y, e.clientY),
      width: Math.abs(e.clientX - start.x),
      height: Math.abs(e.clientY - start.y),
    });
  };

  const handlePointerUp = () => {
    if (rect && rect.width > 5 && rect.height > 5) {
      window.electronAPI?.confirmRegion({
        x: Math.round(window.screenX + rect.x),
        y: Math.round(window.screenY + rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    }
    setStart(null);
    setRect(null);
  };

  return (
    <div
      className="overlay-root"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <div className="hint-bar">
        드래그로 버프창 영역을 선택하세요 · 선택 후 아이콘 자동등록 · Esc 취소
      </div>
      {rect && (
        <div
          className="selection"
          style={{
            left: rect.x,
            top: rect.y,
            width: rect.width,
            height: rect.height,
          }}
        />
      )}
    </div>
  );
}
