/**
 * Aggressive, parallel video pre-warmer for the cinematic landing page.
 */

declare global {
  interface Window {
    __vaaniVideoBlobs?: Record<string, string>;
  }
}

type CacheEntry = {
  originalSrc: string;
  resolvedSrc: string;
  ready: Promise<string>;
  isBlob: boolean;
};

const cache = new Map<string, CacheEntry>();

function isLikelyCrossOrigin(src: string): boolean {
  if (typeof window === "undefined") return true;
  if (src.startsWith("/") || src.startsWith("./")) return false;
  try {
    const u = new URL(src, window.location.href);
    return u.origin !== window.location.origin;
  } catch {
    return false;
  }
}

function readBootBlob(src: string): string | undefined {
  if (typeof window === "undefined") return undefined;
  const map = window.__vaaniVideoBlobs;
  if (map && typeof map[src] === "string") return map[src];
  return undefined;
}

export function warmVideo(src: string, priority: "high" | "auto" = "auto"): Promise<string> {
  const existing = cache.get(src);
  if (existing) return existing.ready;

  const bootBlob = readBootBlob(src);
  const fallbackEntry: CacheEntry = {
    originalSrc: src,
    resolvedSrc: bootBlob ?? src,
    isBlob: Boolean(bootBlob),
    ready: bootBlob ? Promise.resolve(bootBlob) : Promise.resolve(src),
  };
  if (bootBlob) {
    cache.set(src, fallbackEntry);
    return fallbackEntry.ready;
  }

  const readyPromise = (async () => {
    const lateBoot = readBootBlob(src);
    if (lateBoot) {
      const entry = cache.get(src);
      if (entry) {
        entry.resolvedSrc = lateBoot;
        entry.isBlob = true;
      }
      return lateBoot;
    }
    try {
      const init: RequestInit & { priority?: "high" | "auto" | "low" } = {
        method: "GET",
        credentials: "omit",
        cache: "force-cache",
        priority,
      };
      if (isLikelyCrossOrigin(src)) {
        init.mode = "cors";
      }
      const response = await fetch(src, init);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const entry = cache.get(src);
      if (entry) {
        entry.resolvedSrc = blobUrl;
        entry.isBlob = true;
      }
      return blobUrl;
    } catch {
      return src;
    }
  })();

  fallbackEntry.ready = readyPromise;
  cache.set(src, fallbackEntry);
  return readyPromise;
}

export function warmAll(sources: string[]): Promise<string> {
  if (sources.length === 0) return Promise.resolve("");
  const [hero, ...rest] = sources;
  const heroReady = warmVideo(hero, "high");
  rest.forEach((src) => {
    warmVideo(src, "high");
  });
  return heroReady;
}

export function peekResolvedSrc(src: string): string {
  const entry = cache.get(src);
  if (entry?.isBlob) return entry.resolvedSrc;
  const bootBlob = readBootBlob(src);
  return bootBlob ?? entry?.resolvedSrc ?? src;
}

export function whenReady(src: string): Promise<string> {
  const entry = cache.get(src);
  if (entry) return entry.ready;
  return warmVideo(src, "auto");
}

export function dropAll(): void {
  cache.forEach((entry) => {
    if (entry.isBlob) {
      try {
        URL.revokeObjectURL(entry.resolvedSrc);
      } catch {
        // ignore
      }
    }
  });
  cache.clear();
}
