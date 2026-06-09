import React from 'react';
import * as THREE from 'three';
import { DronePose } from '../types';
import { useControlSocket } from '../hooks/useControlSocket';

type DroneControlPanelProps = {
  dronePose: DronePose | null;
};

const DroneControlPanel: React.FC<DroneControlPanelProps> = ({ dronePose }) => {
  const panelStyle: React.CSSProperties = {
    height: '100%',
    boxSizing: 'border-box',
    borderLeft: '1px solid #ddd',
  };

  const panelInnerStyle: React.CSSProperties = {
    padding: 8,
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  };

  const buttonsColumnStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  };

  const emergencyButtonStyle: React.CSSProperties = {
    marginTop: 16,
  };

  const separatorStyle: React.CSSProperties = {
    border: 0,
    borderTop: '1px solid #ddd',
    margin: '12px 0',
  };

  const poseListStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'max-content max-content 1fr',
    columnGap: 8,
    rowGap: 4,
    fontSize: 14,
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontVariantNumeric: 'tabular-nums',
  };

  const poseSectionStyle: React.CSSProperties = {
    gridColumn: '1 / -1',
    fontWeight: 600,
    marginTop: 6,
  };

  const poseValueStyle: React.CSSProperties = {
    whiteSpace: 'pre',
    textAlign: 'right',
  };

  const formatFixedWidth = (value: number | null | undefined, decimals: number, integerWidth: number) => {
    if (typeof value !== 'number' || Number.isNaN(value)) return '--';
    const fixed = value.toFixed(decimals);
    const totalWidth = integerWidth + (decimals > 0 ? 1 + decimals : 0) + 1;
    return fixed.padStart(totalWidth, ' ');
  };

  const formatPosition = (value: number | null | undefined) => formatFixedWidth(value, 3, 3);
  const formatAttitude = (value: number | null | undefined) => formatFixedWidth(value, 3, 3);

  const toEulerDegrees = (quaternion: [number, number, number, number] | null) => {
    if (!quaternion) return null;
    const quat = new THREE.Quaternion(...quaternion);
    const euler = new THREE.Euler().setFromQuaternion(quat, 'XYZ');
    return {
      roll: THREE.MathUtils.radToDeg(euler.x),
      pitch: THREE.MathUtils.radToDeg(euler.y),
      yaw: THREE.MathUtils.radToDeg(euler.z),
    };
  };

  const euler = toEulerDegrees(dronePose?.quaternion ?? null);

  const { sendCommand } = useControlSocket();

  const handleClickSetHome = () => sendCommand('set_home');
  const handleClickTakeoff = () => sendCommand('takeoff');
  const handleClickLanding = () => sendCommand('landing');
  const handleClickEmergencyStop = () => sendCommand('emergency_stop');

  return (
    <div style={panelStyle}>
      <div style={panelInnerStyle}>
        <div style={buttonsColumnStyle}>
          <h2>Drone Control</h2>
          <button onClick={handleClickSetHome}>SET HOME</button>
          <button onClick={handleClickTakeoff}>TAKEOFF</button>
          <button onClick={handleClickLanding}>LANDING</button>
          <button style={emergencyButtonStyle} onClick={handleClickEmergencyStop}>
            EMERGENCY STOP
          </button>
          <hr style={separatorStyle} />
          <div style={poseListStyle}>
            <div style={poseSectionStyle}>Position</div>
            <div>x</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatPosition(dronePose?.position[0])}</div>
            <div>y</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatPosition(dronePose?.position[1])}</div>
            <div>z</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatPosition(dronePose?.position[2])}</div>

            <div style={poseSectionStyle}>Attitude</div>
            <div>roll</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatAttitude(euler?.roll)} deg</div>
            <div>pitch</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatAttitude(euler?.pitch)} deg</div>
            <div>yaw</div>
            <div>:</div>
            <div style={poseValueStyle}>{formatAttitude(euler?.yaw)} deg</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DroneControlPanel;
