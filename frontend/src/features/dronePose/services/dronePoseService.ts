import { DronePose } from '../types';

export async function fetchDronePose(): Promise<DronePose> {
  // APIから取得する例
  // return fetch('/api/drone-pose').then(res => res.json());
  return { position: [0, 0, 0], quaternion: [0, 0, 0, 1] }; // ダミー
}