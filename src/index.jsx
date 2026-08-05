import React from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Routes, Route } from 'react-router-dom';
import CaptureOverlay from './CaptureOverlay/CaptureOverlay';
import NotifyOverlay from './NotifyOverlay/NotifyOverlay';
import ControlPanel from './ControlPanel/ControlPanel';
import './styles/global.css';

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/control" element={<ControlPanel />} />
        <Route path="/capture-overlay" element={<CaptureOverlay />} />
        <Route path="/notify-overlay" element={<NotifyOverlay />} />
        <Route path="*" element={<ControlPanel />} />
      </Routes>
    </HashRouter>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
