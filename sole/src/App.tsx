import { useAppSetup } from './hooks/useAppSetup'
import { BagDrawer } from './components/BagDrawer'
import { CollectionLabels } from './components/CollectionLabels'
import { Footer } from './components/Footer'
import { HeroOverlay } from './components/HeroOverlay'
import { Nav } from './components/Nav'
import { Philosophy } from './components/Philosophy'
import { ProductPanel } from './components/ProductPanel'
import { SkipControl } from './components/SkipControl'
import { Experience } from './scene/Experience'
import { StoreProvider, useStore } from './state/store'

function Shell() {
  useAppSetup()
  const {
    state: { sceneReady, reducedMotion },
  } = useStore()

  return (
    <div id="top" className="app">
      <a className="skip-link" href="#philosophy">
        Skip to content
      </a>

      <Experience />

      <div className={`poster ${sceneReady ? 'fade' : ''}`} aria-hidden="true">
        <div className="poster-glow" />
        <p>SOLÈ</p>
      </div>

      <Nav />
      <HeroOverlay />
      <SkipControl />
      <CollectionLabels />
      <ProductPanel />
      <BagDrawer />

      <main>
        <section
          id="journey"
          className="journey"
          aria-label="Cinematic product journey"
          style={{ height: reducedMotion ? '100svh' : '420svh' }}
        >
          <div className="journey-pin" />
        </section>

        <section
          id="collection-anchor"
          className="collection-hold"
          aria-label="Product collection"
        />

        <Philosophy />
        <Footer />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  )
}
