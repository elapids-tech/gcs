// ドローンの姿勢・座標データ型
export type DronePose = {
  position: [number, number, number];
  quaternion: [number, number, number, number];
};