import React, { ChangeEvent, useState } from 'react';
import axios from 'axios';
import './App.css';

const App: React.FC = () => {
  const [xValue, setXValue] = useState<string>('');
  const [yValue, setYValue] = useState<string>('');
  const [zValue, setZValue] = useState<string>('');

  const handleXChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    if (/^\d*\.?\d*$/.test(value)) {
      setXValue(value);
    }
  };

  const handleYChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    if (/^\d*\.?\d*$/.test(value)) {
      setYValue(value);
    }
  };

  const handleZChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    if (/^\d*\.?\d*$/.test(value)) {
      setZValue(value);
    }
  };

  const handleSend = async () => {
    console.log(`X: ${xValue}, Y: ${yValue}, Z: ${zValue}`);
    // const pos = [xValue, yValue, zValue]
    const pos = {
      x: xValue,
      y: yValue,
      z: zValue
    };
    
    try {
      const response = await axios.post('http://localhost:8000/pos_send', pos, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      console.log(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const [messages, setMessages] = useState<string[]>([
    'Message 1',
    'Message 2',
    'Message 3',
  ]);

  const addMessage = (message: string) => {
    setMessages([...messages, message]);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      console.log('Selected file:', file);
      addMessage(`Selected file: ${file.name}`);
      // ファイル処理のコードをここに追加
    }
  };

  const handleButtonClick = async (endpoint: string) => {
    try {
      const response = await axios.post(`http://localhost:8000/${endpoint}`);
      console.log(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1 className="title">IDLS Configurator</h1>
        <input
          type="file"
          accept=".json"
          id="fileInput"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button onClick={() => document.getElementById('fileInput')?.click()}>Read Project</button>
        <p className="small-text">Title: none</p>
        <p className="small-text">Path: none</p>
        <hr />
        <p>Controller</p>
        <div className="button-row">
          <button onClick={() => handleButtonClick('start')}>START</button>
          <button onClick={() => handleButtonClick('pause')}>PAUSE</button>
          <button onClick={() => handleButtonClick('exit')}>EXIT</button>
          <button onClick={() => handleButtonClick('disarm')}>DIS ARM</button>
        </div>
          <div className="horizontal-container">
            <div className="container">
              <label className="label">
                X :
              </label>
              <input 
                type="text" 
                value={xValue} 
                onChange={handleXChange} 
                pattern="\d*"
                className="input"
              />
            </div>
            <div className="container">
              <label className="label">
                Y :
              </label>
              <input 
                type="text" 
                value={yValue} 
                onChange={handleYChange} 
                pattern="\d*"
                className="input"
              />
            </div>
            <div className="container">
              <label className="label">
                Z :
              </label>
              <input 
                type="text" 
                value={zValue} 
                onChange={handleZChange} 
                pattern="\d*"
                className="input"
              />
            </div>
            <div className="button-container">
              <button onClick={handleSend} className="button">SEND</button>
            </div>
          </div>
        <hr />
        <p>Settings</p>
      </header>
    </div>
  );
}

export default App;
