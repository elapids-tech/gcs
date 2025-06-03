import React from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

type Props = {
  position: [number, number, number];
  quaternion: [number, number, number, number];
};

export const DronePoseAxes: React.FC<Props> = ({ position, quaternion }) => {
  const pos = new THREE.Vector3(...position);
  const quat = new THREE.Quaternion(...quaternion);
  const length = 0.3;

  const axes = [
    { dir: new THREE.Vector3(1, 0, 0), color: 'red' },
    { dir: new THREE.Vector3(0, 1, 0), color: 'green' },
    { dir: new THREE.Vector3(0, 0, 1), color: 'blue' }
  ];

  return (
    <>
      {axes.map(({ dir, color }, idx) => {
        const to = dir.clone().applyQuaternion(quat).multiplyScalar(length).add(pos);
        return (
          <Line
            key={color}
            points={[pos.toArray(), to.toArray()]}
            color={color}
            lineWidth={2}
          />
        );
      })}
    </>
  );
};