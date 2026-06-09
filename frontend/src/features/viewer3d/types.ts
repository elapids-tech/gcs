import * as THREE from 'three';

export type Vec3 = [number, number, number];

export type Landmarks = {
  id: string;
  x: number;
  y: number;
  z: number;
};

export type DronePose = {
  sysid: number;
  position: [number, number, number];
  quaternion: [number, number, number, number];
  hasOdometry?: boolean;
};

export type WebSocketMessage =
  | { key: 'setLandmarks'; value: Landmarks[] }
  | { key: 'dronePoseUpdate'; value: DronePose };

export type Viewer3dSceneProps = {
  landmarks: Landmarks[];
  dronePose: DronePose | null;
  importedObject: THREE.Group | null;
  environmentMap: THREE.Texture | null;
  showGrid: boolean;
  showOriginAxes: boolean;
  hasReceivedDronePose: boolean;
};
