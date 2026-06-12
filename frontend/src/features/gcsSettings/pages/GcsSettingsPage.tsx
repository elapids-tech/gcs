import React, { useCallback, useEffect, useState } from 'react';

const API_BASE_URL = 'http://localhost:8003';
const CHECK_TIMEOUT_MS = 3000;
const SETTINGS_LOAD_TIMEOUT_MS = 3000;

const GcsSettingsPage: React.FC = () => {
  const [sfmIp, setSfmIp] = useState('');
  const [sfmPort, setSfmPort] = useState('');
  const [isLoadingSettings, setIsLoadingSettings] = useState(false);
  const [checkStatus, setCheckStatus] = useState<'idle' | 'checking' | 'ok' | 'error'>('idle');
  const [checkMessage, setCheckMessage] = useState('');
  const [saveMessage, setSaveMessage] = useState('');

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

  const loadSettings = useCallback(async () => {
    setIsLoadingSettings(true);
    setSaveMessage('Loading saved settings...');

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      controller.abort();
    }, SETTINGS_LOAD_TIMEOUT_MS);

    try {
      const res = await fetch(`${API_BASE_URL}/app-setting/network/sfm-server`, {
        signal: controller.signal,
      });
      const data = await res.json().catch(() => null);

      if (!res.ok || data?.status !== 'ok') {
        setSaveMessage(data?.message || `Failed to load settings (${res.status})`);
        return;
      }

      setSfmIp(String(data?.ip ?? ''));
      setSfmPort(String(data?.port ?? ''));
      setSaveMessage('');
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        setSaveMessage(`Failed to load settings (timeout ${SETTINGS_LOAD_TIMEOUT_MS / 1000}s)`);
      } else {
        setSaveMessage('Failed to load saved settings');
      }
    } finally {
      window.clearTimeout(timeoutId);
      setIsLoadingSettings(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleCheck = async () => {
    const ip = sfmIp.trim();
    const port = sfmPort.trim();
    if (!ip || !port) {
      setCheckStatus('error');
      setCheckMessage('IP and Port required');
      return;
    }

    setCheckStatus('checking');
    setCheckMessage('Checking...');

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      controller.abort();
    }, CHECK_TIMEOUT_MS);

    try {
      const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
      const res = await fetch(`${API_BASE_URL}/app-setting/network/sfm-server/check?${query}`, {
        method: 'POST',
        signal: controller.signal,
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.reachable) {
        setCheckStatus('ok');
        setCheckMessage('OK');
      } else {
        setCheckStatus('error');
        setCheckMessage(data?.message || `Failed (${res.status})`);
      }
    } catch (error) {
      setCheckStatus('error');
      if (error instanceof Error && error.name === 'AbortError') {
        setCheckMessage('Timeout (3s)');
      } else {
        setCheckMessage('Cannot reach backend');
      }
    } finally {
      window.clearTimeout(timeoutId);
    }
  };

  const handleSave = async () => {
    const ip = sfmIp.trim();
    const port = sfmPort.trim();
    if (!ip || !port) {
      setSaveMessage('IP and Port required');
      return;
    }

    setSaveMessage('Saving...');
    try {
      const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
      const res = await fetch(`${API_BASE_URL}/app-setting/network/sfm-server?${query}`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.status === 'ok') {
        setSaveMessage('Saved');
      } else {
        setSaveMessage(data?.message || `Save failed (${res.status})`);
      }
    } catch {
      setSaveMessage('Failed to save settings');
    }
  };

  return (
    <div className="config-panel" style={pageStyle}>
      <div style={{ maxWidth: 480 }}>
        <h3>SfM Server</h3>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'flex-start', alignItems: 'center' }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span>IP</span>
            <input
              type="text"
              placeholder="127.0.0.1"
              value={sfmIp}
              onChange={(event) => setSfmIp(event.target.value)}
              disabled={isLoadingSettings}
              style={{ ...controlStyle, width: 120 }}
            />
          </label>

          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span>Port</span>
              <input
                type="text"
                placeholder="8000"
                value={sfmPort}
                onChange={(event) => setSfmPort(event.target.value)}
                disabled={isLoadingSettings}
                style={{ ...controlStyle, width: 72 }}
              />
            </label>
            <button
              type="button"
              onClick={handleCheck}
              disabled={checkStatus === 'checking' || isLoadingSettings}
              style={controlStyle}
            >
              Check
            </button>
            <span
              aria-live="polite"
              style={{
                minWidth: 120,
                color: checkStatus === 'ok' ? '#1b7f2a' : checkStatus === 'error' ? '#b00020' : '#666',
              }}
            >
              {checkMessage}
            </span>
            <button type="button" onClick={handleSave} disabled={isLoadingSettings} style={controlStyle}>
              Save
            </button>
          </div>
        </div>
        <div aria-live="polite" style={{ marginTop: 8, fontSize: 12, color: '#444' }}>
          {saveMessage}
        </div>
      </div>
    </div>
  );
};

export default GcsSettingsPage;