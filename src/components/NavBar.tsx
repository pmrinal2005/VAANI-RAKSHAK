"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/detect", label: "Live Detector" },
  { href: "/architecture", label: "Architecture" },
  { href: "/ledger", label: "Audit Ledger" },
  { href: "/research", label: "Research & Gaps" },
  { href: "/colab", label: "Colab / Models" },
];

export function NavBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink-950/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-saffron to-indiagreen text-lg font-black text-ink-950">
            वा
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-bold tracking-wide text-white">
              VAANI-RAKSHAK
            </span>
            <span className="block text-[10px] uppercase tracking-[0.2em] text-white/40">
              Guardian of Voice
            </span>
          </span>
        </Link>

        <button
          className="btn-ghost !px-2.5 !py-1.5 md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <span className="text-lg">☰</span>
        </button>

        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-white/10 text-white"
                      : "text-white/60 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {open && (
        <ul className="flex flex-col gap-1 border-t border-white/10 px-4 py-3 md:hidden">
          {LINKS.map((l) => (
            <li key={l.href}>
              <Link
                href={l.href}
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  pathname === l.href ? "bg-white/10 text-white" : "text-white/70"
                }`}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}
