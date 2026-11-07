import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getCreamTexture, getTravertineTexture } from '../lib/textures'

interface CreamJarProps {
  position?: [number, number, number]
  scale?: number
  lidLift?: number
  accent?: 'terracotta' | 'aubergine'
  ambient?: number
}

export function CreamJar({
  position = [0, 0, 0],
  scale = 1,
  lidLift = 0,
  accent = 'terracotta',
  ambient = 0,
}: CreamJarProps) {
  const group = useRef<THREE.Group>(null)
  const lid = useRef<THREE.Group>(null)
  const creamMap = useMemo(() => getCreamTexture(), [])
  const stoneMap = useMemo(() => getTravertineTexture(), [])
  const rimColor = '#C9B08A'

  useFrame(({ clock }) => {
    if (!group.current) return
    if (ambient > 0) {
      group.current.rotation.y =
        Math.sin(clock.elapsedTime * 0.35) * 0.025 * ambient
      group.current.position.y =
        position[1] + Math.sin(clock.elapsedTime * 0.55) * 0.008 * ambient
    }
    if (lid.current) {
      lid.current.position.y = 0.78 + lidLift * 0.55
      lid.current.rotation.y = lidLift * 0.35
      lid.current.rotation.z = lidLift * 0.08
    }
  })

  const glassMat = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: accent === 'terracotta' ? '#AC624B' : '#392B35',
        metalness: 0.15,
        roughness: 0.22,
        transparent: true,
        opacity: 0.82,
        clearcoat: 0.85,
        clearcoatRoughness: 0.18,
        envMapIntensity: 0.8,
      }),
    [accent],
  )

  const metalMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: rimColor,
        metalness: 0.92,
        roughness: 0.28,
      }),
    [],
  )

  const creamMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: creamMap,
        color: '#F7F0E6',
        roughness: 0.72,
        metalness: 0,
      }),
    [creamMap],
  )

  const labelMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: stoneMap,
        color: '#F4EEE5',
        roughness: 0.85,
        metalness: 0,
      }),
    [stoneMap],
  )

  return (
    <group ref={group} position={position} scale={scale}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0]} receiveShadow>
        <circleGeometry args={[0.55, 48]} />
        <meshStandardMaterial color="#3A2C2A" transparent opacity={0.18} />
      </mesh>

      <mesh castShadow receiveShadow position={[0, 0.38, 0]} material={glassMat}>
        <cylinderGeometry args={[0.42, 0.46, 0.72, 64]} />
      </mesh>

      <mesh position={[0, 0.4, 0]}>
        <cylinderGeometry args={[0.36, 0.39, 0.62, 48]} />
        <meshStandardMaterial
          color={accent === 'terracotta' ? '#8E4E3C' : '#2C2128'}
          roughness={0.4}
          metalness={0.1}
          transparent
          opacity={0.35}
        />
      </mesh>

      <mesh castShadow position={[0, 0.48, 0]} material={creamMat}>
        <cylinderGeometry args={[0.34, 0.35, 0.22, 48]} />
      </mesh>
      {/* Domed cream surface — only above the rim once the lid lifts */}
      <mesh
        position={[0, 0.58, 0]}
        material={creamMat}
        visible={lidLift > 0.08}
        scale={[1, 0.55 + lidLift * 0.45, 1]}
      >
        <sphereGeometry args={[0.3, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>

      <mesh
        castShadow
        position={[0, 0.72, 0]}
        rotation={[Math.PI / 2, 0, 0]}
        material={metalMat}
      >
        <torusGeometry args={[0.43, 0.025, 16, 64]} />
      </mesh>

      <mesh position={[0, 0.32, 0.01]} material={labelMat}>
        <cylinderGeometry args={[0.435, 0.455, 0.22, 64, 1, true]} />
      </mesh>

      <group ref={lid} position={[0, 0.78, 0]}>
        <mesh castShadow material={glassMat}>
          <cylinderGeometry args={[0.44, 0.44, 0.12, 64]} />
        </mesh>
        <mesh castShadow position={[0, 0.08, 0]} material={metalMat}>
          <cylinderGeometry args={[0.4, 0.42, 0.06, 64]} />
        </mesh>
        <mesh position={[0, 0.115, 0]} material={metalMat}>
          <cylinderGeometry args={[0.12, 0.14, 0.02, 32]} />
        </mesh>
      </group>
    </group>
  )
}
