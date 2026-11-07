import { useStore } from '../state/store'

export function Nav() {
  const { bagCount, setBagOpen, focusProduct, state } = useStore()

  const goCollection = () => {
    focusProduct(null)
    const el = document.getElementById('collection-anchor')
    el?.scrollIntoView({
      behavior: state.reducedMotion ? 'auto' : 'smooth',
    })
  }

  const goRitual = () => {
    focusProduct(null)
    document.getElementById('philosophy')?.scrollIntoView({
      behavior: state.reducedMotion ? 'auto' : 'smooth',
    })
  }

  return (
    <header className="nav">
      <a className="wordmark" href="#top" aria-label="SOLÈ home">
        SOLÈ
      </a>
      <nav className="nav-links" aria-label="Primary">
        <button type="button" onClick={goCollection}>
          Collection
        </button>
        <button type="button" onClick={goRitual}>
          Our Ritual
        </button>
        <button
          type="button"
          className="bag-btn"
          onClick={() => setBagOpen(true)}
          aria-label={`Bag, ${bagCount} items`}
        >
          Bag
          <span className="bag-count" aria-hidden="true">
            {bagCount}
          </span>
        </button>
      </nav>
    </header>
  )
}
