import { useEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import gsap from 'gsap'
import * as THREE from 'three'
import {
  getProductCamera,
  getScrollCamera,
  type CameraKeyframe,
} from '../lib/cameraPath'
import { useStore, type ProductId } from '../state/store'

/**
 * Single camera-state owner.
 * Scroll drives the cinematic path while mode === 'scroll'.
 * Hotspot focus takes ownership until Back to collection.
 */
export function CameraController() {
  const { camera } = useThree()
  const {
    state: {
      scrollProgress,
      cameraMode,
      focusedProduct,
      reducedMotion,
      isMobile,
    },
  } = useStore()

  const current = useRef({
    position: new THREE.Vector3(1.15, 1.2, 3.8),
    lookAt: new THREE.Vector3(0, 0.55, 0),
    fov: 38,
  })
  const lookTarget = useRef(new THREE.Vector3(0, 0.55, 0))
  const tweening = useRef(false)
  const lastFocus = useRef<ProductId | null>(null)
  const pointer = useRef({ x: 0, y: 0 })

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (isMobile || reducedMotion) return
      pointer.current.x = (e.clientX / window.innerWidth - 0.5) * 2
      pointer.current.y = (e.clientY / window.innerHeight - 0.5) * 2
    }
    window.addEventListener('pointermove', onMove)
    return () => window.removeEventListener('pointermove', onMove)
  }, [isMobile, reducedMotion])

  useEffect(() => {
    if (cameraMode !== 'focus' || !focusedProduct) {
      lastFocus.current = null
      return
    }
    if (lastFocus.current === focusedProduct && tweening.current) return

    lastFocus.current = focusedProduct
    const target = getProductCamera(focusedProduct, isMobile)
    animateTo(target)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraMode, focusedProduct, isMobile])

  useEffect(() => {
    if (cameraMode === 'scroll' && lastFocus.current !== null) {
      // Returning from focus — ease back to scroll path pose
      lastFocus.current = null
      const target = getScrollCamera(Math.max(scrollProgress, 0.85), isMobile)
      animateTo(target)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraMode])

  function animateTo(target: CameraKeyframe) {
    tweening.current = true
    const duration = reducedMotion ? 0.01 : 1.15
    gsap.to(current.current.position, {
      x: target.position.x,
      y: target.position.y,
      z: target.position.z,
      duration,
      ease: 'power3.inOut',
    })
    gsap.to(current.current.lookAt, {
      x: target.lookAt.x,
      y: target.lookAt.y,
      z: target.lookAt.z,
      duration,
      ease: 'power3.inOut',
    })
    gsap.to(current.current, {
      fov: target.fov,
      duration,
      ease: 'power3.inOut',
      onComplete: () => {
        tweening.current = false
      },
    })
  }

  useFrame((_, delta) => {
    const persp = camera as THREE.PerspectiveCamera

    if (cameraMode === 'scroll' && !tweening.current) {
      const key = getScrollCamera(
        reducedMotion ? Math.max(scrollProgress, 0.9) : scrollProgress,
        isMobile,
      )
      const damp = reducedMotion ? 8 : 4
      current.current.position.lerp(key.position, 1 - Math.exp(-damp * delta))
      current.current.lookAt.lerp(key.lookAt, 1 - Math.exp(-damp * delta))
      current.current.fov = THREE.MathUtils.damp(
        current.current.fov,
        key.fov,
        damp,
        delta,
      )
    }

    const parallax =
      cameraMode === 'scroll' && !reducedMotion && !isMobile ? 0.08 : 0
    const px = pointer.current.x * parallax
    const py = -pointer.current.y * parallax * 0.5

    persp.position.set(
      current.current.position.x + px,
      current.current.position.y + py,
      current.current.position.z,
    )
    lookTarget.current.copy(current.current.lookAt)
    lookTarget.current.x += px * 0.3
    persp.lookAt(lookTarget.current)
    if (Math.abs(persp.fov - current.current.fov) > 0.01) {
      persp.fov = current.current.fov
      persp.updateProjectionMatrix()
    }
  })

  return null
}
