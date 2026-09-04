import { useMemo } from 'react';

const metal = { color: '#c7cbd1', roughness: 0.45, metalness: 0.65 };
const dark = { color: '#1a1d21', roughness: 0.55, metalness: 0.3 };
const carbon = { color: '#0e1013', roughness: 0.35, metalness: 0.55 };
const board = { color: '#2b8a5e', roughness: 0.5, metalness: 0.2 };
const lens = { color: '#0a0c0e', roughness: 0.15, metalness: 0.8 };
const amber = { color: '#c9a15a', roughness: 0.4, metalness: 0.4 };

// Assembled (rest) local offsets — a tight, real drone layout.
const REST = {
  frame: [0, 0, 0],
  motors: [0, 0.03, 0],
  props: [0, 0.09, 0],
  esc: [0.12, -0.03, 0.05],
  pixhawk: [0, 0.1, -0.05],
  battery: [0, -0.12, -0.05],
  rxtx: [-0.18, 0.14, -0.32],
  rpi: [0, 0.16, -0.2],
  rgb: [0.06, -0.04, 0.42],
  thermal: [-0.06, -0.04, 0.42],
  telemetry: [0.18, 0.14, -0.32],
  ground: [0, -1.1, -1.6],
};

const ARM_DIRS = [
  [1, 1],
  [1, -1],
  [-1, 1],
  [-1, -1],
];

function Part({ id, explode, target, highlighted, children }) {
  const rest = REST[id];
  const pos = useMemo(
    () => rest.map((v, i) => v + (target[i] - v) * explode),
    [explode, rest, target]
  );
  return (
    <group position={pos}>
      {highlighted && (
        <mesh>
          <sphereGeometry args={[0.34, 12, 12]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.06} />
        </mesh>
      )}
      {children}
    </group>
  );
}

export default function DroneModel({ explode = 0, explodeTargets, highlighted = null }) {
  const targets = explodeTargets || REST;

  return (
    <group>
      {/* FRAME */}
      <Part id="frame" explode={explode} target={targets.frame} highlighted={highlighted === 'frame'}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[0.34, 0.05, 0.34]} />
          <meshStandardMaterial {...carbon} />
        </mesh>
        {ARM_DIRS.map(([x, z], i) => (
          <mesh key={i} position={[x * 0.32, 0, z * 0.32]} rotation={[0, Math.atan2(z, x), 0]} castShadow>
            <boxGeometry args={[0.62, 0.028, 0.045]} />
            <meshStandardMaterial {...carbon} />
          </mesh>
        ))}
        <mesh position={[0, -0.06, 0.05]}>
          <boxGeometry args={[0.16, 0.03, 0.2]} />
          <meshStandardMaterial {...dark} />
        </mesh>
      </Part>

      {/* MOTORS */}
      <Part id="motors" explode={explode} target={targets.motors} highlighted={highlighted === 'motors'}>
        {ARM_DIRS.map(([x, z], i) => (
          <mesh key={i} position={[x * 0.58, 0, z * 0.58]} castShadow>
            <cylinderGeometry args={[0.045, 0.05, 0.06, 16]} />
            <meshStandardMaterial {...metal} />
          </mesh>
        ))}
      </Part>

      {/* PROPELLERS */}
      <Part id="props" explode={explode} target={targets.props} highlighted={highlighted === 'props'}>
        {ARM_DIRS.map(([x, z], i) => (
          <group key={i} position={[x * 0.58, 0, z * 0.58]}>
            <mesh rotation={[0, (i * Math.PI) / 4, 0]} castShadow>
              <boxGeometry args={[0.42, 0.006, 0.03]} />
              <meshStandardMaterial {...dark} />
            </mesh>
            <mesh rotation={[0, (i * Math.PI) / 4 + Math.PI / 2, 0]} castShadow>
              <boxGeometry args={[0.42, 0.006, 0.03]} />
              <meshStandardMaterial {...dark} />
            </mesh>
          </group>
        ))}
      </Part>

      {/* ESC */}
      <Part id="esc" explode={explode} target={targets.esc} highlighted={highlighted === 'esc'}>
        <mesh castShadow>
          <boxGeometry args={[0.1, 0.02, 0.05]} />
          <meshStandardMaterial {...board} />
        </mesh>
      </Part>

      {/* PIXHAWK */}
      <Part id="pixhawk" explode={explode} target={targets.pixhawk} highlighted={highlighted === 'pixhawk'}>
        <mesh castShadow>
          <boxGeometry args={[0.09, 0.03, 0.09]} />
          <meshStandardMaterial {...dark} />
        </mesh>
      </Part>

      {/* BATTERY */}
      <Part id="battery" explode={explode} target={targets.battery} highlighted={highlighted === 'battery'}>
        <mesh castShadow>
          <boxGeometry args={[0.16, 0.05, 0.24]} />
          <meshStandardMaterial {...amber} />
        </mesh>
      </Part>

      {/* RX/TX */}
      <Part id="rxtx" explode={explode} target={targets.rxtx} highlighted={highlighted === 'rxtx'}>
        <mesh castShadow>
          <cylinderGeometry args={[0.006, 0.006, 0.16, 8]} />
          <meshStandardMaterial {...metal} />
        </mesh>
      </Part>

      {/* RASPBERRY PI */}
      <Part id="rpi" explode={explode} target={targets.rpi} highlighted={highlighted === 'rpi'}>
        <mesh castShadow>
          <boxGeometry args={[0.1, 0.018, 0.07]} />
          <meshStandardMaterial {...board} />
        </mesh>
      </Part>

      {/* RGB CAMERA */}
      <Part id="rgb" explode={explode} target={targets.rgb} highlighted={highlighted === 'rgb'}>
        <mesh castShadow>
          <boxGeometry args={[0.06, 0.06, 0.05]} />
          <meshStandardMaterial {...dark} />
        </mesh>
        <mesh position={[0, 0, 0.03]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.02, 0.02, 0.02, 16]} />
          <meshStandardMaterial {...lens} />
        </mesh>
      </Part>

      {/* THERMAL CAMERA */}
      <Part id="thermal" explode={explode} target={targets.thermal} highlighted={highlighted === 'thermal'}>
        <mesh castShadow>
          <boxGeometry args={[0.045, 0.045, 0.045]} />
          <meshStandardMaterial {...dark} />
        </mesh>
        <mesh position={[0, 0, 0.025]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.014, 0.014, 0.015, 16]} />
          <meshStandardMaterial {...lens} />
        </mesh>
      </Part>

      {/* TELEMETRY RADIO */}
      <Part id="telemetry" explode={explode} target={targets.telemetry} highlighted={highlighted === 'telemetry'}>
        <mesh castShadow>
          <boxGeometry args={[0.05, 0.02, 0.03]} />
          <meshStandardMaterial {...metal} />
        </mesh>
        <mesh position={[0, 0.06, 0]}>
          <cylinderGeometry args={[0.004, 0.004, 0.1, 6]} />
          <meshStandardMaterial {...metal} />
        </mesh>
      </Part>

      {/* GROUND SUPPORT SYSTEM */}
      <Part id="ground" explode={explode} target={targets.ground} highlighted={highlighted === 'ground'}>
        <mesh castShadow rotation={[-0.35, 0, 0]}>
          <boxGeometry args={[0.4, 0.26, 0.02]} />
          <meshStandardMaterial {...dark} />
        </mesh>
        <mesh position={[0, -0.13, 0.09]}>
          <boxGeometry args={[0.4, 0.02, 0.2]} />
          <meshStandardMaterial {...metal} />
        </mesh>
      </Part>
    </group>
  );
}

export { REST };
