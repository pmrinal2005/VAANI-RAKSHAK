/**
 * videoCache.ts
 * ─────────────────────────────────────────────────────────────────────────
 * Aggressive, parallel video pre-warmer for the cinematic landing page.
 *
 * TASK 1 (instant video load):
 *   - index.html now starts a boot-time fetch loop for every clip BEFORE
 *     React mounts.  Each completed download is exposed via the global
 *     `window.__vaaniVideoBlobs` map as { src → blob URL }.
 *   - This module checks that map first and adopts the pre-baked blob URL
 *     synchronously, so the very first paint of every <video> already
 *     points at a same-origin blob URL — zero further network requests,
 *     zero black frames, even when the user scrolls fast.
 *   - If the boot warm hasn't completed yet for a particular src, we
 *     fall back to the original fetch-and-blob pipeline (which is still
 *     dramatically faster than letting the browser load the <video> on
 *     mount).
 */

declare global {
  interface Window {
    __vaaniVideoBlobs?: Record<string, string>
  }
}

type CacheEntry = {
  /** The original src the caller asked for. */
  originalSrc: string
  /** A blob URL once ready, otherwise the original src. */
  resolvedSrc: string
  /** Resolves when the blob URL is available (or when fallback is decided). */
  ready: Promise<string>
  /** True when the blob URL has been materialised. */
  isBlob: boolean
}

const cache = new Map<string, CacheEntry>()

function isLikelyCrossOrigin(src: string): boolean {
  if (typeof window === 'undefined') return true
  if (src.startsWith('/') || src.startsWith('./')) return false
  try {
    const u = new URL(src, window.location.href)
    return u.origin !== window.location.origin
  } catch {
    return false
  }
}

/**
 * Look up an already-materialised blob URL produced by the boot script
 * in index.html.  Returns undefined when not yet ready.
 */
function readBootBlob(src: string): string | undefined {
  if (typeof window === 'undefined') return undefined
  const map = window.__vaaniVideoBlobs
  if (map && typeof map[src] === 'string') return map[src]
  return undefined
}

/**
 * Begin warming a single video. Idempotent: repeated calls for the same src
 * return the same Promise.
 */
export function warmVideo(src: string, priority: 'high' | 'auto' = 'auto'): Promise<string> {
  const existing = cache.get(src)
  if (existing) return existing.ready

  // ── Fast path: the boot script in index.html already produced a blob URL
  //    for this exact src.  Adopt it synchronously so the first paint uses
  //    a same-origin blob with zero latency.
  const bootBlob = readBootBlob(src)

  const fallbackEntry: CacheEntry = {
    originalSrc: src,
    resolvedSrc: bootBlob ?? src,
    isBlob: Boolean(bootBlob),
    ready: bootBlob ? Promise.resolve(bootBlob) : Promise.resolve(src),
  }

  if (bootBlob) {
    cache.set(src, fallbackEntry)
    return fallbackEntry.ready
  }

  const readyPromise = (async () => {
    // Give the boot fetch a brief chance to finish — often it does between
    // mount and effect-run.
    const lateBoot = readBootBlob(src)
    if (lateBoot) {
      const entry = cache.get(src)
      if (entry) {
        entry.resolvedSrc = lateBoot
        entry.isBlob = true
      }
      return lateBoot
    }

    try {
      const init: RequestInit & { priority?: 'high' | 'auto' | 'low' } = {
        method: 'GET',
        credentials: 'omit',
        cache: 'force-cache',
        priority,
      }
      if (isLikelyCrossOrigin(src)) {
        init.mode = 'cors'
      }

      const response = await fetch(src, init)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)

      const entry = cache.get(src)
      if (entry) {
        entry.resolvedSrc = blobUrl
        entry.isBlob = true
      }
      return blobUrl
    } catch {
      return src
    }
  })()

  fallbackEntry.ready = readyPromise
  cache.set(src, fallbackEntry)
  return readyPromise
}

/**
 * Kick off parallel warming for a list of clips.  The first entry is treated
 * as the above-the-fold hero and gets `fetchpriority: high`; the rest get
 * `auto`.  Returns the hero's ready-promise so callers can gate their loader
 * exclusively on the hero (other clips can finish later, in the background).
 */
export function warmAll(sources: string[]): Promise<string> {
  if (sources.length === 0) return Promise.resolve('')
  const [hero, ...rest] = sources
  const heroReady = warmVideo(hero, 'high')
  rest.forEach((src) => {
    warmVideo(src, 'high')
  })
  return heroReady
}

/**
 * Synchronously read the current resolved src for a given input (blob URL if
 * ready, otherwise the original src).  Now ALSO honours the boot-time blob
 * map so the very first render of a freshly mounted <video> can already
 * point at a same-origin blob URL.
 */
export function peekResolvedSrc(src: string): string {
  const entry = cache.get(src)
  if (entry?.isBlob) return entry.resolvedSrc
  const bootBlob = readBootBlob(src)
  return bootBlob ?? entry?.resolvedSrc ?? src
}

/**
 * Subscribe to the ready event for a particular src.  Resolves to the final
 * resolvedSrc (blob or fallback).
 */
export function whenReady(src: string): Promise<string> {
  const entry = cache.get(src)
  if (entry) return entry.ready
  return warmVideo(src, 'auto')
}

/**
 * Release all blob URLs.  Called by the landing page on unmount as a courtesy
 * — modern browsers handle the GC automatically, but it keeps DevTools clean.
 */
export function dropAll(): void {
  cache.forEach((entry) => {
    if (entry.isBlob) {
      try {
        URL.revokeObjectURL(entry.resolvedSrc)
      } catch {
        // ignore
      }
    }
  })
  cache.clear()
}
