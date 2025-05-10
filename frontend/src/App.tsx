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

type LineData = {
  points: [number, number, number][];
  color: string;
};

type DronePose = {
  position: [number, number, number];
  quaternion: [number, number, number, number];
};

type WebSocketMessage =
  | { key: "setLandmarks"; value: Landmarks[] }
  | { key: "dronePosUpdate"; value: LineData[] }
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
  const [dronePos, setDronePos] = useState<LineData[]>([]);
  const [dronePose, setDronePose] = useState<DronePose | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log("WebSocket connection established");
    };

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.key) {
        case "setLandmarks":
          setLandmarks(data.value);
          break;
        case "dronePosUpdate":
          setDronePos(data.value);
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

        {/* ドローンの移動軌跡 */}
        {dronePos.map((line, index) => (
          <Line
            key={`drone-path-${index}`}
            points={line.points.flat()}
            color={line.color}
            lineWidth={2}
          />
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

const ProjectManagementPanel: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [filePath, setFilePath] = useState('');
  const [fileContent, setFileContent] = useState('');
  const containerRef = useRef(null);
  const [containerHeight, setContainerHeight] = useState(0);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    console.log('handleFileChange')
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      const text = await file.text();
      setFilePath(file.name);
      setFileContent(text);

      // ファイル読み込みが完了した後にfetchを呼び出す
      const response = await fetch('http://localhost:8000/upload/', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: text,
      });

      const result = await response.json();
      console.log(result);
    }
  };

  const LoadClusters = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const LoadImage = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleClickStart = () => {
    fetch('http://localhost:8000/start', {
      method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
  };

  const handleClickStop = () => {
    fetch('http://localhost:8000/stop', {
      method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
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
        <h1>Project</h1>
        <div className='bottons-column'>
          <button onClick={LoadClusters}>Load Clusters</button>
          <input 
            type="file" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange} 
            accept=".json"
          />
          <p>選択されたファイルのパス:</p>
          <p>{filePath}</p>

          <button onClick={LoadImage}>Add Image</button>
          <input 
            type="file" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange} 
            accept=".json"
          />
          <p>選択された画像ファイルをリストで表示したい:</p>
          <p>{filePath}</p>

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
        <ProjectManagementPanel />
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