import React, { useEffect, useState, useCallback, memo } from 'react';
import { Canvas } from '@react-three/fiber'
import { Grid, Center, GizmoHelper, GizmoViewport, AccumulativeShadows, RandomizedLight, OrbitControls, Environment, useGLTF } from '@react-three/drei'
import { useControls } from 'leva'
import Split from "react-split";
import './styles.css';

const R1Left = () => {
  // const gridSize = [10, 10];
  const gridConfig = { cellSize: 1, cellThickness: 0.5, sectionSize: 3, sectionThickness: 1.5, followCamera: true, infiniteGrid: true }; // Example grid config

  return (
    <Canvas className='left' camera={{ position: [10, 12, 12], fov: 25 }}>
      <group position={[0, -0.5, 0]}>
        <Grid position={[0, -0.01, 0]} args={[10, 10]} {...gridConfig} />
      </group>
      <OrbitControls makeDefault enableDamping={false} />
      <Environment preset="city" />
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewport axisColors={['#9d4b4b', '#2f7f4f', '#3b5b9d']} labelColor="white" />
      </GizmoHelper>
    </Canvas>
  );
};

const R1Right = () => {
  const [item, setItem] = useState(null);
  
  const readProject = () => {
    fetch('http://localhost:8000/items/1')
      .then(response => response.json())
      .then(data => setItem(data))
      .catch(error => console.error('Error fetching data:', error));
  };

  const readCamPos = () => {
    fetch('http://localhost:8000/items/1')
    .then(response => response.json())
    .then(data => setItem(data))
    .catch(error => console.error('Error fetching data:', error));
  };

  const handleClickStart = () => {};
  const handleClickStop = () => {};
  return (
    <div className='right' style={{ border: "1px solid red" }}>
      <h1>Component B</h1>
      <div className='bottons-column'>
        <button onClick={readProject}>Read Project</button>
        <button onClick={readCamPos}> Read Camera Position</button>
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