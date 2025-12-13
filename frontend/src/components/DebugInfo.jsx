import React from 'react';

export default function DebugInfo() {
  return (
    <div style={{
      position: 'fixed',
      bottom: 10,
      right: 10,
      background: 'rgba(0,0,0,0.8)',
      color: '#0f0',
      padding: '10px',
      fontFamily: 'monospace',
      fontSize: '11px',
      zIndex: 9999,
      maxWidth: '400px',
      borderRadius: '4px'
    }}>
      <div style={{fontWeight: 'bold', marginBottom: '5px'}}>🔍 DEBUG INFO:</div>
      <div>REACT_APP_BACKEND_URL:</div>
      <div style={{color: '#ff0', wordBreak: 'break-all'}}>
        {process.env.REACT_APP_BACKEND_URL || 'NOT SET'}
      </div>
      <div style={{marginTop: '5px'}}>Build Time:</div>
      <div style={{color: '#0ff'}}>{new Date().toISOString()}</div>
      <div style={{marginTop: '5px', fontSize: '9px', color: '#888'}}>
        Close DevTools to see API baseURL in console
      </div>
    </div>
  );
}
