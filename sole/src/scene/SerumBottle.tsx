import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SerumBottleProps {
  position?: [number, number, number]
  scale?: number
  ambient?: number
}

export function SerumBottle({
  position = [0, 0, 0],
  scale = 1,
  ambient = 0,
}: SerumBottleProps) {
  const group = useRef<THREE.Group>(null)

  useFrame(({ clock }) => {
    if (!group.current || ambient <= 0) return
    group.current.rotation.y =
      Math.sin(clock.elapsedTime * 0.3 + 1) * 0.03 * ambient
    group.current.position.y =
      position[1] + Math.sin(clock.elapsedTime * 0.5 + 0.8) * 0.01 * ambient
  })

  const glassMat = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: '#C27A45',
        metalness: 0.12,
        roughness: 0.16,
        transparent: true,
        opacity: 0.78,
        clearcoat: 0.9,
        clearcoatRoughness: 0.12,
      }),
    [],
  )

  const metalMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#C9B08A',
        metalness: 0.95,
        roughness: 0.22,
      }),
    [],
  )

  const liquidMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#D4894A',
        metalness: 0.05,
        roughness: 0.28,
        transparent: true,
        opacity: 0.88,
      }),
    [],
  )

  return (
    <group ref={group} position={position} scale={scale}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0]}>
        <circleGeometry args={[0.32, 40]} />
        <meshStandardMaterial color="#3A2C2A" transparent opacity={0.16} />
      </mesh>

      {/* Body */}
      <mesh castShadow receiveShadow position={[0, 0.55, 0]} material={glassMat}>
        <cylinderGeometry args={[0.22, 0.26, 1.0, 48]} />
      </mesh>

      {/* Liquid */}
      <mesh position={[0, 0.45, 0]} material={liquidMat}>
        <cylinderGeometry args={[0.17, 0.2, 0.72, 32]} />
      </mesh>

      {/* Shoulder */}
      <mesh castShadow position={[0, 1.1, 0]} material={glassMat}>
        <sphereGeometry args={[0.22, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>

      {/* Neck */}
      <mesh castShadow position={[0, 1.28, 0]} material={glassMat}>
        <cylinderGeometry args={[0.07, 0.09, 0.28, 24]} />
      </mesh>

      {/* Dropper collar */}
      <mesh castShadow position={[0, 1.44, 0]} material={metalMat}>
        <cylinderGeometry args={[0.1, 0.1, 0.1, 24]} />
      </mesh>

      {/* Dropper bulb */}
      <mesh castShadow position={[0, 1.62, 0]} material={metalMat}>
        <sphereGeometry args={[0.11, 24, 16]} />
      </mesh>

      {/* Pipette tip hint */}
      <mesh position={[0, 1.05, 0]}>
        <cylinderGeometry args={[0.015, 0.02, 0.55, 8]} />
        <meshStandardMaterial color="#C9B08A" metalness={0.8} roughness={0.3} />
      </mesh>
    </group>
  )
}
