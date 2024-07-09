import React, { ChangeEvent, useState } from 'react';
import Splitter, { SplitDirection } from '@devbookhq/splitter'
import './App.css';

const App: React.FC = () => {
  const [messages, setMessages] = useState<string[]>([
    'Message 1',
    'Message 2',
    'Message 3',
  ]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      console.log('Selected file:', file);
      addMessage(`Selected file: ${file.name}`);
      // ファイル処理のコードをここに追加
    }
  };

  const addMessage = (message: string) => {
    setMessages([...messages, message]);
  };

  return (
    <div className="App">
      <div style={{ overflow: 'hidden' }}>
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
        </header>
      </div>

      <main>
        <hr />
        <p>Controller</p>
        <div className="button-row">
          <button>START</button>
          <button>PAUSE</button>
          <button>EXIT</button>
          <button>DIS ARM</button>
        </div>

        <hr />
        <p>Settings</p>

      </main>

      <footer>


      </footer>
    </div>
  );
}

export default App;
