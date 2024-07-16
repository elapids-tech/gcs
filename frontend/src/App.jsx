import React, { memo, useEffect, useState } from 'react';
import Split from 'react-split';
import './App.css';

function ControlPanel() {

}


function PlotViewerPanel() {

}
// https://github.com/nathancahill/split/tree/master/packages/splitjs#sizes
const App = () => {
  return (
    <div className="App">
      <Split
        sizes={[50, 50]}
        minSize={100}
        expandToMin={false}
        gutterSize={10}
        gutterAlign="center"
        snapOffset={30}
        dragInterval={1}
        direction="horizontal"
        cursor="col-resize"
        className="split"
      >
        <div className="panel">左側のパネル</div>
        <div className="panel">右側のパネル</div>
      </Split>
    </div>
  );
}

export default App;

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
