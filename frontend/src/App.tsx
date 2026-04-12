import React, { useEffect, useState, useRef } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { Grid, Line, GizmoHelper, GizmoViewport, OrbitControls, Environment, Sphere } from '@react-three/drei';
import { CameraSettingsPage } from './features/cameraSettings';
import { FlightAreaPage } from './features/flightArea';
import './styles.css';


// Z-up をグローバルで一度だけ
THREE.Object3D.DEFAULT_UP = new THREE.Vector3(0, 0, 1);

// === 型定義 ===
type Vec3 = [number, number, number];

type Landmarks = {
  id: string;
  x: number;
  y: number;
  z: number;
};

type DronePose = {
  sysid: number;
  position: [number, number, number];
  quaternion: [number, number, number, number];
};

type WebSocketMessage =
  | { key: 'setLandmarks'; value: Landmarks[] }
  | { key: 'dronePoseUpdate'; value: DronePose };

// === 色マップ ===
const colorMap: { [key: string]: string } = {
  '1': 'red',
  '2': 'blue',
  '3': 'green',
  '4': 'orange',
  '5': 'purple',
  '6': 'yellow',
};
const getColorForId = (id: number | string): string => colorMap[id.toString()] || 'gray';


export function useControlSocket() {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8003/ws/drone/control");
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => socket.close();
  }, []);

  // サーバーに操作コマンドを送信する関数
  const sendCommand = (action: string, params?: any) => {
    socketRef.current?.send(JSON.stringify({ action, params }));
  };

  return { sendCommand };
}


const Viewer3d: React.FC = () => {
  const gridConfig = {
    cellSize: 1,
    cellThickness: 0.5,
    sectionSize: 5,
    sectionThickness: 1.5,
    followCamera: true,
    infiniteGrid: true,
  };

  const [landmarks, setLandmarks] = useState<Landmarks[]>([]);
  const [dronePose, setDronePose] = useState<DronePose | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8003/ws');

    ws.onopen = () => console.log('WebSocket connection established');
    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      switch (data.key) {
        case 'setLandmarks':
          setLandmarks(data.value);
          break;
        case 'dronePoseUpdate':
          setDronePose(data.value);
          break;
        default:
          console.warn(`Unknown key: ${(data as any).key}`);
      }
    };
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => console.log('WebSocket connection closed');
    return () => ws.close();
  }, []);

  // ドローン姿勢のxyz軸（points は二次元配列）
  const getDroneAxes = (
    position: [number, number, number],
    quaternion: [number, number, number, number]
  ) => {
    const pos = new THREE.Vector3(...position);
    const quat = new THREE.Quaternion(...quaternion);
    const length = 0.3;

    const axes = [
      { dir: new THREE.Vector3(1, 0, 0), color: 'red' },
      { dir: new THREE.Vector3(0, 1, 0), color: 'green' },
      { dir: new THREE.Vector3(0, 0, 1), color: 'blue' }
    ];

    return axes.map(({ dir, color }) => {
      const to = dir.clone().applyQuaternion(quat).multiplyScalar(length).add(pos);
      const fromArr: Vec3 = [pos.x, pos.y, pos.z];
      const toArr:   Vec3 = [to.x,  to.y,  to.z ];
      return { points: [fromArr, toArr] as [Vec3, Vec3], color };
    });
  };

  const centerAxis: { points: [Vec3, Vec3]; color: string }[] = [
    { points: [[0, 0, 0], [1, 0, 0]], color: 'red' },
    { points: [[0, 0, 0], [0, 1, 0]], color: 'green' },
    { points: [[0, 0, 0], [0, 0, 1]], color: 'blue' }
  ];

  return (
    <Canvas
      className="canvas"
      camera={{ position: [10, 12, 12], fov: 25 }}
    >
      <color attach="background" args={['#a9a9a9']} />
      <group position={[0, 0, 0]}>
        {/* グリッド（Z-up のため X 軸回りに 90 度回転） */}
        <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]} args={[10, 10]} {...gridConfig} />

        {/* 世界座標中心軸 */}
        {centerAxis.map((line, i) => (
          <Line key={`center-axis-${i}`} points={line.points} color={line.color} lineWidth={2} />
        ))}

        {/* ランドマーク */}
        {landmarks.map((lm) => (
          <Sphere key={lm.id} args={[0.06, 32, 32]} position={[lm.x, lm.y, lm.z]}>
            <meshStandardMaterial color={getColorForId(lm.id)} />
          </Sphere>
        ))}

        {/* ドローン姿勢のxyz軸 */}
        {dronePose &&
          getDroneAxes(dronePose.position, dronePose.quaternion).map((axis, i) => (
            <Line key={`drone-axis-${i}`} points={axis.points} color={axis.color} lineWidth={2} />
          ))}
      </group>

      {/* 環境 */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />

      {/* カメラ操作 */}
      <OrbitControls makeDefault enableDamping={false} />
      <Environment preset="city" />
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewport axisColors={['#9d4b4b', '#2f7f4f', '#3b5b9d']} labelColor="white" />
      </GizmoHelper>
    </Canvas>
  );
};


