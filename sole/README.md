# SOLÈ — Immersive Skincare Landing

Cinematic product experience for a design hackathon: warm mineral landscape, amber-glass packaging, scroll-driven camera journey, and interactive collection hotspots.

Built with **Vite + React + TypeScript**, **Three.js / React Three Fiber**, and **GSAP ScrollTrigger**.

## Run locally

```bash
cd sole
npm install
npm run dev
```

Then open the printed local URL (typically `http://localhost:5173`).

```bash
npm run build    # production build
npm run preview  # preview the build
```

## Experience map

1. **Hero** — Night Restore jar on a travertine plinth; brand overlay + Explore CTA
2. **Cinematic journey** — scroll progresses camera (top-down → lid lift → cream macro → skin-texture bridge → collection)
3. **Collection** — Daily Veil, Night Restore, Golden Drop with hotspots
4. **Product panel** — benefit, size, demo price, Add to bag, Back to collection
5. **Bag drawer** — working count + line items
6. **Philosophy + footer** — short brand close

## Controls

- **Skip to collection** during the journey
- **Bag** in the top nav
- **prefers-reduced-motion** — static collection framing, fades, full product UI still usable

## Asset approach

Products and scenery are real-time 3D meshes with physical materials (amber glass transmission, champagne metal, procedural cream/sand/travertine canvases). No emoji or CSS-shape stand-ins.

The mid-sequence “cream on skin” beat uses a rendered cream-texture / soft skin-macro bridge (procedural canvases) rather than licensed live-action footage — same push-in / pull-back structure as the brief.

## Camera ownership

A single `CameraController` owns camera state. Scroll drives the path while mode is `scroll`; hotspot selection switches to `focus` and tweens (~1.1s) without fighting ScrollTrigger. “Back to collection” restores scroll ownership.
