import React, { useEffect, useState, useMemo, useCallback, useRef, memo } from 'react';
import * as THREE from "three";
import { Canvas } from '@react-three/fiber'
import { Grid, Line, GizmoHelper, GizmoViewport, OrbitControls, Environment, Sphere, Box } from '@react-three/drei'
import Split from "react-split";
import './styles.css';

// === 型定義 ===

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
  | { key: "setLandmarks"; value: Landmarks[] }
  | { key: "dronePoseUpdate"; value: DronePose };

// === 色マップ ===

const colorMap: { [key: string]: string } = {
  "1": "red",
  "2": "blue",
  "3": "green",
  "4": "orange",
  "5": "purple",
  "6": "yellow",
};

const getColorForId = (id: number | string): string => {
  const idStr = id.toString();
  return colorMap[idStr] || "gray";
};

const Viewer3d: React.FC = () => {
  const gridConfig = {
    cellSize: 1,
    cellThickness: 0.5,
    sectionSize: 3,
    sectionThickness: 1.5,
    followCamera: true,
    infiniteGrid: true
  };

  const [landmarks, setLandmarks] = useState<Landmarks[]>([]);
  const [dronePose, setDronePose] = useState<DronePose | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8003/ws');

    ws.onopen = () => {
      console.log("WebSocket connection established");
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.key) {
        case "setLandmarks":
          setLandmarks(data.value);
          break;
        case "dronePoseUpdate":
          setDronePose(data.value);
          break;
        default:
          console.warn(`Unknown key: ${(data as any).key}`);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };

    return () => {
      ws.close();
    };
  }, []);

  THREE.Object3D.DEFAULT_UP = new THREE.Vector3(0, 0, 1);

  // === ドローンの姿勢軸を生成 ===
  const getDroneAxes = (position: [number, number, number], quaternion: [number, number, number, number]) => {
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
      return {
        points: [pos.toArray(), to.toArray()].flat(), // [x1, y1, z1, x2, y2, z2]
        color
      };
    });
  };

  const centerAxis = [
    {
      points: [0, 0, 0, 1, 0, 0],
      color: 'red'
    },
    {
      points: [0, 0, 0, 0, 1, 0],
      color: 'green'
    },
    {
      points: [0, 0, 0, 0, 0, 1],
      color: 'blue'
    }
  ];

  return (
    <Canvas className='left' camera={{ position: [10, 12, 12], fov: 25 }} style={{ border: "1px solid red" }}>
      <group position={[0, 0, 0]}>
        {/* グリッド */}
        <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]} args={[10, 10]} {...gridConfig} />

        {/* 世界座標中心軸 */}
        {centerAxis.map((line, index) => (
          <Line key={`center-axis-${index}`} points={line.points} color={line.color} lineWidth={2} />
        ))}

        {/* ランドマーク */}
        {landmarks.map((center) => (
          <Sphere
            key={center.id}
            args={[0.03, 32, 32]}
            position={[center.x, center.y, center.z]}
          >
            <meshStandardMaterial attach="material" color={getColorForId(center.id)} />
          </Sphere>
        ))}

        {/* ドローン姿勢のxyz軸 */}
        {dronePose &&
          getDroneAxes(dronePose.position, dronePose.quaternion).map((axis, index) => (
            <Line
              key={`drone-axis-${index}`}
              points={axis.points}
              color={axis.color}
              lineWidth={2}
            />
          ))
        }
      </group>

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
  const containerRef = useRef(null);
  const [containerHeight, setContainerHeight] = useState(0);

  // Setpoint用 state
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [z, setZ] = useState('');
  const [yaw, setYaw] = useState('');

  const handleClickArm = () => {
    fetch('http://localhost:8003/arm', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickDisarm = () => {
    fetch('http://localhost:8003/disarm', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickGuideMode = () => {
    fetch('http://localhost:8003/guide', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickAutoMode = () => {
    fetch('http://localhost:8003/auto', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickStart = () => {
    fetch('http://localhost:8003/start', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickStop = () => {
    fetch('http://localhost:8003/stop', {
      method: 'POST',
    })
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error('Error:', error));
  };

  const handleClickSetpoint = () => {
    const payload = {
      x: parseFloat(x),
      y: parseFloat(y),
      z: parseFloat(z),
      yaw_deg: parseFloat(yaw), // FastAPI側に合わせて yaw_deg に変更
    };

    fetch('http://localhost:8003/set-setpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(res => res.json())
      .then(data => console.log(data))
      .catch(err => console.error('Error:', err));
  };

  useEffect(() => {
    const resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        if (entry.target === containerRef.current) {
          setContainerHeight(entry.contentRect.height);
        }
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        resizeObserver.unobserve(containerRef.current);
      }
    };
  }, []);

  return (
    <div className='right' style={{ border: "1px solid red", height: '100%', overflowY: 'auto'}}>
      <div style={{ minHeight: containerHeight + 100 }}>
        <div className='bottons-column'>

          <h2>Control</h2>
          <button onClick={handleClickArm}>Arm</button>
          <button onClick={handleClickDisarm}>Disarm</button>
          <button onClick={handleClickGuideMode}>Guide Mode</button>
          <button onClick={handleClickAutoMode}>Auto Mode</button>

          <h2>Setpoint</h2>
          <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '200px' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              X:<input type="number" value={x} onChange={(e) => setX(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Y:<input type="number" value={y} onChange={(e) => setY(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Z:<input type="number" value={z} onChange={(e) => setZ(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <label style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
              Yaw:<input type="number" value={yaw} onChange={(e) => setYaw(e.target.value)} style={{ width: '100px', margin: 0 }} />
            </label>
            <button onClick={handleClickSetpoint} style={{ padding: '4px 8px', margin: '4px 0 0 0' }}>Set</button>
          </div>

          <h2>No function</h2>
          <button onClick={handleClickStart}>Start</button>
          <button onClick={handleClickStop}>Stop</button>
        </div>
      </div>
    </div>
  );
};

function R1() {
  return (
    <div className="R1">
      <Split
        className="top"
        sizes={[70, 30]}
        minSize={300}
        expandToMin={false}
        gutterSize={10}
        gutterAlign="center"
        snapOffset={30}
        dragInterval={1}
        direction="horizontal"
        cursor="col-resize">
        <Viewer3d />
        <DroneControlPanel />
      </Split>
    </div>
  );
}

const App = () => {
  return (
    <div className="app">
      <R1/>
    </div>
  );
};

export default App;