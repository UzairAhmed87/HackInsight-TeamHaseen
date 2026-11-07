import * as THREE from 'three'

let creamTexture: THREE.CanvasTexture | null = null
let sandTexture: THREE.CanvasTexture | null = null
let travertineTexture: THREE.CanvasTexture | null = null
let skinMacroTexture: THREE.CanvasTexture | null = null

function noise(x: number, y: number, seed = 0) {
  const n = Math.sin(x * 12.9898 + y * 78.233 + seed) * 43758.5453
  return n - Math.floor(n)
}

function fbm(x: number, y: number, octaves = 4, seed = 0) {
  let value = 0
  let amp = 0.5
  let freq = 1
  for (let i = 0; i < octaves; i++) {
    value += amp * noise(x * freq, y * freq, seed + i * 17)
    amp *= 0.5
    freq *= 2
  }
  return value
}

export function getCreamTexture() {
  if (creamTexture) return creamTexture
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(size, size)

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = x / size
      const v = y / size
      const swirl = fbm(u * 4 + Math.sin(v * 6) * 0.3, v * 4, 5, 2)
      const ridge = fbm(u * 8, v * 8, 3, 9)
      const tone = 0.86 + swirl * 0.1 + ridge * 0.04
      const r = Math.floor(244 * tone)
      const g = Math.floor(232 * tone)
      const b = Math.floor(214 * tone)
      const i = (y * size + x) * 4
      img.data[i] = r
      img.data[i + 1] = g
      img.data[i + 2] = b
      img.data[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)

  // Soft peaks of cream
  for (let i = 0; i < 18; i++) {
    const cx = 80 + Math.random() * 350
    const cy = 80 + Math.random() * 350
    const grd = ctx.createRadialGradient(cx, cy, 2, cx, cy, 40 + Math.random() * 35)
    grd.addColorStop(0, 'rgba(255,250,244,0.55)')
    grd.addColorStop(1, 'rgba(255,250,244,0)')
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.arc(cx, cy, 60, 0, Math.PI * 2)
    ctx.fill()
  }

  creamTexture = new THREE.CanvasTexture(canvas)
  creamTexture.wrapS = creamTexture.wrapT = THREE.RepeatWrapping
  creamTexture.colorSpace = THREE.SRGBColorSpace
  creamTexture.anisotropy = 8
  return creamTexture
}

export function getSandTexture() {
  if (sandTexture) return sandTexture
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(size, size)

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const n = fbm(x / 40, y / 40, 5, 4)
      const grain = noise(x * 0.7, y * 0.7, 1)
      const tone = 0.72 + n * 0.18 + grain * 0.05
      const i = (y * size + x) * 4
      img.data[i] = Math.floor(214 * tone)
      img.data[i + 1] = Math.floor(185 * tone)
      img.data[i + 2] = Math.floor(156 * tone)
      img.data[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  sandTexture = new THREE.CanvasTexture(canvas)
  sandTexture.wrapS = sandTexture.wrapT = THREE.RepeatWrapping
  sandTexture.repeat.set(4, 4)
  sandTexture.colorSpace = THREE.SRGBColorSpace
  return sandTexture
}

export function getTravertineTexture() {
  if (travertineTexture) return travertineTexture
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(size, size)

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const bands = Math.sin(y * 0.04 + fbm(x / 60, y / 20, 3, 6) * 4) * 0.5 + 0.5
      const pits = fbm(x / 18, y / 18, 4, 11)
      const tone = 0.78 + bands * 0.12 - pits * 0.08
      const i = (y * size + x) * 4
      img.data[i] = Math.floor(232 * tone)
      img.data[i + 1] = Math.floor(220 * tone)
      img.data[i + 2] = Math.floor(204 * tone)
      img.data[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  travertineTexture = new THREE.CanvasTexture(canvas)
  travertineTexture.wrapS = travertineTexture.wrapT = THREE.RepeatWrapping
  travertineTexture.colorSpace = THREE.SRGBColorSpace
  return travertineTexture
}

/** Soft skin-tone macro substitute for cream application sequence */
export function getSkinMacroTexture() {
  if (skinMacroTexture) return skinMacroTexture
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(size, size)

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const soft = fbm(x / 70, y / 70, 4, 20)
      const pores = fbm(x / 12, y / 12, 2, 21) * 0.04
      const tone = 0.82 + soft * 0.12 - pores
      const i = (y * size + x) * 4
      img.data[i] = Math.floor(210 * tone)
      img.data[i + 1] = Math.floor(168 * tone * 0.98)
      img.data[i + 2] = Math.floor(148 * tone * 0.95)
      img.data[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)

  // Cream smear highlight
  const grd = ctx.createRadialGradient(260, 240, 10, 260, 250, 160)
  grd.addColorStop(0, 'rgba(255,248,240,0.7)')
  grd.addColorStop(0.45, 'rgba(244,230,210,0.35)')
  grd.addColorStop(1, 'rgba(244,230,210,0)')
  ctx.fillStyle = grd
  ctx.beginPath()
  ctx.ellipse(270, 250, 170, 110, -0.4, 0, Math.PI * 2)
  ctx.fill()

  skinMacroTexture = new THREE.CanvasTexture(canvas)
  skinMacroTexture.colorSpace = THREE.SRGBColorSpace
  return skinMacroTexture
}
