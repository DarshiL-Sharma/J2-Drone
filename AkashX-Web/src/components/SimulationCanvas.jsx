import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import SimulationScene from './SimulationScene';

export default function SimulationCanvas({ mode, onUpdate }) {
  return (
    <Canvas camera={{ position: [6, 5, 7], fov: 42 }} dpr={[1, 1.5]} shadows>
      <color attach="background" args={['#0b0d10']} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[5, 8, 4]} intensity={1.3} castShadow />
      <directionalLight position={[-6, 3, -4]} intensity={0.3} color="#8892a0" />
      <SimulationScene mode={mode} onUpdate={onUpdate} />
      <OrbitControls
        enablePan={false}
        minDistance={4}
        maxDistance={13}
        maxPolarAngle={Math.PI / 2.1}
      />
    </Canvas>
  );
}
