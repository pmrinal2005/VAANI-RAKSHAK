"use client";

import { usePathname } from "next/navigation";
import { NavBar } from "@/components/NavBar";

/**
 * SiteChrome
 * ──────────────────────────────────────────────────────────────────────────
 * Wraps every page with the shared VAANI-RAKSHAK navigation + footer, EXCEPT
 * the landing page ("/"). The landing page is a full-bleed cinematic surface
 * (Akashara design system) that ships its own floating glass navbar, so the
 * standard sticky NavBar + <main> padding + footer would fight its layout.
 *
 * The dashboard and all other routes keep the exact chrome + spacing they had
 * before, so their functionality is completely untouched.
 */
export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/";

  if (isLanding) {
    return <>{children}</>;
  }

  return (
    <>
      <NavBar />
      <main className="mx-auto w-full max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
        {children}
      </main>
      <footer className="border-t border-white/10 py-8 text-center text-xs text-white/40">
        <p>
          VAANI-RAKSHAK · वाणी-रक्षक — Guardian of Voice · 100% free/open-source stack ·
          Edge-first · DPDP-aligned
        </p>
        <p className="mt-1">
          Research &amp; engineering prototype. Deployed on Vercel. Detection runs fully
          client-side (privacy by architecture).
        </p>
      </footer>
    </>
  );
}
