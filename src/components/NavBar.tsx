import { Link, useLocation } from "react-router-dom";
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
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <div className="sticky top-0 z-50 px-3 pt-3 sm:px-6 lg:px-8">
      <nav className="landing-nav-shell mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-full px-3 py-2 sm:px-4">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-saffron to-indiagreen text-lg font-black text-ink-950">
            वा
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-semibold tracking-wide text-white">
              VAANI-RAKSHAK
            </span>
            <span className="block text-[10px] uppercase tracking-[0.2em] text-white/45">
              Guardian of Voice
            </span>
          </span>
        </Link>

        <button
          className="liquid-glass inline-flex h-9 w-9 items-center justify-center rounded-full text-white md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          <span className="text-lg leading-none">{open ? "✕" : "☰"}</span>
        </button>

        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <li key={l.href}>
                <Link
                  to={l.href}
                  className={`rounded-full px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-white/15 text-white"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
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
        <div className="mx-auto mt-2 max-w-7xl md:hidden">
          <ul className="landing-nav-shell flex flex-col gap-1 rounded-[1.75rem] px-3 py-3">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  to={l.href}
                  onClick={() => setOpen(false)}
                  className={`block rounded-2xl px-4 py-3 text-sm font-medium ${
                    pathname === l.href
                      ? "bg-white/15 text-white"
                      : "text-white/75 hover:bg-white/10"
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
