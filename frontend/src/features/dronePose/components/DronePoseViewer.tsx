import React from 'react';
import { DronePose } from '../types';

type Props = {
  dronePose: DronePose | null;
};

export const DronePoseViewer: React.FC<Props> = ({ dronePose }) => {
  if (!dronePose) return <div>ドローン情報なし</div>;
  return (
    <div>
      <div>位置: {dronePose.position.join(', ')}</div>
      <div>クォータニオン: {dronePose.quaternion.join(', ')}</div>
    </div>
  );
};