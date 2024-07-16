import React, { useEffect, useState, useCallback } from 'react';
import Split from "react-split";
import './styles.css';

function ControlPanel() {
  return (
    <div>
      read プロジェクトファイル
      スタートボタン
      ストップボタン
    </div>
  );
};

const R1Left = () => {
  return (
    <div class='left' style={{ border: "1px solid red" }}>
      <h1>Component A</h1>
    </div>
  );
};

const R1Right = () => {
  return (
    <div class='right' style={{ border: "1px solid red" }}>
      <h1>Component B</h1>
    </div>
  );
};

function R1() {
  return (
    <div className="R1">
      <Split
        className="top"
        sizes={[60, 40]}
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


// const App = () => {
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

// export default App;