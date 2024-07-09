import React, { ChangeEvent, useState } from 'react';
import './App.css'; // CSSファイルをインポート

const App = () => {
    return (
        <div className="App">
            <header className="App-header">
                <h1>Welcome to My Website</h1>
            </header>
            <main className="App-main">
                <p>This is a paragraph in the main content area.</p>
                {/* メインコンテンツが増えるとスクロールバーが表示されます */}
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</p>
                
            </main>
            <footer className="App-footer">
                <p>&copy; 2024 My Website</p>
            </footer>
        </div>
    );
}

export default App;
