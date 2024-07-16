import React, { useEffect, useState, useCallback } from 'react';
import './App.css'; // 上記のCSSをインポート

const App = () => {
  return(
    <div className="filled-area"></div>
  );
};
//   const [clientWidth, setClientWidth] = useState(document.documentElement.clientWidth);
//   const [clientHeight, setClientHeight] = useState(document.documentElement.clientHeight);
//   const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

//   const handleMouseMove = useCallback((event) => {
//     setMousePosition({
//       x: event.clientX,
//       y: event.clientY,
//     });
//   }, []);

//   const handleResize = useCallback(() => {
//     setClientWidth(document.documentElement.clientWidth);
//     setClientHeight(document.documentElement.clientHeight);
//   }, []);

//   useEffect(() => {
//     window.addEventListener('resize', handleResize);

//     // クリーンアップ関数
//     return () => {
//       window.removeEventListener('resize', handleResize);
//     };
//   }, [handleResize]);

//   useEffect(() => {
//     console.log('ウィンドウサイズが変更されました:', clientWidth, clientHeight);
//     // ここにサイズ変更時に実行するロジックを記述
//   }, [clientWidth, clientHeight]);

//   const containerStyle = {
//     width: `${clientWidth}px`,
//     height: `${clientHeight}px`,
//     backgroundColor: 'lightblue'
//   };

//   return (
//     <div style={containerStyle} onMouseMove={handleMouseMove}>
//       <p>描画可能範囲の幅: {clientWidth}px</p>
//       <p>描画可能範囲の高さ: {clientHeight}px</p>
//       <p>Mouse Position: ({mousePosition.x}, {mousePosition.y})</p>
//     </div>
//   );
// };

export default App;

// export default App;

// import React, { memo, useEffect, useState } from 'react';
// import { Canvas } from '@react-three/fiber';
// import { Grid, Center, GizmoHelper, GizmoViewport, AccumulativeShadows, RandomizedLight, OrbitControls, Environment, useGLTF } from '@react-three/drei';
// import { useControls } from 'leva';
// import Split from 'react-split';
// import './App.css';

// const Model = () => {
//   const { scene } = useGLTF('/path/to/your/model.glb');
//   return <primitive object={scene} />;
// };

// const App = () => {
//   const [sizes, setSizes] = useState([75, 25]); // デフォルトのサイズを設定

//   useEffect(() => {
//     // サイズの変動を防ぐための設定
//     const handleResize = () => {
//       setSizes([sizes[0], 25]);
//     };

//     window.addEventListener('resize', handleResize);
//     return () => window.removeEventListener('resize', handleResize);
//   }, [sizes]);

//   const controls = useControls({
//     position: { value: [0, 0, 0], step: 0.1 },
//     rotation: { value: [0, 0, 0], step: 0.1 },
//     scale: { value: [1, 1, 1], step: 0.1 }
//   });

//   return (
//     <Split
//       sizes={sizes}
//       minSize={100}
//       expandToMin={false}
//       direction="horizontal"
//       gutterSize={10}
//       cursor="col-resize"
//       onDragEnd={(newSizes) => setSizes([newSizes[0], 25])} // 右側のサイズを固定
//     >
//       <div className="left-pane">
//         <Canvas>
//           <ambientLight />
//           <pointLight position={[10, 10, 10]} />
//           <OrbitControls />
//           <Environment preset="sunset" background />
//           <Center>
//             <Model />
//           </Center>
//           <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
//             <GizmoViewport axisColors={['red', 'green', 'blue']} labelColor="black" />
//           </GizmoHelper>
//           <AccumulativeShadows temporal frames={100} alphaTest={0.9} scale={10}>
//             <RandomizedLight amount={8} radius={4} ambient={0.5} position={[5, 5, -10]} />
//           </AccumulativeShadows>
//         </Canvas>
//       </div>
//       <div className="right-pane">
//         <h2>Controls</h2>
//         <p>Use the Leva controls to adjust the model properties:</p>
//         {/* Leva controls will appear here */}
//       </div>
//     </Split>
//   );
// };

// export default App;
