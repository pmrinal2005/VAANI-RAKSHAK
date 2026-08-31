"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { NavBar } from "@/components/NavBar";

export function SiteChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/";

  if (isLanding) {
    return <>{children}</>;
  }

  return (
    <div className="dash-shell">
      <NavBar />
      <main className="mx-auto w-full max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">{children}</main>
      <footer className="border-t border-white/10 py-8 text-center text-xs text-white/40">
        <p>
          VAANI-RAKSHAK · वाणी-रक्षक — Guardian of Voice · 100% free/open-source stack · Edge-first
          · DPDP-aligned
        </p>
        <p className="mt-1">
          Research &amp; engineering prototype. Detection runs fully client-side (privacy by
          architecture).
        </p>
      </footer>
    </div>
  );
}
