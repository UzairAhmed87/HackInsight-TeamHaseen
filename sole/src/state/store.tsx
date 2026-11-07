import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react'

export type ProductId = 'daily-veil' | 'night-restore' | 'golden-drop'

export type CameraMode = 'scroll' | 'focus' | 'transition'

export interface Product {
  id: ProductId
  name: string
  benefit: string
  size: string
  price: string
  priceValue: number
}

export const PRODUCTS: Product[] = [
  {
    id: 'daily-veil',
    name: 'Daily Veil',
    benefit: 'A weightless mineral veil that softens light on the skin.',
    size: '50 ml',
    price: '$68',
    priceValue: 68,
  },
  {
    id: 'night-restore',
    name: 'Night Restore',
    benefit: 'Overnight cream that replenishes while you rest.',
    size: '50 ml',
    price: '$78',
    priceValue: 78,
  },
  {
    id: 'golden-drop',
    name: 'Golden Drop',
    benefit: 'Amber serum with a slow, luminous finish.',
    size: '30 ml',
    price: '$92',
    priceValue: 92,
  },
]

export interface BagItem {
  product: Product
  quantity: number
}

interface AppState {
  scrollProgress: number
  cameraMode: CameraMode
  focusedProduct: ProductId | null
  bagOpen: boolean
  bag: BagItem[]
  sceneReady: boolean
  reducedMotion: boolean
  isMobile: boolean
}

type Action =
  | { type: 'SET_SCROLL'; progress: number }
  | { type: 'SET_CAMERA_MODE'; mode: CameraMode }
  | { type: 'FOCUS_PRODUCT'; id: ProductId | null }
  | { type: 'SET_BAG_OPEN'; open: boolean }
  | { type: 'ADD_TO_BAG'; id: ProductId }
  | { type: 'REMOVE_FROM_BAG'; id: ProductId }
  | { type: 'SET_SCENE_READY'; ready: boolean }
  | { type: 'SET_REDUCED_MOTION'; value: boolean }
  | { type: 'SET_IS_MOBILE'; value: boolean }

const initialState: AppState = {
  scrollProgress: 0,
  cameraMode: 'scroll',
  focusedProduct: null,
  bagOpen: false,
  bag: [],
  sceneReady: false,
  reducedMotion: false,
  isMobile: false,
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_SCROLL':
      return { ...state, scrollProgress: action.progress }
    case 'SET_CAMERA_MODE':
      return { ...state, cameraMode: action.mode }
    case 'FOCUS_PRODUCT':
      return {
        ...state,
        focusedProduct: action.id,
        cameraMode: action.id ? 'focus' : 'scroll',
      }
    case 'SET_BAG_OPEN':
      return { ...state, bagOpen: action.open }
    case 'ADD_TO_BAG': {
      const product = PRODUCTS.find((p) => p.id === action.id)
      if (!product) return state
      const existing = state.bag.find((item) => item.product.id === action.id)
      const bag = existing
        ? state.bag.map((item) =>
            item.product.id === action.id
              ? { ...item, quantity: item.quantity + 1 }
              : item,
          )
        : [...state.bag, { product, quantity: 1 }]
      return { ...state, bag, bagOpen: true }
    }
    case 'REMOVE_FROM_BAG':
      return {
        ...state,
        bag: state.bag.filter((item) => item.product.id !== action.id),
      }
    case 'SET_SCENE_READY':
      return { ...state, sceneReady: action.ready }
    case 'SET_REDUCED_MOTION':
      return { ...state, reducedMotion: action.value }
    case 'SET_IS_MOBILE':
      return { ...state, isMobile: action.value }
    default:
      return state
  }
}

interface StoreApi {
  state: AppState
  setScrollProgress: (progress: number) => void
  setCameraMode: (mode: CameraMode) => void
  focusProduct: (id: ProductId | null) => void
  setBagOpen: (open: boolean) => void
  addToBag: (id: ProductId) => void
  removeFromBag: (id: ProductId) => void
  setSceneReady: (ready: boolean) => void
  setReducedMotion: (value: boolean) => void
  setIsMobile: (value: boolean) => void
  bagCount: number
}

const StoreContext = createContext<StoreApi | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)

  const setScrollProgress = useCallback((progress: number) => {
    dispatch({ type: 'SET_SCROLL', progress })
  }, [])

  const setCameraMode = useCallback((mode: CameraMode) => {
    dispatch({ type: 'SET_CAMERA_MODE', mode })
  }, [])

  const focusProduct = useCallback((id: ProductId | null) => {
    dispatch({ type: 'FOCUS_PRODUCT', id })
  }, [])

  const setBagOpen = useCallback((open: boolean) => {
    dispatch({ type: 'SET_BAG_OPEN', open })
  }, [])

  const addToBag = useCallback((id: ProductId) => {
    dispatch({ type: 'ADD_TO_BAG', id })
  }, [])

  const removeFromBag = useCallback((id: ProductId) => {
    dispatch({ type: 'REMOVE_FROM_BAG', id })
  }, [])

  const setSceneReady = useCallback((ready: boolean) => {
    dispatch({ type: 'SET_SCENE_READY', ready })
  }, [])

  const setReducedMotion = useCallback((value: boolean) => {
    dispatch({ type: 'SET_REDUCED_MOTION', value })
  }, [])

  const setIsMobile = useCallback((value: boolean) => {
    dispatch({ type: 'SET_IS_MOBILE', value })
  }, [])

  const bagCount = useMemo(
    () => state.bag.reduce((sum, item) => sum + item.quantity, 0),
    [state.bag],
  )

  const value = useMemo(
    () => ({
      state,
      setScrollProgress,
      setCameraMode,
      focusProduct,
      setBagOpen,
      addToBag,
      removeFromBag,
      setSceneReady,
      setReducedMotion,
      setIsMobile,
      bagCount,
    }),
    [
      state,
      setScrollProgress,
      setCameraMode,
      focusProduct,
      setBagOpen,
      addToBag,
      removeFromBag,
      setSceneReady,
      setReducedMotion,
      setIsMobile,
      bagCount,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  const ctx = useContext(StoreContext)
  if (!ctx) throw new Error('useStore must be used within StoreProvider')
  return ctx
}
