import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getCreamReveal } from '../lib/cameraPath'
import { getCreamTexture, getSkinMacroTexture } from '../lib/textures'
import { useStore } from '../state/store'

/** Cream → skin macro bridge during the cinematic mid-sequence */
export function MacroPlane() {
  const {
    state: { scrollProgress, reducedMotion },
  } = useStore()
  const creamRef = useRef<THREE.Mesh>(null)
  const skinRef = useRef<THREE.Mesh>(null)
  const creamMap = useMemo(() => getCreamTexture(), [])
  const skinMap = useMemo(() => getSkinMacroTexture(), [])

  useFrame(() => {
    const reveal = reducedMotion ? 0 : getCreamReveal(scrollProgress)
    if (creamRef.current) {
      const mat = creamRef.current.material as THREE.MeshBasicMaterial
      // Visible primarily during cream fill / application
      const creamOpacity =
        scrollProgress > 0.35 && scrollProgress < 0.58
          ? THREE.MathUtils.smoothstep(scrollProgress, 0.35, 0.42) *
            (1 - THREE.MathUtils.smoothstep(scrollProgress, 0.52, 0.58))
          : 0
      mat.opacity = creamOpacity * 0.95
      creamRef.current.visible = creamOpacity > 0.02
      creamRef.current.scale.setScalar(0.9 + reveal * 0.35)
    }
    if (skinRef.current) {
      const mat = skinRef.current.material as THREE.MeshBasicMaterial
      const skinOpacity =
        scrollProgress > 0.5 && scrollProgress < 0.78
          ? THREE.MathUtils.smoothstep(scrollProgress, 0.5, 0.58) *
            (1 - THREE.MathUtils.smoothstep(scrollProgress, 0.7, 0.78))
          : 0
      mat.opacity = skinOpacity * 0.92
      skinRef.current.visible = skinOpacity > 0.02
    }
  })

  return (
    <group position={[0, 0.9, 0.4]}>
      <mesh ref={creamRef} rotation={[-0.9, 0.1, 0.05]} visible={false}>
        <planeGeometry args={[1.4, 1.4]} />
        <meshBasicMaterial
          map={creamMap}
          transparent
          opacity={0}
          depthWrite={false}
        />
      </mesh>
      <mesh ref={skinRef} rotation={[-0.55, -0.05, 0.02]} position={[0.15, -0.1, 0.35]} visible={false}>
        <planeGeometry args={[1.8, 1.2]} />
        <meshBasicMaterial
          map={skinMap}
          transparent
          opacity={0}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}
