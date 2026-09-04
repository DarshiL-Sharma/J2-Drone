import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import DroneModel from './DroneModel';

export default function ExplodedCanvas({ explode, targets, highlighted }) {
  return (
    <Canvas camera={{ position: [2.6, 1.4, 3.4], fov: 38 }} dpr={[1, 1.6]} shadows>
      <color attach="background" args={['#0b0d10']} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[4, 6, 4]} intensity={1.5} castShadow />
      <directionalLight position={[-4, -2, -4]} intensity={0.35} color="#8892a0" />
      <group position={[0, 0.2, 0]} scale={1.4}>
        <DroneModel explode={explode} explodeTargets={targets} highlighted={highlighted} />
      </group>
      <gridHelper args={[8, 16, '#24282D', '#161a1e']} position={[0, -1.15, 0]} />
      <OrbitControls
        enablePan={false}
        minDistance={2.5}
        maxDistance={7}
        maxPolarAngle={Math.PI / 1.9}
      />
    </Canvas>
  );
}
