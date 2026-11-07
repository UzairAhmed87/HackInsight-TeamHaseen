import { useStore } from '../state/store'

export function SkipControl() {
  const {
    state: { scrollProgress, reducedMotion, focusedProduct },
    focusProduct,
  } = useStore()

  if (reducedMotion || focusedProduct || scrollProgress > 0.82) return null
  if (scrollProgress < 0.05) return null

  const skip = () => {
    focusProduct(null)
    document.getElementById('collection-anchor')?.scrollIntoView({
      behavior: 'smooth',
    })
  }

  return (
    <button type="button" className="skip-control" onClick={skip}>
      Skip to collection
    </button>
  )
}
