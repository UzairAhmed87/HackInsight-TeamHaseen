import * as THREE from 'three'
import { getLidLift, PRODUCT_LAYOUT } from '../lib/cameraPath'
import { useStore, type ProductId } from '../state/store'
import { CreamJar } from './CreamJar'
import { SerumBottle } from './SerumBottle'

function Hotspot({
  id,
  position,
  visible,
}: {
  id: ProductId
  position: [number, number, number]
  visible: boolean
}) {
  const { focusProduct, state } = useStore()
  const active = state.focusedProduct === id

  if (!visible) return null

  return (
    <group position={position}>
      <mesh
        onClick={(e) => {
          e.stopPropagation()
          if (state.cameraMode === 'focus' && state.focusedProduct === id) return
          focusProduct(id)
        }}
        onPointerOver={() => {
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'auto'
        }}
      >
        <sphereGeometry args={[0.09, 24, 24]} />
        <meshStandardMaterial
          color={active ? '#AC624B' : '#F4EEE5'}
          emissive={active ? '#AC624B' : '#D6B99C'}
          emissiveIntensity={active ? 0.55 : 0.25}
          roughness={0.35}
          metalness={0.2}
          transparent
          opacity={0.95}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.4}>
        <ringGeometry args={[0.1, 0.125, 32]} />
        <meshBasicMaterial
          color="#C9B08A"
          transparent
          opacity={active ? 0.7 : 0.35}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}

function mix(
  a: [number, number, number],
  b: [number, number, number],
  t: number,
): [number, number, number] {
  return [
    THREE.MathUtils.lerp(a[0], b[0], t),
    THREE.MathUtils.lerp(a[1], b[1], t),
    THREE.MathUtils.lerp(a[2], b[2], t),
  ]
}

export function Products() {
  const {
    state: { scrollProgress, reducedMotion, focusedProduct, cameraMode },
  } = useStore()

  const lidLift = reducedMotion ? 0 : getLidLift(scrollProgress)
  const spread = reducedMotion
    ? 1
    : cameraMode === 'focus'
      ? 1
      : THREE.MathUtils.smoothstep(scrollProgress, 0.68, 0.9)

  const showHotspots =
    reducedMotion || cameraMode === 'focus' || scrollProgress > 0.78

  const heroAmbient = scrollProgress < 0.12 && !reducedMotion ? 1 : 0

  const dailyPos = mix([0, 0, -0.4], PRODUCT_LAYOUT['daily-veil'].position, spread)
  const nightPos = mix([0, 0, 0], PRODUCT_LAYOUT['night-restore'].position, spread)
  const dropPos = mix([0, 0, -0.4], PRODUCT_LAYOUT['golden-drop'].position, spread)

  const focusNudge = (id: ProductId): [number, number, number] => {
    if (!focusedProduct || focusedProduct === id) return [0, 0, 0]
    if (id === 'daily-veil') return [-0.35, 0, -0.2]
    if (id === 'golden-drop') return [0.35, 0, -0.2]
    return [0, 0, -0.25]
  }

  return (
    <group>
      <group
        position={dailyPos}
        scale={(0.85 + spread * 0.15) * THREE.MathUtils.smoothstep(spread, 0.05, 0.45)}
        visible={spread > 0.04}
      >
        <group position={focusNudge('daily-veil')}>
          <CreamJar
            accent="terracotta"
            lidLift={focusedProduct === 'daily-veil' ? 0.15 : 0}
            scale={PRODUCT_LAYOUT['daily-veil'].scale}
          />
          <Hotspot
            id="daily-veil"
            position={[0, 1.15, 0.35]}
            visible={showHotspots && spread > 0.55}
          />
        </group>
      </group>

      <group position={nightPos}>
        <group position={focusNudge('night-restore')}>
          <CreamJar
            accent="aubergine"
            lidLift={
              spread < 0.5
                ? lidLift
                : focusedProduct === 'night-restore'
                  ? 0.2
                  : 0
            }
            scale={PRODUCT_LAYOUT['night-restore'].scale}
            ambient={heroAmbient}
          />
          <Hotspot
            id="night-restore"
            position={[0, 1.2, 0.4]}
            visible={showHotspots && spread > 0.55}
          />
        </group>
      </group>

      <group
        position={dropPos}
        scale={(0.85 + spread * 0.15) * THREE.MathUtils.smoothstep(spread, 0.05, 0.45)}
        visible={spread > 0.04}
      >
        <group position={focusNudge('golden-drop')}>
          <SerumBottle scale={PRODUCT_LAYOUT['golden-drop'].scale} />
          <Hotspot
            id="golden-drop"
            position={[0, 1.85, 0.3]}
            visible={showHotspots && spread > 0.55}
          />
        </group>
      </group>
    </group>
  )
}
