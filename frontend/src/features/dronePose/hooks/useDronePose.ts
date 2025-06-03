import { useState, useEffect } from 'react';
import { DronePose } from '../types';

export function useDronePose() {
  const [dronePose, setDronePose] = useState<DronePose | null>(null);

  useEffect(() => {
    // WebSocketやAPIから取得する処理例
    // setDronePose({ position: [0,0,0], quaternion: [0,0,0,1] });
  }, []);

  return dronePose;
}