import React, { useState } from 'react';

const API_BASE_URL = 'http://localhost:8003';

const FlightAreaPage: React.FC = () => {
  const [sfmIp, setSfmIp] = useState('');
  const [sfmPort, setSfmPort] = useState('');
  const [checkStatus, setCheckStatus] = useState<'idle' | 'checking' | 'ok' | 'error'>('idle');
  const [checkMessage, setCheckMessage] = useState('');

  const pageStyle: React.CSSProperties = {
    padding: '0px 10px',
    boxSizing: 'border-box',
  };

  return (
    <div className="config-panel" style={pageStyle}>
      <h2>Flight Area</h2>
      <div style={{ maxWidth: 480 }}>
        <h3>sfm server</h3>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'flex-start', alignItems: 'center' }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span>IP</span>
            <input
              type="text"
              placeholder="127.0.0.1"
              value={sfmIp}
              onChange={(e) => setSfmIp(e.target.value)}
            />
          </label>

          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span>Port</span>
              <input
                type="number"
                placeholder="8000"
                value={sfmPort}
                onChange={(e) => setSfmPort(e.target.value)}
                min={1}
                max={65535}
              />
            </label>
            <button
              type="button"
              onClick={async () => {
                const ip = sfmIp.trim();
                const port = sfmPort.trim();
                if (!ip || !port) {
                  setCheckStatus('error');
                  setCheckMessage('IP and Port required');
                  return;
                }

                setCheckStatus('checking');
                setCheckMessage('Checking...');
                try {
                  const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
                  const res = await fetch(`${API_BASE_URL}/flight-area/check-connection?${query}`, {
                    method: 'POST',
                  });
                  const data = await res.json().catch(() => null);
                  if (res.ok && data?.reachable) {
                    setCheckStatus('ok');
                    setCheckMessage('OK');
                  } else {
                    setCheckStatus('error');
                    setCheckMessage(data?.message || `Failed (${res.status})`);
                  }
                } catch (err) {
                  setCheckStatus('error');
                  setCheckMessage('Cannot reach backend');
                }
              }}
              disabled={checkStatus === 'checking'}
              style={{ padding: '4px 8px', fontSize: 12 }}
            >
              Check
            </button>
            <span
              aria-live="polite"
              style={{
                minWidth: 100,
                color: checkStatus === 'ok' ? '#1b7f2a' : checkStatus === 'error' ? '#b00020' : '#666',
              }}
            >
              {checkMessage}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlightAreaPage;
