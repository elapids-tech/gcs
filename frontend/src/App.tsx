import React, { useEffect, useState } from 'react';
import * as THREE from 'three';
import { CameraSettingsPage } from './features/cameraSettings';
import { FlightAreaPage } from './features/flightArea';
import { Viewer3dPage, disposeLoadedObject } from './features/viewer3d';
import './styles.css';

function MainLayout() {
  const [activeTab, setActiveTab] = useState<'preview' | 'config' | 'flight'>('preview');
  const [importedObject, setImportedObject] = useState<THREE.Group | null>(null);
  const [environmentMap, setEnvironmentMap] = useState<THREE.Texture | null>(null);

  useEffect(() => {
    return () => {
      disposeLoadedObject(importedObject);
      environmentMap?.dispose();
    };
  }, [importedObject, environmentMap]);

  const handleModelImported = (nextObject: THREE.Group, nextEnvironmentMap: THREE.Texture | null) => {
    setImportedObject((prev) => {
      disposeLoadedObject(prev);
      return nextObject;
    });

    setEnvironmentMap((prev) => {
      prev?.dispose();
      return nextEnvironmentMap;
    });
  };

  return (
    <div className="main-layout">
      <div className="top-bar">
        <button className={activeTab === 'preview' ? 'active' : ''} onClick={() => setActiveTab('preview')}>
          3D Viewer
        </button>
        <button className={activeTab === 'config' ? 'active' : ''} onClick={() => setActiveTab('config')}>
          Camera Settings
        </button>
        <button className={activeTab === 'flight' ? 'active' : ''} onClick={() => setActiveTab('flight')}>
          Flight Area
        </button>
      </div>

      <div className="main-content">
        {activeTab === 'preview' ? (
          <Viewer3dPage importedObject={importedObject} environmentMap={environmentMap} />
        ) : activeTab === 'config' ? (
          <div className="config-panel">
            <CameraSettingsPage />
          </div>
        ) : (
          <FlightAreaPage onModelImported={handleModelImported} />
        )}
      </div>
    </div>
  );
}

const App = () => {
  return (
    <div className="app">
      <MainLayout />
    </div>
  );
};

export default App;
