import React, { useEffect, useState, useCallback, useRef, memo } from 'react';
import * as THREE from "three";
import { Canvas } from '@react-three/fiber'
import { Grid, Line, Center, GizmoHelper, GizmoViewport, AccumulativeShadows, RandomizedLight, OrbitControls, Environment, useGLTF } from '@react-three/drei'
import { useControls } from 'leva'
import Split from "react-split";
import './styles.css';
import axios from 'axios';

const R1Left = () => {
  // const gridSize = [10, 10];
  const gridConfig = { cellSize: 1, cellThickness: 0.5, sectionSize: 3, sectionThickness: 1.5, followCamera: true, infiniteGrid: true }; // Example grid config
  THREE.Object3D.DEFAULT_UP = new THREE.Vector3(0, 0, 1);

  return (
    <Canvas className='left' camera={{ position: [10, 12, 12], fov: 25 }}>
      <group position={[0, -0.5, 0]}>
        <Grid rotation={[Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} args={[10, 10]} {...gridConfig} />
        <Line
          points={[[0, 0, 0], [10, 10, 10]]}       // Array of points, Array<Vector3 | Vector2 | [number, number, number] | [number, number] | number>
          color="white"                   // Default
          lineWidth={5}                   // In pixels (default)
          segments                        // If true, renders a THREE.LineSegments2. Otherwise, renders a THREE.Line2
          dashed={false}                  // Default
        />
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

  const readCamPos = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleClickStart = () => {};
  const handleClickStop = () => {};

  return (
    <div className='right' style={{ border: "1px solid red" }}>
      <h1>Component B</h1>
      <div className='bottons-column'>
        <button onClick={readCamPos}>Read Camera Position</button>
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileChange} 
          accept=".txt"
        />
        <p>選択されたファイルのパス:</p>
        <p>{filePath}</p>
        <button onClick={handleClickStart}>Start</button>
        <button onClick={handleClickStop}>Stop</button>
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

function R2() {
  return(
    <div className="R2">
      <p>R2</p>
    </div>
  );
}

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