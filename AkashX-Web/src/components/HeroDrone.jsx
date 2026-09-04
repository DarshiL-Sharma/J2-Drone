import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import DroneModel from './DroneModel';

function RotatingRig() {
  const group = useRef();
  useFrame((state) => {
    if (!group.current) return;
    const t = state.clock.getElapsedTime();
    group.current.rotation.y = 0.5 + Math.sin(t * 0.08) * 0.35;
    group.current.position.y = Math.sin(t * 0.4) * 0.06;
  });
  return (
    <group ref={group} position={[1.6, -0.3, 0]} scale={1.15}>
      <DroneModel />
    </group>
  );
}

export default function HeroDrone() {
  return (
    <Canvas
      camera={{ position: [0, 0.6, 6], fov: 32 }}
      dpr={[1, 1.6]}
      gl={{ antialias: true, alpha: true }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 6, 3]} intensity={1.4} color="#ffffff" />
      <directionalLight position={[-5, -2, -3]} intensity={0.3} color="#8892a0" />
      <RotatingRig />
    </Canvas>
  );
}
