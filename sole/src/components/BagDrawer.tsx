import { useEffect } from 'react'
import { useStore } from '../state/store'

export function BagDrawer() {
  const { state, setBagOpen, removeFromBag, bagCount } = useStore()
  const open = state.bagOpen

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setBagOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, setBagOpen])

  const total = state.bag.reduce(
    (sum, item) => sum + item.product.priceValue * item.quantity,
    0,
  )

  return (
    <>
      <div
        className={`bag-backdrop ${open ? 'open' : ''}`}
        onClick={() => setBagOpen(false)}
        aria-hidden={!open}
      />
      <aside
        className={`bag-drawer ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Shopping bag"
        aria-hidden={!open}
      >
        <div className="bag-header">
          <h2>Your bag</h2>
          <button
            type="button"
            className="ghost"
            onClick={() => setBagOpen(false)}
            aria-label="Close bag"
          >
            Close
          </button>
        </div>

        {bagCount === 0 ? (
          <p className="bag-empty">Your bag is empty. Explore the collection.</p>
        ) : (
          <ul className="bag-list">
            {state.bag.map((item) => (
              <li key={item.product.id}>
                <div>
                  <strong>{item.product.name}</strong>
                  <span>
                    {item.quantity} × {item.product.price}
                  </span>
                </div>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => removeFromBag(item.product.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="bag-footer">
          <div className="bag-total">
            <span>Total</span>
            <strong>${total}</strong>
          </div>
          <button type="button" className="cta" disabled={bagCount === 0}>
            Checkout · demo
          </button>
        </div>
      </aside>
    </>
  )
}
