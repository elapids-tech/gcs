import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import DroneControlPanel from '../components/DroneControlPanel';
import Viewer3dScene from '../components/Viewer3dScene';
import { DronePose, Landmarks, WebSocketMessage } from '../types';
import { isFallbackPoseWithoutOdometry } from '../utils/viewer3dUtils';

type Viewer3dPageProps = {
  importedObject: THREE.Group | null;
  environmentMap: THREE.Texture | null;
};

const Viewer3dPage: React.FC<Viewer3dPageProps> = ({ importedObject, environmentMap }) => {
  const previewContainerRef = useRef<HTMLDivElement | null>(null);
  const initialRightWidth = 320;
  const [leftWidth, setLeftWidth] = useState<number>(900);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isSplitterHovered, setIsSplitterHovered] = useState<boolean>(false);
  const [landmarks, setLandmarks] = useState<Landmarks[]>([]);
  const [dronePose, setDronePose] = useState<DronePose | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showOriginAxes, setShowOriginAxes] = useState(true);
  const [hasReceivedDronePose, setHasReceivedDronePose] = useState(false);

  const minLeft = 480;
  const minRight = 280;
  const splitterWidth = 4;
  const splitterGap = 5;

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8003/ws');

    ws.onopen = () => console.log('WebSocket connection established');
    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      switch (data.key) {
        case 'setLandmarks':
          setLandmarks(data.value);
          break;
        case 'dronePoseUpdate': {
          const hasOdometry =
            typeof data.value.hasOdometry === 'boolean'
              ? data.value.hasOdometry
              : !isFallbackPoseWithoutOdometry(data.value);

          setHasReceivedDronePose(hasOdometry);
          setDronePose(hasOdometry ? data.value : null);
          break;
        }
        default:
          console.warn(`Unknown key: ${(data as { key?: string }).key}`);
      }
    };

    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => {
      setHasReceivedDronePose(false);
      setDronePose(null);
      console.log('WebSocket connection closed');
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    if (!previewContainerRef.current) return;

    const rect = previewContainerRef.current.getBoundingClientRect();
    const maxLeft = Math.max(minLeft, rect.width - minRight - splitterWidth - splitterGap * 2);
    const desiredLeft = rect.width - initialRightWidth - splitterWidth - splitterGap * 2;
    const nextLeft = Math.min(Math.max(desiredLeft, minLeft), maxLeft);
    setLeftWidth(nextLeft);
  }, [initialRightWidth, minLeft, minRight]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!isDragging || !previewContainerRef.current) return;

      const rect = previewContainerRef.current.getBoundingClientRect();
      const maxLeft = Math.max(minLeft, rect.width - minRight - splitterWidth - splitterGap * 2);
      const nextLeft = Math.min(Math.max(event.clientX - rect.left, minLeft), maxLeft);
      setLeftWidth(nextLeft);
    };

    const handlePointerUp = () => {
      if (isDragging) setIsDragging(false);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, minLeft, minRight]);

  return (
    <div
      ref={previewContainerRef}
      className="split"
      style={{ display: 'flex', gap: 0, height: '100%' }}
    >
      <div
        className="pane pane-left"
        style={{
          width: leftWidth,
          minWidth: minLeft,
          marginRight: splitterGap,
          overflow: 'hidden',
        }}
      >
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 10,
              zIndex: 10,
              display: 'flex',
              gap: 12,
              alignItems: 'center',
              padding: '6px 10px',
              background: 'rgba(255, 255, 255, 0.9)',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 13,
            }}
          >
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="checkbox"
                checked={showGrid}
                onChange={(event) => setShowGrid(event.target.checked)}
              />
              Grid
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="checkbox"
                checked={showOriginAxes}
                onChange={(event) => setShowOriginAxes(event.target.checked)}
              />
              Origin
            </label>
          </div>

          <Viewer3dScene
            landmarks={landmarks}
            dronePose={dronePose}
            importedObject={importedObject}
            environmentMap={environmentMap}
            showGrid={showGrid}
            showOriginAxes={showOriginAxes}
            hasReceivedDronePose={hasReceivedDronePose}
          />
        </div>
      </div>

      <div
        role="separator"
        aria-orientation="vertical"
        onPointerEnter={() => setIsSplitterHovered(true)}
        onPointerLeave={() => setIsSplitterHovered(false)}
        onPointerDown={(event) => {
          event.preventDefault();
          setIsDragging(true);
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        style={{
          width: splitterWidth,
          cursor: 'col-resize',
          background: isSplitterHovered
            ? '#e5e7eb'
            : 'linear-gradient(90deg, transparent 0, transparent 1px, #d1d5db 1px, #d1d5db 2px, transparent 2px)',
        }}
      />

      <div
        className="pane pane-right"
        style={{
          flex: 1,
          minWidth: minRight,
          marginLeft: splitterGap,
          overflow: 'hidden',
        }}
      >
        <DroneControlPanel dronePose={dronePose} />
      </div>
    </div>
  );
};

export default Viewer3dPage;
