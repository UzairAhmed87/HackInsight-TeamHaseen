import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { useStore } from '../state/store'
import { CameraController } from './CameraController'
import { Landscape } from './Landscape'
import { Lighting } from './Lighting'
import { MacroPlane } from './MacroPlane'
import { Products } from './Products'

function SceneReady() {
  const { setSceneReady } = useStore()
  useEffect(() => {
    const t = window.setTimeout(() => setSceneReady(true), 400)
    return () => window.clearTimeout(t)
  }, [setSceneReady])
  return null
}

export function Experience() {
  const {
    state: { isMobile, reducedMotion },
  } = useStore()

  return (
    <div className="experience" aria-hidden={!reducedMotion}>
      <Canvas
        shadows={!isMobile}
        dpr={isMobile ? [1, 1.15] : [1, 1.5]}
        camera={{ position: [1.15, 1.2, 3.8], fov: 38, near: 0.1, far: 40 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          toneMappingExposure: 1.05,
          stencil: false,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor('#E8D9C4')
        }}
      >
        <Suspense fallback={null}>
          <Lighting />
          <Landscape />
          <Products />
          <MacroPlane />
          <CameraController />
          <SceneReady />
        </Suspense>
      </Canvas>
    </div>
  )
}
