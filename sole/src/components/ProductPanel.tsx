import { PRODUCTS, useStore, type ProductId } from '../state/store'

export function ProductPanel() {
  const { state, focusProduct, addToBag } = useStore()
  const product = PRODUCTS.find((p) => p.id === state.focusedProduct)

  if (!product) return null

  return (
    <aside
      className="product-panel"
      role="dialog"
      aria-label={`${product.name} details`}
    >
      <p className="panel-kicker">Collection</p>
      <h2>{product.name}</h2>
      <p className="panel-benefit">{product.benefit}</p>
      <div className="panel-meta">
        <span>{product.size}</span>
        <span className="panel-price">{product.price}</span>
      </div>
      <div className="panel-actions">
        <button
          type="button"
          className="cta"
          onClick={() => addToBag(product.id as ProductId)}
        >
          Add to bag
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => focusProduct(null)}
        >
          Back to collection
        </button>
      </div>
    </aside>
  )
}
