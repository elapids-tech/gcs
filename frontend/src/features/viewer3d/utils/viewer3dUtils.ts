import * as THREE from 'three';
import { DronePose } from '../types';

export const isNearlyEqual = (a: number, b: number, eps = 1e-6) => Math.abs(a - b) <= eps;

export const isFallbackPoseWithoutOdometry = (pose: DronePose) => {
  const [px, py, pz] = pose.position;
  const [qx, qy, qz, qw] = pose.quaternion;

  const isZeroPosition = isNearlyEqual(px, 0) && isNearlyEqual(py, 0) && isNearlyEqual(pz, 0);
  const isIdentityQuat =
    isNearlyEqual(qx, 0) && isNearlyEqual(qy, 0) && isNearlyEqual(qz, 0) && isNearlyEqual(qw, 1);
  const isConvertedDefaultQuat =
    isNearlyEqual(qx, 1) && isNearlyEqual(qy, 0) && isNearlyEqual(qz, 0) && isNearlyEqual(qw, 0);

  return isZeroPosition && (isIdentityQuat || isConvertedDefaultQuat);
};

const colorMap: Record<string, string> = {
  '1': 'red',
  '2': 'blue',
  '3': 'green',
  '4': 'orange',
  '5': 'purple',
  '6': 'yellow',
};

export const getColorForId = (id: number | string): string => colorMap[id.toString()] || 'gray';

export const disposeLoadedObject = (object: THREE.Object3D | null) => {
  if (!object) return;

  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;

    child.geometry?.dispose();

    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => {
      material?.dispose();
    });
  });
};
