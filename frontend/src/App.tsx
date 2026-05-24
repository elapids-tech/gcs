import React, { useEffect, useState, useRef } from 'react';
import * as THREE from 'three';
import { Canvas, useThree } from '@react-three/fiber';
import { Grid, Line, OrbitControls, Environment, Sphere } from '@react-three/drei';
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
  hasOdometry?: boolean;
};

type WebSocketMessage =
  | { key: 'setLandmarks'; value: Landmarks[] }
  | { key: 'dronePoseUpdate'; value: DronePose };

const isNearlyEqual = (a: number, b: number, eps = 1e-6) => Math.abs(a - b) <= eps;

const isFallbackPoseWithoutOdometry = (pose: DronePose) => {
  const [px, py, pz] = pose.position;
  const [qx, qy, qz, qw] = pose.quaternion;

  const isZeroPosition = isNearlyEqual(px, 0) && isNearlyEqual(py, 0) && isNearlyEqual(pz, 0);
  const isIdentityQuat = isNearlyEqual(qx, 0) && isNearlyEqual(qy, 0) && isNearlyEqual(qz, 0) && isNearlyEqual(qw, 1);
  const isConvertedDefaultQuat = isNearlyEqual(qx, 1) && isNearlyEqual(qy, 0) && isNearlyEqual(qz, 0) && isNearlyEqual(qw, 0);

  return isZeroPosition && (isIdentityQuat || isConvertedDefaultQuat);
};

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

const disposeLoadedObject = (object: THREE.Object3D | null) => {
  if (!object) return;

  object.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh) return;

    mesh.geometry?.dispose();

    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((material) => {
      if (!material) return;
      material.dispose();
    });
  });
};

const ViewerEnvironment: React.FC<{ environmentMap: THREE.Texture }> = ({ environmentMap }) => {
  const { scene } = useThree();

  useEffect(() => {
    scene.environment = environmentMap;
    return () => {
      if (scene.environment === environmentMap) {
        scene.environment = null;
      }
    };
  }, [scene, environmentMap]);

  return null;
};


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


type Viewer3dProps = {
  landmarks: Landmarks[];
  dronePose: DronePose | null;
  importedObject: THREE.Group | null;
  environmentMap: THREE.Texture | null;
  showGrid: boolean;
  showOriginAxes: boolean;
  hasReceivedDronePose: boolean;
};

const Viewer3d: React.FC<Viewer3dProps> = ({
  landmarks,
  dronePose,
  importedObject,
  environmentMap,
  showGrid,
  showOriginAxes,
  hasReceivedDronePose,
}) => {
  const gridConfig = {
    cellSize: 1,
    cellThickness: 0.5,
    sectionSize: 5,
    sectionThickness: 1.5,
    followCamera: true,
    infiniteGrid: true,
  };

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
      onCreated={({ gl }) => {
        gl.outputColorSpace = THREE.SRGBColorSpace;
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.8;
      }}
    >
      <color attach="background" args={['#a9a9a9']} />
      <group position={[0, 0, 0]}>
        {/* グリッド（Z-up のため X 軸回りに 90 度回転） */}
        {showGrid && <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]} args={[10, 10]} {...gridConfig} />}

        {/* 世界座標中心軸 */}
        {showOriginAxes && centerAxis.map((line, i) => (
          <Line key={`center-axis-${i}`} points={line.points} color={line.color} lineWidth={2} />
        ))}

        {/* ランドマーク */}
        {landmarks.map((lm) => (
          <Sphere key={lm.id} args={[0.06, 32, 32]} position={[lm.x, lm.y, lm.z]}>
            <meshStandardMaterial color={getColorForId(lm.id)} />
          </Sphere>
        ))}

        {/* インポートモデル */}
        {importedObject && <primitive object={importedObject} />}

        {/* ドローン姿勢のxyz軸 */}
        {hasReceivedDronePose && dronePose &&
          getDroneAxes(dronePose.position, dronePose.quaternion).map((axis, i) => (
            <Line key={`drone-axis-${i}`} points={axis.points} color={axis.color} lineWidth={2} />
          ))}
      </group>

      {/* 環境 */}
      <ambientLight intensity={1.1} />
      <hemisphereLight args={['#ffffff', '#b7c9e8', 0.55]} />
      <directionalLight position={[5, 5, 5]} intensity={1.35} />

      {/* カメラ操作 */}
      <OrbitControls makeDefault enableDamping={false} />
      {environmentMap ? <ViewerEnvironment environmentMap={environmentMap} /> : <Environment preset="city" />}
    </Canvas>
  );
};


type DroneControlPanelProps = {
  dronePose: DronePose | null;
};

