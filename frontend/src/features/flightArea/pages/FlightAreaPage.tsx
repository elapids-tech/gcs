import React, { useEffect, useState } from 'react';

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

  const controlStyle: React.CSSProperties = {
    height: 24,
    padding: '0 8px',
    fontSize: 12,
    lineHeight: '24px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxSizing: 'border-box',
  };

  const projectLabelWidth = 120;
  const projectControlWidth = 220;

  const labelTextStyle: React.CSSProperties = {
    width: projectLabelWidth,
    whiteSpace: 'nowrap',
  };

  const projectRowStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `${projectLabelWidth}px ${projectControlWidth}px auto`,
    columnGap: 12,
    alignItems: 'center',
    marginTop: 8,
  };

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/app-setting/network/flight-area-build-server`);
        const data = await res.json().catch(() => null);
        if (res.ok && data?.status === 'ok') {
          setSfmIp(String(data?.ip ?? ''));
          setSfmPort(String(data?.port ?? ''));
        }
      } catch {
        // Ignore load errors.
      }
    };
    loadSettings();
  }, []);

  return (
    <div className="config-panel" style={pageStyle}>
      <h2>Flight Area</h2>
      <div style={{ maxWidth: 480 }}>
        <h3>Server Setting</h3>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'flex-start', alignItems: 'center' }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span>IP</span>
            <input
              type="text"
              placeholder="127.0.0.1"
              value={sfmIp}
              onChange={(e) => setSfmIp(e.target.value)}
              style={controlStyle}
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
                style={controlStyle}
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
              style={controlStyle}
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
            <button
              type="button"
              onClick={async () => {
                const ip = sfmIp.trim();
                const port = sfmPort.trim();
                if (!ip || !port) {
                  return;
                }

                const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
                await fetch(`${API_BASE_URL}/app-setting/network/flight-area-build-server?${query}`, {
                  method: 'POST',
                });
              }}
              style={controlStyle}
            >
              Save
            </button>
          </div>
        </div>
        <h3>Project</h3>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Create Project</span>
          <input
            type="text"
            placeholder="Enter the project name."
            style={{ ...controlStyle, width: projectControlWidth }}
          />
          <button type="button" style={controlStyle}>
            Create
          </button>
        </div>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Select Project</span>
          <select defaultValue="" style={{ ...controlStyle, width: projectControlWidth }}>
            <option value="" disabled>
              -- Select a Project --
            </option>
          </select>
          <span />
        </div>
        <div style={{ borderTop: '1px solid #ddd', margin: '8px 0' }} />
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Build</span>
          <span />
          <button type="button" style={controlStyle}>
            Run
          </button>
        </div>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Meshroom Process State</span>
          <span style={{ ...controlStyle, width: projectControlWidth, justifyContent: 'flex-start' }} />
          <span />
        </div>
      </div>
    </div>
  );
};

export default FlightAreaPage;
