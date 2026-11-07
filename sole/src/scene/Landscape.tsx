import { useMemo } from 'react'
import * as THREE from 'three'
import { getSandTexture, getTravertineTexture } from '../lib/textures'

function Rock({
  position,
  scale = 1,
  rotation = [0, 0, 0] as [number, number, number],
}: {
  position: [number, number, number]
  scale?: number | [number, number, number]
  rotation?: [number, number, number]
}) {
  const map = useMemo(() => getTravertineTexture(), [])
  return (
    <mesh
      castShadow
      receiveShadow
      position={position}
      scale={scale}
      rotation={rotation}
    >
      <icosahedronGeometry args={[1, 2]} />
      <meshStandardMaterial
        map={map}
        color="#E8DCCB"
        roughness={0.88}
        metalness={0.02}
      />
    </mesh>
  )
}

export function Landscape() {
  const sandMap = useMemo(() => getSandTexture(), [])

  const groundGeo = useMemo(() => {
    const geo = new THREE.PlaneGeometry(28, 28, 80, 80)
    const pos = geo.attributes.position
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const y = pos.getY(i)
      const dunes =
        Math.sin(x * 0.35) * 0.18 +
        Math.cos(y * 0.28) * 0.14 +
        Math.sin((x + y) * 0.15) * 0.1
      pos.setZ(i, dunes)
    }
    geo.computeVertexNormals()
    return geo
  }, [])

  return (
    <group>
      <mesh
        geometry={groundGeo}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.02, 0]}
        receiveShadow
      >
        <meshStandardMaterial
          map={sandMap}
          color="#D6B99C"
          roughness={0.95}
          metalness={0}
        />
      </mesh>

      {/* Hero plinth */}
      <mesh castShadow receiveShadow position={[0, 0.12, 0]}>
        <cylinderGeometry args={[1.1, 1.25, 0.28, 6]} />
        <meshStandardMaterial
          map={sandMap}
          color="#E6D7C4"
          roughness={0.88}
          metalness={0.04}
        />
      </mesh>

      <Rock position={[-2.8, 0.35, -1.8]} scale={[1.2, 0.7, 1]} rotation={[0.2, 0.4, 0.1]} />
      <Rock position={[2.6, 0.45, -2.2]} scale={[0.9, 1.1, 0.8]} rotation={[0.1, -0.6, 0]} />
      <Rock position={[-1.8, 0.25, 2.4]} scale={[0.7, 0.45, 0.9]} rotation={[0, 1.1, 0.15]} />
      <Rock position={[3.4, 0.3, 1.2]} scale={[1.1, 0.5, 0.7]} rotation={[0.15, 0.2, -0.1]} />
      <Rock position={[0.8, 0.55, -3.5]} scale={[1.6, 0.9, 1.2]} rotation={[0.05, 0.8, 0]} />
      <Rock position={[-4.2, 0.7, -0.4]} scale={[1.3, 1.4, 1]} rotation={[0.2, -0.3, 0.05]} />

      {/* Soft horizon haze plane */}
      <mesh position={[0, 2.2, -10]}>
        <planeGeometry args={[40, 10]} />
        <meshBasicMaterial color="#E8D5BC" transparent opacity={0.45} />
      </mesh>
    </group>
  )
}
