import React, { useEffect, useState, useCallback, useRef, memo } from 'react';
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


const R1Left = () => {
  const [landmarksCorners, setLandmarksCorners] = useState<LandmarksCorners[]>([]);
  const gridConfig = { cellSize: 1, cellThickness: 0.5, sectionSize: 3, sectionThickness: 1.5, followCamera: true, infiniteGrid: true }; // Example grid config

  let cam_pos: number[] = [0.8837511461111193, 1.273606628730099, -0.04604716620709769];
  let cam_axis_x: number[] = [0.009925571161736535,-0.02566810726314839,-0.9996212439252385];
  let cam_axis_y: number[] = [0.9220628954311656,-0.3865694042852517,0.01908173314038775];
  let cam_axis_z: number[] = [-0.3869127807480762, -0.9219030556083829, 0.01983068717211323];
  let axis_color: string[] = ["red", "green", "blue"]

  useEffect(() => {
    // create websocket
    const ws = new WebSocket('ws://localhost:8000/ws');
  
    // received message
    ws.onmessage = (event) => {
      const data: LandmarksCorners[] = JSON.parse(event.data);
      setLandmarksCorners(data);
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
        <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} args={[10, 10]} {...gridConfig} />  
        {/* 原点軸 */}
        {/* <Line points={[[0, 0, 0], [1, 0, 0]]} color="red" lineWidth={3} segments/>
        <Line points={[[0, 0, 0], [0, 1, 0]]} color="green" lineWidth={3} segments/>
        <Line points={[[0, 0, 0], [0, 0, 1]]} color="blue" lineWidth={3} segments/> */}

        <Sphere args={[0.1, 32, 32]} position={[0, 0, 0]}>
          <meshStandardMaterial attach="material" color="blue" />
        </Sphere>

        {landmarksCorners.map((corner) => (
        <Sphere args={[0.03, 32, 32]} position={[corner.x, corner.y, corner.z]}>
          <meshStandardMaterial attach="material" color="orange" />
        </Sphere>
        ))}

        {/* カメラ位置 */}
        <Line
          points={[[0.8718785913511636, 0.02561684830236978, 1.259717682823211], 
                  [0.8818871746908766, 1.025524706031532,1.250546842566777]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.8718785913511636, 0.02561684830236978, 1.259717682823211], 
                  [1.797489764997355,0.0128826421824138,0.8814561394225951]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.8718785913511636, 0.02561684830236978, 1.259717682823211], 
                  [0.4935351184580095, 0.0209140782706234, 0.3340643457292556]]}
          color="blue" 
          lineWidth={2}  
          segments
        />

        {/* 回転行列 変換前*/}
        {/* <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.01000858333971266, 0.9999078577291625, -0.009170840256436968]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.9256111736461912, -0.0127342061199569, -0.3782615434006145]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.3783434728931537, -0.00470277003174896, -0.9256533370939555]]}
          color="blue" 
          lineWidth={2}  
          segments
        /> */}

        {/* 回転行列 変換後*/}
        {/* <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.3783434728931537, -0.00470277003174896, -0.9256533370939555]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.01000858333971266, -0.9999078577291625, 0.009170840256436968]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.9256111736461912, 0.0127342061199569, 0.3782615434006145]]}
          color="blue" 
          lineWidth={2}  
          segments
        /> */}


        <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.7071067811865476, 0, -0.7071067811865475]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [0, 1, 0]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.7071067811865475, 0, 0.7071067811865476]]}
          color="blue" 
          lineWidth={2}  
          segments
        />

        {/* <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.4586583741122357, 0.003559066956693537, 0.8886055530431476]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.01000858333971266, -0.9999078577291625,  0.009170840256436968]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [0.8885563145441331, -0.01309996541502443, -0.4585804910698587]]}
          color="blue" 
          lineWidth={2}  
          segments
        /> */}

        {/* flu_cam_mat */}
        {/* <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.37834346, -0.010008584, 0.9256112]]}
          color="red" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.0047027702, -0.99990785, -0.012734206]]}
          color="green" 
          lineWidth={2}  
          segments
        />
        <Line
          points={[[0.0, 0.0, 0.0], 
                  [-0.92565334, 0.0091708405, -0.37826154]]}
          color="blue" 
          lineWidth={2}  
          segments
        /> */}


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