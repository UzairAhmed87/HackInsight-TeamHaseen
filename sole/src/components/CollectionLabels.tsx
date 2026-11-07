import { PRODUCTS, useStore } from '../state/store'

export function CollectionLabels() {
  const {
    state: { scrollProgress, reducedMotion, focusedProduct, cameraMode, isMobile },
    focusProduct,
  } = useStore()

  const visible =
    reducedMotion ||
    cameraMode === 'focus' ||
    scrollProgress > 0.78

  if (!visible || focusedProduct) return null

  return (
    <div className={`collection-labels ${isMobile ? 'mobile' : ''}`}>
      {PRODUCTS.map((product) => (
        <button
          key={product.id}
          type="button"
          className={`hotspot-label hotspot-${product.id}`}
          onClick={() => focusProduct(product.id)}
          aria-label={`View ${product.name}`}
        >
          <span className="hotspot-dot" aria-hidden="true" />
          {product.name}
        </button>
      ))}
    </div>
  )
}
