import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import DroneModel from './DroneModel';

const BUILDINGS = [
  { pos: [-3.2, 0, -2.4], size: [0.8, 1.4, 0.8] },
  { pos: [2.6, 0, -1.6], size: [1, 1.8, 1] },
  { pos: [3.4, 0, 1.8], size: [0.7, 1, 0.7] },
  { pos: [-2.4, 0, 2.2], size: [0.9, 0.8, 0.9] },
  { pos: [0.4, 0, -3.4], size: [0.6, 1.1, 0.6] },
];

const PEOPLE = [
  [-1.6, 1.4],
  [2.1, -0.6],
  [-0.4, 2.6],
];

function buildPath(mode) {
  const pts = [];
  const y = 1.6;
  if (mode === 'grid') {
    const rows = 5;
    const half = 3.4;
    for (let i = 0; i < rows; i++) {
      const z = -half + (i * (half * 2)) / (rows - 1);
      if (i % 2 === 0) {
        pts.push([-half, y, z], [half, y, z]);
      } else {
        pts.push([half, y, z], [-half, y, z]);
      }
    }
  } else if (mode === 'zigzag') {
    const steps = 8;
    for (let i = 0; i <= steps; i++) {
      const x = -3.4 + (i * 6.8) / steps;
      const z = i % 2 === 0 ? -2.6 : 2.6;
      pts.push([x, y, z]);
    }
  } else if (mode === 'spiral') {
    const turns = 3;
    const steps = 60;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const angle = t * turns * Math.PI * 2;
      const radius = 0.4 + t * 3.2;
      pts.push([Math.cos(angle) * radius, y, Math.sin(angle) * radius]);
    }
  } else if (mode === 'waypoint') {
    pts.push([-3.4, y, -2.8], [1.2, y, -1.4], [2.8, y, 1.6], [-1, y, 2.8], [0, y, 0]);
  } else {
    // return
    pts.push([2, y, 2], [1, y * 1.4, 1], [0, y * 2, 0], [0, y * 2.6, 0]);
  }
  return pts.map((p) => new THREE.Vector3(...p));
}

export default function SimulationScene({ mode, onUpdate }) {
  const drone = useRef();
  const t = useRef(0);

  const curve = useMemo(() => {
    const pts = buildPath(mode);
    t.current = 0;
    return new THREE.CatmullRomCurve3(pts, mode !== 'return', 'catmullrom', 0.2);
  }, [mode]);

  useFrame((_, delta) => {
    if (!drone.current) return;
    const speed = mode === 'return' ? 0.08 : 0.045;
    t.current = (t.current + delta * speed) % 1;
    const pos = curve.getPointAt(mode === 'return' ? Math.min(t.current * 1.6, 1) : t.current);
    const lookAhead = curve.getPointAt(Math.min(t.current + 0.01, 0.999));
    drone.current.position.copy(pos);
    drone.current.lookAt(lookAhead);
    if (onUpdate) {
      onUpdate({
        altitude: pos.y.toFixed(1),
        x: pos.x.toFixed(1),
        z: pos.z.toFixed(1),
      });
    }
  });

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.02, 0]}>
        <planeGeometry args={[14, 14]} />
        <meshStandardMaterial color="#0b0d10" roughness={1} />
      </mesh>
      <gridHelper args={[14, 28, '#24282D', '#171a1e']} />

      {/* search zone boundary */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[3.55, 3.6, 64]} />
        <meshBasicMaterial color="#BFC5CC" transparent opacity={0.4} />
      </mesh>

      {BUILDINGS.map((b, i) => (
        <mesh key={i} position={[b.pos[0], b.size[1] / 2, b.pos[2]]} castShadow>
          <boxGeometry args={b.size} />
          <meshStandardMaterial color="#15181c" roughness={0.8} />
        </mesh>
      ))}

      {PEOPLE.map((p, i) => (
        <group key={i} position={[p[0], 0.05, p[1]]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.14, 0.17, 24]} />
            <meshBasicMaterial color="#C9A15A" />
          </mesh>
        </group>
      ))}

      <group ref={drone} scale={2.2}>
        <DroneModel explode={0} />
      </group>
    </group>
  );
}
