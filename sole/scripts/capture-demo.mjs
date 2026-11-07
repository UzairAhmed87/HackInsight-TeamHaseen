import { chromium } from 'playwright'
import { mkdir, copyFile, stat } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'

const MEDIA = '/cursor/stores/self/media'
const ARTIFACTS = '/opt/cursor/artifacts'
const BASE = 'http://127.0.0.1:5173/'

await mkdir(MEDIA, { recursive: true })
await mkdir(ARTIFACTS, { recursive: true })

const browser = await chromium.launch({
  headless: true,
  args: [
    '--use-gl=swiftshader',
    '--enable-webgl',
    '--ignore-gpu-blocklist',
    '--disable-dev-shm-usage',
  ],
})

async function cdpShot(page, name) {
  const session = await page.context().newCDPSession(page)
  const { data } = await session.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
  })
  const buf = Buffer.from(data, 'base64')
  const mediaPath = `${MEDIA}/${name}`
  const artPath = `${ARTIFACTS}/${name}`
  await import('node:fs/promises').then((fs) => fs.writeFile(mediaPath, buf))
  await copyFile(mediaPath, artPath)
  const s = await stat(mediaPath)
  console.log('wrote', mediaPath, s.size)
  if (s.size < 20000) throw new Error(`screenshot too small: ${name}`)
}

async function waitForScene(page) {
  await page.waitForSelector('canvas', { timeout: 20000 })
  await page.waitForTimeout(3500)
}

async function goCollection(page) {
  await page.evaluate(() => {
    const hold = document.getElementById('collection-anchor')
    if (hold) {
      hold.scrollIntoView({ behavior: 'instant', block: 'start' })
      return
    }
    const journey = document.getElementById('journey')
    if (!journey) return
    window.scrollTo(0, journey.offsetTop + journey.offsetHeight * 0.88)
  })
  await page.waitForTimeout(2500)
}

{
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  })
  const page = await context.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
  await waitForScene(page)
  await cdpShot(page, 'sole-hero-desktop.png')

  await goCollection(page)
  await cdpShot(page, 'sole-collection-desktop.png')

  // Prefer DOM labels for selection
  const night = page.locator('button.hotspot-night-restore')
  if (await night.count()) {
    await night.click({ force: true })
    await page.waitForTimeout(1600)
  }

  const add = page.getByRole('button', { name: /Add to bag/i })
  if (await add.count()) {
    await add.click()
    await page.waitForTimeout(1000)
  }

  await context.close()
}

{
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  })
  const page = await context.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
  await waitForScene(page)
  await goCollection(page)

  const drop = page.locator('button.hotspot-golden-drop')
  if (await drop.count()) {
    await drop.click({ force: true })
    await page.waitForTimeout(1600)
  } else {
    // Force focus via store if labels not visible — click Collection then try again
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find((b) =>
        /golden drop/i.test(b.textContent || ''),
      )
      btn?.click()
    })
    await page.waitForTimeout(1600)
  }
  await cdpShot(page, 'sole-product-panel-mobile.png')
  await context.close()
}

{
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: `${ARTIFACTS}/video-tmp`, size: { width: 1280, height: 720 } },
  })
  const page = await context.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
  await waitForScene(page)
  await page.waitForTimeout(600)

  await page.evaluate(async () => {
    const journey = document.getElementById('journey')
    if (!journey) return
    const end = journey.offsetTop + journey.offsetHeight - window.innerHeight * 0.15
    for (const t of [0.2, 0.4, 0.6, 0.8, 0.95]) {
      window.scrollTo(0, journey.offsetTop + (end - journey.offsetTop) * t)
      await new Promise((r) => setTimeout(r, 600))
    }
  })
  await page.waitForTimeout(700)

  const daily = page.locator('button.hotspot-daily-veil')
  if (await daily.count()) await daily.click({ force: true })
  await page.waitForTimeout(1400)

  const add = page.getByRole('button', { name: /Add to bag/i })
  if (await add.count()) await add.click()
  await page.waitForTimeout(1100)

  await page.locator('.bag-drawer .ghost').filter({ hasText: 'Close' }).click({ force: true })
  await page.waitForTimeout(600)
  await page.locator('.bag-backdrop').click({ force: true }).catch(() => {})
  await page.waitForTimeout(400)

  const back = page.getByRole('button', { name: /Back to collection/i })
  if (await back.count()) await back.click({ force: true })
  await page.waitForTimeout(1100)

  const video = page.video()
  await context.close()
  const rawPath = await video.path()
  const outMp4 = `${MEDIA}/sole-walkthrough.mp4`
  try {
    execFileSync(
      'ffmpeg',
      ['-y', '-i', rawPath, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outMp4],
      { stdio: 'inherit' },
    )
    await copyFile(outMp4, `${ARTIFACTS}/sole-walkthrough.mp4`)
    console.log('wrote', outMp4)
  } catch {
    const webm = `${MEDIA}/sole-walkthrough.webm`
    await copyFile(rawPath, webm)
    await copyFile(rawPath, `${ARTIFACTS}/sole-walkthrough.webm`)
    console.log('wrote', webm)
  }
}

await browser.close()

const required = [
  'sole-hero-desktop.png',
  'sole-collection-desktop.png',
  'sole-product-panel-mobile.png',
]
for (const f of required) {
  const p = `${MEDIA}/${f}`
  if (!existsSync(p) || (await stat(p)).size < 20000) {
    console.error('MISSING/SMALL', p)
    process.exitCode = 1
  } else console.log('verified', p, (await stat(p)).size)
}
const vid = existsSync(`${MEDIA}/sole-walkthrough.mp4`)
  ? `${MEDIA}/sole-walkthrough.mp4`
  : `${MEDIA}/sole-walkthrough.webm`
if (!existsSync(vid)) {
  console.error('MISSING video')
  process.exitCode = 1
} else console.log('verified', vid, (await stat(vid)).size)