export const DroneControlPanel: React.FC = () => {
  const panelStyle: React.CSSProperties = {
    height: "100%",
    boxSizing: "border-box",
    borderLeft: "1px solid #ddd",
  };

  const panelInnerStyle: React.CSSProperties = {
    padding: 8,
    height: "100%",
    display: "flex",
    flexDirection: "column",
  };

  const buttonsColumnStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  };

  const emergencyButtonStyle: React.CSSProperties = {
    marginTop: 16, 
  };


  const { sendCommand } = useControlSocket();

  const handleClickSetGpsGlobalOrigin = () => sendCommand("set_gps_global_origin");
  const handleClickSetHomePosition = () => sendCommand("set_home_position");
  const handleClickTakeoff = () => sendCommand("takeoff");
  const handleClickLanding = () => sendCommand("landing");
  const handleClickEmergencyStop = () => sendCommand("emergency_stop");

  return (
    <div style={panelStyle}>
      <div style={panelInnerStyle}>
        <div style={buttonsColumnStyle}>
          <h2>Server State</h2>
          <h2>Drone State</h2>
          <button onClick={handleClickSetGpsGlobalOrigin}>SET GPS GLOBAL ORIGIN</button>
          <button onClick={handleClickSetHomePosition}>SET HOME POSITION</button>
          <button onClick={handleClickTakeoff}>TAKEOFF</button>
          <button onClick={handleClickLanding}>LANDING</button>
          <button
            style={emergencyButtonStyle}
            onClick={handleClickEmergencyStop}
          >
            EMERGENCY STOP
          </button>
        </div>
      </div>
    </div>
  );
};


function MainLayout() {
  const [activeTab, setActiveTab] = useState<'preview' | 'config' | 'flight'>('preview');
  const previewContainerRef = useRef<HTMLDivElement | null>(null);
  const initialRightWidth = 320;
  const [leftWidth, setLeftWidth] = useState<number>(900);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSplitterHovered, setIsSplitterHovered] = useState<boolean>(false);

  const minLeft = 480;
  const minRight = 280;
  const splitterWidth = 4;
  const splitterGap = 5;

  useEffect(() => {
    if (activeTab !== 'preview' || !previewContainerRef.current) return;

    const rect = previewContainerRef.current.getBoundingClientRect();
    const maxLeft = Math.max(
      minLeft,
      rect.width - minRight - splitterWidth - splitterGap * 2
    );
    const desiredLeft = rect.width - initialRightWidth - splitterWidth - splitterGap * 2;
    const nextLeft = Math.min(Math.max(desiredLeft, minLeft), maxLeft);
    setLeftWidth(nextLeft);
  }, [activeTab, initialRightWidth, minLeft, minRight]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!isDragging || !previewContainerRef.current) return;

      const rect = previewContainerRef.current.getBoundingClientRect();
      const maxLeft = Math.max(
        minLeft,
        rect.width - minRight - splitterWidth - splitterGap * 2
      );
      const nextLeft = Math.min(Math.max(event.clientX - rect.left, minLeft), maxLeft);
      setLeftWidth(nextLeft);
    };

    const handlePointerUp = () => {
      if (isDragging) setIsDragging(false);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, minLeft, minRight]);

  return (
    <div className="main-layout">
      {/* 上部の切替ボタン */}
      <div className="top-bar">
        <button
          className={activeTab === 'preview' ? 'active' : ''}
          onClick={() => setActiveTab('preview')}
        >
          3D Viewer
        </button>
        <button
          className={activeTab === 'config' ? 'active' : ''}
          onClick={() => setActiveTab('config')}
        >
          Camera Settings
        </button>
        <button
          className={activeTab === 'flight' ? 'active' : ''}
          onClick={() => setActiveTab('flight')}
        >
          Flight Area
        </button>
      </div>

      {/* メイン画面 */}
      <div className="main-content">
        {activeTab === 'preview' ? (
          <div
            ref={previewContainerRef}
            className="split"
            style={{ display: 'flex', gap: 0, height: '100%' }}
          >
            <div
              className="pane pane-left"
              style={{
                width: leftWidth,
                minWidth: minLeft,
                marginRight: splitterGap,
                overflow: 'hidden',
              }}
            >
              <Viewer3d />
            </div>
            <div
              role="separator"
              aria-orientation="vertical"
              onPointerEnter={() => setIsSplitterHovered(true)}
              onPointerLeave={() => setIsSplitterHovered(false)}
              onPointerDown={(event) => {
                event.preventDefault();
                setIsDragging(true);
                event.currentTarget.setPointerCapture(event.pointerId);
              }}
              style={{
                width: splitterWidth,
                cursor: 'col-resize',
                background: isSplitterHovered
                  ? '#e5e7eb'
                  : 'linear-gradient(90deg, transparent 0, transparent 1px, #d1d5db 1px, #d1d5db 2px, transparent 2px)',
              }}
            />
            <div
              className="pane pane-right"
              style={{
                flex: 1,
                minWidth: minRight,
                marginLeft: splitterGap,
                overflow: 'hidden',
              }}
            >
              <DroneControlPanel />
            </div>
          </div>
        ) : activeTab === 'config' ? (
          <div className="config-panel">
            <CameraSettingsPage />
          </div>
        ) : (
          <FlightAreaPage />
        )}
      </div>
    </div>
  );
}


const App = () => {
  return (
    <div className="app">
      <MainLayout />
    </div>
  );
};

export default App;
