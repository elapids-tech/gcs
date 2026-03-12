import React, { useState } from 'react';

const FlightAreaPage: React.FC = () => {
  const [sfmIp, setSfmIp] = useState('');
  const [sfmPort, setSfmPort] = useState('');

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
        </div>
      </div>
    </div>
  );
};

export default FlightAreaPage;
