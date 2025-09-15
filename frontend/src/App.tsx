import React, { useEffect, useState, useRef } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { Grid, Line, GizmoHelper, GizmoViewport, OrbitControls, Environment, Sphere } from '@react-three/drei';
import { DroneConfigurationPage } from './features/droneConfiguration';
import Split from 'react-split';
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

const DroneControlPanel: React.FC = () => {
  // Setpoint用 state
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [z, setZ] = useState('');
  const [yaw, setYaw] = useState('');

  const post = (path: string, body?: any) =>
    fetch(`http://localhost:8003/${path}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }).then((r) => r.json());

  const handleClickArm = () => post('arm').then(console.log).catch(console.error);
  const handleClickDisarm = () => post('disarm').then(console.log).catch(console.error);
  const handleClickGuideMode = () => post('guide').then(console.log).catch(console.error);
  const handleClickAutoMode = () => post('auto').then(console.log).catch(console.error);
  const handleClickStart = () => post('start').then(console.log).catch(console.error);
  const handleClickStop = () => post('stop').then(console.log).catch(console.error);

  const handleClickSetpoint = () => {
    const payload = {
      x: parseFloat(x),
      y: parseFloat(y),
      z: parseFloat(z),
      yaw_deg: parseFloat(yaw),
    };
    post('set-setpoint', payload).then(console.log).catch(console.error);
  };

  return (
    <div className="panel">
      <div className="panel-inner">
        <div className="bottons-column">
          <h2>Telemetry</h2>

          <h2>Control</h2>
          <button onClick={handleClickArm}>Arm</button>
          <button onClick={handleClickDisarm}>Disarm</button>
          <button onClick={handleClickGuideMode}>Guide Mode</button>
          <button onClick={handleClickAutoMode}>Auto Mode</button>

          <h2>Setpoint</h2>
          <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '200px' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              X:
              <input type="number" value={x} onChange={(e) => setX(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Y:
              <input type="number" value={y} onChange={(e) => setY(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Z:
              <input type="number" value={z} onChange={(e) => setZ(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Yaw:
              <input type="number" value={yaw} onChange={(e) => setYaw(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <button onClick={handleClickSetpoint} style={{ padding: '4px 8px', margin: '4px 0 0 0' }}>
              Set
            </button>
          </div>

          <h2>No function</h2>
          <button onClick={handleClickStart}>Start</button>
          <button onClick={handleClickStop}>Stop</button>
        </div>
      </div>
    </div>
  );
};

function MainLayout() {
  const [activeTab, setActiveTab] = useState<'preview' | 'config'>('preview');

  return (
    <div className="main-layout">
      {/* 上部の切替ボタン */}
      <div className="top-bar">
        <button
          className={activeTab === 'preview' ? 'active' : ''}
          onClick={() => setActiveTab('preview')}
        >
          プレビュー
        </button>
        <button
          className={activeTab === 'config' ? 'active' : ''}
          onClick={() => setActiveTab('config')}
        >
          コンフィグレーション
        </button>
      </div>

      {/* メイン画面 */}
      <div className="main-content">
        {activeTab === 'preview' ? (
          <Split
            className="split"
            sizes={[70, 30]}
            minSize={300}
            gutterSize={10}
            direction="horizontal"
          >
            <div className="pane pane-left">
              <Viewer3d />
            </div>
            <div className="pane pane-right">
              <DroneControlPanel />
            </div>
          </Split>
        ) : (
          <div className="config-panel">
            <DroneConfigurationPage />
          </div>
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