export const DroneControlPanel: React.FC<DroneControlPanelProps> = ({ dronePose }) => {
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
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
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

  const formatFixedWidth = (
    value: number | null | undefined,
    decimals: number,
    integerWidth: number
  ) => {
    if (typeof value !== 'number' || Number.isNaN(value)) return '--';
    const fixed = value.toFixed(decimals);
    const totalWidth = integerWidth + (decimals > 0 ? 1 + decimals : 0) + 1;
    return fixed.padStart(totalWidth, ' ');
  };

  const formatPosition = (value: number | null | undefined) =>
    formatFixedWidth(value, 3, 3);

  const formatAttitude = (value: number | null | undefined) =>
    formatFixedWidth(value, 3, 3);

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

  const handleClickSetHome = () => sendCommand("set_home");
  const handleClickTakeoff = () => sendCommand("takeoff");
  const handleClickLanding = () => sendCommand("landing");
  const handleClickEmergencyStop = () => sendCommand("emergency_stop");

  return (
    <div style={panelStyle}>
      <div style={panelInnerStyle}>
        <div style={buttonsColumnStyle}>
          <h2>Drone Control</h2>
          <button onClick={handleClickSetHome}>SET HOME</button>
          <button onClick={handleClickTakeoff}>TAKEOFF</button>
          <button onClick={handleClickLanding}>LANDING</button>
          <button style={emergencyButtonStyle} onClick={handleClickEmergencyStop}>EMERGENCY STOP</button>
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


function MainLayout() {
  const [activeTab, setActiveTab] = useState<'preview' | 'config' | 'flight'>('preview');
  const previewContainerRef = useRef<HTMLDivElement | null>(null);
  const initialRightWidth = 320;
  const [leftWidth, setLeftWidth] = useState<number>(900);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSplitterHovered, setIsSplitterHovered] = useState<boolean>(false);
  const [landmarks, setLandmarks] = useState<Landmarks[]>([]);
  const [dronePose, setDronePose] = useState<DronePose | null>(null);
  const [importedObject, setImportedObject] = useState<THREE.Group | null>(null);
  const [environmentMap, setEnvironmentMap] = useState<THREE.Texture | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showOriginAxes, setShowOriginAxes] = useState(true);
  const [hasReceivedDronePose, setHasReceivedDronePose] = useState(false);

  const minLeft = 480;
  const minRight = 280;
  const splitterWidth = 4;
  const splitterGap = 5;

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
          {
            const hasOdometry = typeof data.value.hasOdometry === 'boolean'
              ? data.value.hasOdometry
              : !isFallbackPoseWithoutOdometry(data.value);

            setHasReceivedDronePose(hasOdometry);
            setDronePose(hasOdometry ? data.value : null);
          }
          break;
        default:
          console.warn(`Unknown key: ${(data as any).key}`);
      }
    };
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => {
      setHasReceivedDronePose(false);
      setDronePose(null);
      console.log('WebSocket connection closed');
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    return () => {
      disposeLoadedObject(importedObject);
      environmentMap?.dispose();
    };
  }, [importedObject, environmentMap]);

  const handleModelImported = (nextObject: THREE.Group, nextEnvironmentMap: THREE.Texture | null) => {
    setImportedObject((prev) => {
      disposeLoadedObject(prev);
      return nextObject;
    });

    setEnvironmentMap((prev) => {
      prev?.dispose();
      return nextEnvironmentMap;
    });
  };

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
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <div
                  style={{
                    position: 'absolute',
                    top: 10,
                    left: 10,
                    zIndex: 10,
                    display: 'flex',
                    gap: 12,
                    alignItems: 'center',
                    padding: '6px 10px',
                    background: 'rgba(255, 255, 255, 0.9)',
                    border: '1px solid #d1d5db',
                    borderRadius: 6,
                    fontSize: 13,
                  }}
                >
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={showGrid}
                      onChange={(event) => setShowGrid(event.target.checked)}
                    />
                    Grid
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={showOriginAxes}
                      onChange={(event) => setShowOriginAxes(event.target.checked)}
                    />
                    Origin
                  </label>
                </div>

                <Viewer3d
                  landmarks={landmarks}
                  dronePose={dronePose}
                  importedObject={importedObject}
                  environmentMap={environmentMap}
                  showGrid={showGrid}
                  showOriginAxes={showOriginAxes}
                  hasReceivedDronePose={hasReceivedDronePose}
                />
              </div>
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
              <DroneControlPanel dronePose={dronePose} />
            </div>
          </div>
        ) : activeTab === 'config' ? (
          <div className="config-panel">
            <CameraSettingsPage />
          </div>
        ) : (
          <FlightAreaPage onModelImported={handleModelImported} />
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
