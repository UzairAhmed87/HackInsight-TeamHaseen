import { useStore } from '../state/store'

export function HeroOverlay() {
  const {
    state: { scrollProgress, reducedMotion, sceneReady },
  } = useStore()

  const hide = !reducedMotion && scrollProgress > 0.12
  const opacity = hide ? Math.max(0, 1 - (scrollProgress - 0.08) / 0.1) : 1

  const explore = () => {
    document.getElementById('journey')?.scrollIntoView({
      behavior: reducedMotion ? 'auto' : 'smooth',
    })
  }

  return (
    <div
      className="hero-overlay"
      style={{ opacity, pointerEvents: opacity < 0.2 ? 'none' : 'auto' }}
      aria-hidden={opacity < 0.2}
    >
      <div className="hero-copy">
        <h1>A slower ritual. A softer glow.</h1>
        <p>
          Mineral-born skincare shaped by warm light, amber glass, and unhurried
          care.
        </p>
        <button type="button" className="cta" onClick={explore}>
          Explore the ritual
        </button>
      </div>
      <div className={`scroll-cue ${sceneReady ? 'ready' : ''}`} aria-hidden="true">
        <span>Scroll</span>
        <div className="scroll-line" />
      </div>
    </div>
  )
}
