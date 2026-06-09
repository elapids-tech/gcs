import React, { useEffect } from 'react';
import * as THREE from 'three';
import { Canvas, useThree } from '@react-three/fiber';
import { Grid, Line, OrbitControls, Environment, Sphere } from '@react-three/drei';
import { Vec3, Viewer3dSceneProps } from '../types';
import { getColorForId } from '../utils/viewer3dUtils';

THREE.Object3D.DEFAULT_UP = new THREE.Vector3(0, 0, 1);

const ViewerEnvironment: React.FC<{ environmentMap: THREE.Texture }> = ({ environmentMap }) => {
  const { scene } = useThree();

  useEffect(() => {
    scene.environment = environmentMap;
    return () => {
      if (scene.environment === environmentMap) {
        scene.environment = null;
      }
    };
  }, [scene, environmentMap]);

  return null;
};

const Viewer3dScene: React.FC<Viewer3dSceneProps> = ({
  landmarks,
  dronePose,
  importedObject,
  environmentMap,
  showGrid,
  showOriginAxes,
  hasReceivedDronePose,
}) => {
  const gridConfig = {
    cellSize: 1,
    cellThickness: 0.5,
    sectionSize: 5,
    sectionThickness: 1.5,
    followCamera: true,
    infiniteGrid: true,
  };

  const getDroneAxes = (
    position: [number, number, number],
    quaternion: [number, number, number, number],
  ) => {
    const pos = new THREE.Vector3(...position);
    const quat = new THREE.Quaternion(...quaternion);
    const length = 0.3;

    const axes = [
      { dir: new THREE.Vector3(1, 0, 0), color: 'red' },
      { dir: new THREE.Vector3(0, 1, 0), color: 'green' },
      { dir: new THREE.Vector3(0, 0, 1), color: 'blue' },
    ];

    return axes.map(({ dir, color }) => {
      const to = dir.clone().applyQuaternion(quat).multiplyScalar(length).add(pos);
      const fromArr: Vec3 = [pos.x, pos.y, pos.z];
      const toArr: Vec3 = [to.x, to.y, to.z];
      return { points: [fromArr, toArr] as [Vec3, Vec3], color };
    });
  };

  const centerAxis: { color: string; position: Vec3; rotation: Vec3 }[] = [
    { color: 'red', position: [0.5, 0, 0], rotation: [0, 0, Math.PI / 2] },
    { color: 'green', position: [0, 0.5, 0], rotation: [0, 0, 0] },
    { color: 'blue', position: [0, 0, 0.5], rotation: [Math.PI / 2, 0, 0] },
  ];

  return (
    <Canvas
      className="canvas"
      camera={{ position: [10, 12, 12], fov: 25 }}
      onCreated={({ gl }) => {
        gl.outputColorSpace = THREE.SRGBColorSpace;
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.8;
      }}
    >
      <color attach="background" args={['#a9a9a9']} />
      <group position={[0, 0, 0]}>
        {showGrid && (
          <Grid
            rotation={[Math.PI / 2, 0, 0]}
            position={[0, 0, 0]}
            args={[10, 10]}
            renderOrder={-10}
            {...gridConfig}
          />
        )}

        {showOriginAxes &&
          centerAxis.map((axis, i) => (
            <mesh
              key={`center-axis-${i}`}
              position={axis.position}
              rotation={axis.rotation}
              renderOrder={1000}
            >
              <cylinderGeometry args={[0.01, 0.01, 1, 16]} />
              <meshBasicMaterial
                color={axis.color}
                depthTest={false}
                depthWrite={false}
                toneMapped={false}
                transparent={true}
                opacity={1}
              />
            </mesh>
          ))}

        {landmarks.map((lm) => (
          <Sphere key={lm.id} args={[0.06, 32, 32]} position={[lm.x, lm.y, lm.z]}>
            <meshStandardMaterial color={getColorForId(lm.id)} />
          </Sphere>
        ))}

        {importedObject && <primitive object={importedObject} />}

        {hasReceivedDronePose &&
          dronePose &&
          getDroneAxes(dronePose.position, dronePose.quaternion).map((axis, i) => (
            <Line key={`drone-axis-${i}`} points={axis.points} color={axis.color} lineWidth={2} />
          ))}
      </group>

      <ambientLight intensity={1.1} />
      <hemisphereLight args={['#ffffff', '#b7c9e8', 0.55]} />
      <directionalLight position={[5, 5, 5]} intensity={1.35} />

      <OrbitControls makeDefault enableDamping={false} />
      {environmentMap ? (
        <ViewerEnvironment environmentMap={environmentMap} />
      ) : (
        <Environment preset="city" />
      )}
    </Canvas>
  );
};

export default Viewer3dScene;
