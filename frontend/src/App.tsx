import React, { useEffect, useState } from 'react';
import * as THREE from 'three';
import { CameraSettingsPage } from './features/cameraSettings';
import { ProjectPage } from './features/project';
import GcsSettingsPage from './features/gcsSettings/pages/GcsSettingsPage';
import { Viewer3dPage, disposeLoadedObject } from './features/viewer3d';
import './styles.css';

function MainLayout() {
  const [activeTab, setActiveTab] = useState<'preview' | 'config' | 'flight' | 'gsc'>('preview');
  const [importedObject, setImportedObject] = useState<THREE.Group | null>(null);
  const [environmentMap, setEnvironmentMap] = useState<THREE.Texture | null>(null);

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLSpanElement>, tab: 'preview' | 'config' | 'flight' | 'gsc') => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setActiveTab(tab);
    }
  };

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
        <span
          role="button"
          tabIndex={0}
          className={`top-tab ${activeTab === 'flight' ? 'active' : ''}`}
          onClick={() => setActiveTab('flight')}
          onKeyDown={(event) => handleTabKeyDown(event, 'flight')}
        >
          Projects
        </span>
        <span
          role="button"
          tabIndex={0}
          className={`top-tab ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
          onKeyDown={(event) => handleTabKeyDown(event, 'preview')}
        >
          3D Viewer
        </span>
        <span
          role="button"
          tabIndex={0}
          className={`top-tab ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
          onKeyDown={(event) => handleTabKeyDown(event, 'config')}
        >
          Camera Settings
        </span>
        <span
          role="button"
          tabIndex={0}
          className={`top-tab ${activeTab === 'gsc' ? 'active' : ''}`}
          onClick={() => setActiveTab('gsc')}
          onKeyDown={(event) => handleTabKeyDown(event, 'gsc')}
        >
          GSC Settings
        </span>
      </div>

      <div className="main-content">
        {activeTab === 'preview' ? (
          <Viewer3dPage importedObject={importedObject} environmentMap={environmentMap} />
        ) : activeTab === 'config' ? (
          <div className="config-panel">
            <CameraSettingsPage />
          </div>
        ) : activeTab === 'gsc' ? (
          <GcsSettingsPage />
        ) : (
          <ProjectPage onModelImported={handleModelImported} />
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
