import * as THREE from 'three'
import type { ProductId } from '../state/store'

export interface CameraKeyframe {
  position: THREE.Vector3
  lookAt: THREE.Vector3
  fov: number
}

/** Scroll-driven cinematic path — progress 0..1 */
export function getScrollCamera(
  progress: number,
  isMobile: boolean,
): CameraKeyframe {
  const p = THREE.MathUtils.clamp(progress, 0, 1)

  const hero: CameraKeyframe = {
    position: new THREE.Vector3(
      isMobile ? 0.55 : 1.15,
      isMobile ? 1.05 : 1.2,
      isMobile ? 3.4 : 3.8,
    ),
    lookAt: new THREE.Vector3(0, 0.55, 0),
    fov: isMobile ? 42 : 38,
  }

  const topDown: CameraKeyframe = {
    position: new THREE.Vector3(0.15, 3.4, 0.9),
    lookAt: new THREE.Vector3(0, 0.7, 0),
    fov: 36,
  }

  const creamMacro: CameraKeyframe = {
    position: new THREE.Vector3(0.05, 1.55, 0.55),
    lookAt: new THREE.Vector3(0, 0.72, 0),
    fov: 28,
  }

  const creamFill: CameraKeyframe = {
    position: new THREE.Vector3(0, 1.05, 0.22),
    lookAt: new THREE.Vector3(0, 0.78, 0),
    fov: 24,
  }

  const application: CameraKeyframe = {
    position: new THREE.Vector3(-0.2, 0.95, 1.1),
    lookAt: new THREE.Vector3(0.1, 0.55, 0),
    fov: 30,
  }

  const collection: CameraKeyframe = {
    position: new THREE.Vector3(
      isMobile ? 0.2 : 0.35,
      isMobile ? 1.55 : 1.75,
      isMobile ? 5.2 : 6.2,
    ),
    lookAt: new THREE.Vector3(0, 0.55, 0),
    fov: isMobile ? 40 : 36,
  }

  if (p < 0.18) {
    return lerpKey(hero, topDown, smooth(p / 0.18))
  }
  if (p < 0.32) {
    return lerpKey(topDown, creamMacro, smooth((p - 0.18) / 0.14))
  }
  if (p < 0.48) {
    return lerpKey(creamMacro, creamFill, smooth((p - 0.32) / 0.16))
  }
  if (p < 0.62) {
    return lerpKey(creamFill, application, smooth((p - 0.48) / 0.14))
  }
  return lerpKey(application, collection, smooth((p - 0.62) / 0.38))
}

export function getProductCamera(
  id: ProductId,
  isMobile: boolean,
): CameraKeyframe {
  const views: Record<ProductId, CameraKeyframe> = {
    'daily-veil': {
      position: new THREE.Vector3(
        isMobile ? -0.9 : -1.35,
        isMobile ? 1.15 : 1.25,
        isMobile ? 2.6 : 2.9,
      ),
      lookAt: new THREE.Vector3(isMobile ? -1.05 : -1.4, 0.55, 0.1),
      fov: isMobile ? 38 : 34,
    },
    'night-restore': {
      position: new THREE.Vector3(
        isMobile ? 0.15 : 0.2,
        isMobile ? 1.2 : 1.35,
        isMobile ? 2.55 : 2.85,
      ),
      lookAt: new THREE.Vector3(0.05, 0.6, 0.05),
      fov: isMobile ? 38 : 34,
    },
    'golden-drop': {
      position: new THREE.Vector3(
        isMobile ? 1.1 : 1.55,
        isMobile ? 1.25 : 1.4,
        isMobile ? 2.7 : 3.0,
      ),
      lookAt: new THREE.Vector3(isMobile ? 1.15 : 1.45, 0.7, 0.05),
      fov: isMobile ? 38 : 34,
    },
  }
  return views[id]
}

export function getLidLift(progress: number): number {
  // Lid begins rising during top-down approach
  if (progress < 0.2) return 0
  if (progress < 0.38) return smooth((progress - 0.2) / 0.18)
  if (progress < 0.72) return 1
  return THREE.MathUtils.clamp(1 - (progress - 0.72) / 0.2, 0, 1)
}

export function getCreamReveal(progress: number): number {
  if (progress < 0.28) return 0
  if (progress < 0.55) return smooth((progress - 0.28) / 0.27)
  if (progress < 0.7) return 1
  return THREE.MathUtils.clamp(1 - (progress - 0.7) / 0.18, 0, 1)
}

function smooth(t: number) {
  const x = THREE.MathUtils.clamp(t, 0, 1)
  return x * x * (3 - 2 * x)
}

function lerpKey(
  a: CameraKeyframe,
  b: CameraKeyframe,
  t: number,
): CameraKeyframe {
  return {
    position: a.position.clone().lerp(b.position, t),
    lookAt: a.lookAt.clone().lerp(b.lookAt, t),
    fov: THREE.MathUtils.lerp(a.fov, b.fov, t),
  }
}

export const PRODUCT_LAYOUT = {
  'daily-veil': { position: [-1.45, 0, 0.15] as [number, number, number], scale: 1 },
  'night-restore': { position: [0.05, 0, 0.35] as [number, number, number], scale: 1.05 },
  'golden-drop': { position: [1.5, 0, 0.05] as [number, number, number], scale: 1 },
}
