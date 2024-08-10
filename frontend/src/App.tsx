import React, { useEffect, useState, useMemo, useCallback, useRef, memo } from 'react';
import * as THREE from "three";
import { Canvas } from '@react-three/fiber'
import { Grid, Line, GizmoHelper, GizmoViewport, OrbitControls, Environment, Sphere, Box } from '@react-three/drei'
import Split from "react-split";
import './styles.css';
import ApexCharts from 'react-apexcharts';

type LandmarksCorners = {
  id:string;
  x: number;
  y: number;
  z: number;
};

type LineData = {
  points: [number, number, number][];
  color: string;
};

type WebSocketMessage = 
  | { key: "setLandmarks"; value: LandmarksCorners[] }
  | { key: "dronePosUpdate"; value: any };

const R1Left = () => {
  const [landmarksCorners, setLandmarksCorners] = useState<LandmarksCorners[]>([]);
  const centerAxis = [
    {
      points: [0, 0, 0, 1, 0, 0], // [x1, y1, z1, x2, y2, z2] の形式
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
  const [dronePos, setDronePos] = useState<LineData[]>([]);
  
  const gridConfig = { cellSize: 1, cellThickness: 0.5, sectionSize: 3, sectionThickness: 1.5, followCamera: true, infiniteGrid: true }; // Example grid config

  useEffect(() => {
    // create websocket
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log("WebSocket connection established");
    };
  
    // received message
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.key) {
        case "setLandmarks":
          setLandmarksCorners(data.value);
          break;
        case "dronePosUpdate":
          // setDronePos([]); 
          setDronePos(data.value);
          break;
        default:
          console.warn(`Unknown key: ${data.key}`);
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
  return (
    <Canvas className='left' camera={{ position: [10, 12, 12], fov: 25 }} style={{ border: "1px solid red" }}>
      <group position={[0, 0, 0]}>
        <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]} args={[10, 10]} {...gridConfig} />  
        {/* 原点軸 */}
        {/* <Line points={[[0, 0, 0], [1, 0, 0]]} color="red" lineWidth={3} segments/>
        <Line points={[[0, 0, 0], [0, 1, 0]]} color="green" lineWidth={3} segments/>
        <Line points={[[0, 0, 0], [0, 0, 1]]} color="blue" lineWidth={3} segments/> */}

        {/* <Sphere args={[0.1, 32, 32]} position={[0, 0, 0]}>
          <meshStandardMaterial attach="material" color="blue" />
        </Sphere> */}

        {landmarksCorners.map((corner) => (
        <Sphere args={[0.03, 32, 32]} position={[corner.x, corner.y, corner.z]}>
          <meshStandardMaterial attach="material" color="orange" />
        </Sphere>
        ))}

        {centerAxis.map((line, index) => (
          <Line
            key={index}
            points={line.points}
            color={line.color}
            lineWidth={2}
          />
        ))}

        {dronePos?.map((line, index) => (
          <Line
            key={index}
            points={line.points}
            color={line.color}
            lineWidth={2}
          />
        ))}

      </group>
      <OrbitControls makeDefault enableDamping={false} />
      <Environment preset="city" />
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewport axisColors={['#9d4b4b', '#2f7f4f', '#3b5b9d']} labelColor="white" />
      </GizmoHelper>
    </Canvas>
  );
};

const R1Right: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [filePath, setFilePath] = useState('');
  const [fileContent, setFileContent] = useState('');
  const containerRef = useRef(null);
  const [containerHeight, setContainerHeight] = useState(0);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
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

  const LoadProject = () => {
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
        <h1>Component B</h1>
        <div className='bottons-column'>
          <button onClick={LoadProject}>Load Project</button>
          <input 
            type="file" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileChange} 
            accept=".json"
          />
          <p>選択されたファイルのパス:</p>
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
        cursor="col-resize"
      >
        <R1Left />
        <R1Right />
      </Split>
    </div>
  );
}

const R2: React.FC = () => {
  const [series, setSeries] = useState([{ data: [] as number[] }]);
  const [time, setTime] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTime((prevTime) => prevTime + 0.1);
      setSeries((prevSeries) => {
        const newData = [...prevSeries[0].data, Math.sin(time / 10)];
        if (newData.length > 30) newData.shift(); // 30ポイント以上のデータがある場合、古いデータを削除
        return [{ data: newData }];
      });
    }, 1000); // 1秒ごとにデータを更新

    return () => clearInterval(interval);
  }, [time]);

  const options: ApexCharts.ApexOptions = {
    chart: {
      id: 'realtime',
      animations: {
        enabled: true,
        easing: 'linear', // 'linear'はApexChartsが受け入れる型の一つです
        dynamicAnimation: {
          speed: 1000,
        },
      },
      toolbar: {
        show: false,
      },
      zoom: {
        enabled: false,
      },
    },
    xaxis: {
      type: 'numeric',
      range: 30,
    },
    yaxis: {
      max: 1,
      min: -1,
    },
  };

  return (
    <div className='chart' style={{ border: "1px solid red", height: '100%', overflowY: 'auto' }}>
      <ApexCharts
        options={options}
        series={series}
        type="line"
        width="100%"
        height="400"
      />
    </div>
  );
};

const App = () => {
  return(
    <div className="app">
      <Split
        direction="vertical"
        sizes={[70, 30]}
        minSize={100}
        gutterSize={10}
        gutterAlign="center"
        style={{ height: '100vh' }}
      >
        <R1/>
        <R2/>
      </Split>
    </div>
  );
}

export default App;