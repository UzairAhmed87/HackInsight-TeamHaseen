import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useStore } from '../state/store'

gsap.registerPlugin(ScrollTrigger)

export function useAppSetup() {
  const {
    setScrollProgress,
    setReducedMotion,
    setIsMobile,
    state: { cameraMode, reducedMotion },
  } = useStore()

  const cameraModeRef = useRef(cameraMode)
  cameraModeRef.current = cameraMode

  useEffect(() => {
    const mqMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const mqMobile = window.matchMedia('(max-width: 768px)')

    const sync = () => {
      setReducedMotion(mqMotion.matches)
      setIsMobile(mqMobile.matches)
    }
    sync()

    mqMotion.addEventListener('change', sync)
    mqMobile.addEventListener('change', sync)
    return () => {
      mqMotion.removeEventListener('change', sync)
      mqMobile.removeEventListener('change', sync)
    }
  }, [setReducedMotion, setIsMobile])

  useEffect(() => {
    const journey = document.getElementById('journey')
    if (!journey) return

    if (reducedMotion) {
      setScrollProgress(1)
      return
    }

    const trigger = ScrollTrigger.create({
      trigger: journey,
      start: 'top top',
      end: 'bottom bottom',
      scrub: true,
      onUpdate: (self) => {
        if (cameraModeRef.current === 'focus') return
        setScrollProgress(self.progress)
      },
      onLeave: () => {
        if (cameraModeRef.current === 'focus') return
        setScrollProgress(1)
      },
    })

    return () => {
      trigger.kill()
    }
  }, [setScrollProgress, reducedMotion])
}
