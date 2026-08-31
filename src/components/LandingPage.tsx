"use client";

/* ─────────────────────────────────────────────────────────────────────────
   VAANI-RAKSHAK — Cinematic Landing Page
   ─────────────────────────────────────────────────────────────────────────
   The first two sections (HERO + CAPABILITIES) are a faithful clone of the
   Akashara landing page's first two sections — same liquid-glass design
   language, blur-in text, floating glass navbar, mirrored video capability
   grid and orbital loader — but every word of content is re-written for
   VAANI-RAKSHAK (real-time voice-cloning detection for India).
   ────────────────────────────────────────────────────────────────────── */

import { motion, useInView } from "framer-motion";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  peekResolvedSrc,
  warmAll,
  warmVideo,
  whenReady,
} from "@/lib/videoCache";

/* ── ASSET MAP ─────────────────────────────────────────────────────────── */
const HERO_VIDEO = "/landing_page.mp4";
const CAP_VIDEO = "/section3.mp4";
const FADE_IN_MS = 320;

const SECTION_IDS = {
  hero: "home",
  capabilities: "capabilities",
} as const;

/* ── LIVE ATTACK STATS (hooking, VAANI-aligned) ────────────────────────── */
const HERO_METRICS = [
  {
    value: "<5 ms",
    label: "Tier-0 DSP verdict on every call chunk — CPU-only",
    icon: "pulse",
  },
  {
    value: "22",
    label: "Indian languages guarded by one IndicWav2Vec backbone",
    icon: "globe",
  },
  {
    value: "$0",
    label: "Cost to run — 100% free / open-source, edge-first stack",
    icon: "coin",
  },
] as const;

/* ── CAPABILITY CARDS (the 3-tier cascade — VAANI's core) ───────────────── */
type CapabilityCard = {
  title: string;
  body: string;
  tags: string[];
  iconPath: string;
};

const capabilities: CapabilityCard[] = [
  {
    title: "Micro-DSP Pre-Filter",
    body: "CQCC/LFCC, spectral flatness, phase and HF-cutoff heuristics fire on every chunk in under 5 ms — discarding obvious clean or flagged audio so heavy compute stays near-zero in the median case.",
    tags: ["<5 ms", "CPU-only", "Every chunk", "Tier 0"],
    // waveform / signal icon
    iconPath:
      "M3 12h4l2.5-4.5L13 16l2.5-4H21",
  },
  {
    title: "Compact Neural CM",
    body: "A distilled AASIST-L graph-attention countermeasure fused with a compact multilingual SSL front-end — near-SOTA spectro-temporal artefact detection running fully on-device via ONNX / TFLite.",
    tags: ["~10 ms", "INT8 quantised", "On-device", "Tier 1"],
    // chip / neural icon
    iconPath:
      "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 7h10v10H7z",
  },
  {
    title: "Deep Multilingual SSL",
    body: "Full IndicWav2Vec / XLS-R + AASIST3 with per-language LoRA adapters — invoked only when cheaper tiers disagree or the call is high-stakes, then anchored to a tamper-evident consortium ledger.",
    tags: ["~60 ms", "Flagged only", "22 languages", "Tier 2"],
    // shield icon
    iconPath:
      "M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z",
  },
];

/* ─────────────────────────────────────────────────────────────────────────
   FADING VIDEO
   ────────────────────────────────────────────────────────────────────── */
type FadingVideoProps = {
  src: string;
  className?: string;
  style?: React.CSSProperties;
  onReady?: () => void;
  isHero?: boolean;
  mirror?: boolean;
};

function useFadingVideo({ src, onReady, isHero }: FadingVideoProps) {
  const ref = useRef<HTMLVideoElement>(null);
  const [resolvedSrc, setResolvedSrc] = useState<string>(() =>
    peekResolvedSrc(src)
  );

  useEffect(() => {
    let active = true;
    warmVideo(src, "high");
    whenReady(src).then((finalSrc) => {
      if (active && finalSrc !== resolvedSrc) setResolvedSrc(finalSrc);
    });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, isHero]);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;

    let fadeRaf = 0;
    let readyEmitted = false;

    const fadeTo = (target: number, duration: number) => {
      cancelAnimationFrame(fadeRaf);
      const startOpacity = Number.parseFloat(video.style.opacity || "0") || 0;
      const startedAt = performance.now();
      const step = (time: number) => {
        const progress = Math.min(1, (time - startedAt) / duration);
        const nextOpacity = startOpacity + (target - startOpacity) * progress;
        video.style.opacity = String(nextOpacity);
        if (progress < 1) fadeRaf = requestAnimationFrame(step);
      };
      fadeRaf = requestAnimationFrame(step);
    };

    const handleReady = () => {
      if (!readyEmitted) {
        video.style.opacity = "0";
        fadeTo(1, FADE_IN_MS);
        readyEmitted = true;
        onReady?.();
      } else {
        video.style.opacity = "1";
      }
      video.play().catch(() => {});
    };

    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.preload = "auto";
    video.style.opacity = "0";

    video.addEventListener("loadeddata", handleReady);
    video.addEventListener("canplay", handleReady);
    video.load();

    return () => {
      cancelAnimationFrame(fadeRaf);
      video.removeEventListener("loadeddata", handleReady);
      video.removeEventListener("canplay", handleReady);
    };
  }, [onReady, resolvedSrc]);

  return { ref, resolvedSrc };
}

function FadingVideo({
  src,
  className,
  style,
  onReady,
  isHero,
  mirror,
}: FadingVideoProps) {
  const { ref, resolvedSrc } = useFadingVideo({ src, onReady, isHero });
  const mergedStyle: React.CSSProperties | undefined = mirror
    ? { ...(style ?? {}), transform: `${style?.transform ?? ""} scaleX(-1)`.trim() }
    : style;
  return (
    <video
      ref={ref}
      src={resolvedSrc}
      autoPlay
      muted
      loop
      playsInline
      preload="auto"
      className={className}
      style={mergedStyle}
    />
  );
}

/* ── ICONS ─────────────────────────────────────────────────────────────── */
function ArrowUpRight({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 17L17 7" />
      <path d="M7 7h10v10" />
    </svg>
  );
}
function PlayIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <polygon points="6 4 20 12 6 20 6 4" />
    </svg>
  );
}
function MenuIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}
function CloseIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

/* ── BRAND LOGO (Akashara-style circle) ────────────────────────────────── */
function BrandLogo({ size = 40 }: { size?: number }) {
  return (
    <div
      className="relative inline-flex items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-saffron to-indiagreen"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <span className="font-black text-ink-950" style={{ fontSize: size * 0.4 }}>
        वा
      </span>
    </div>
  );
}

/* ── BLUR-IN TEXT ──────────────────────────────────────────────────────── */
function BlurText({
  text,
  className,
  delayOffset = 0,
}: {
  text: string;
  className?: string;
  delayOffset?: number;
}) {
  const ref = useRef<HTMLParagraphElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.1 });
  const words = useMemo(() => text.split(" "), [text]);

  return (
    <p
      ref={ref}
      className={className}
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        rowGap: "0.1em",
      }}
    >
      {words.map((word, index) => (
        <motion.span
          key={`${word}-${index}`}
          initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
          animate={
            inView
              ? {
                  filter: ["blur(10px)", "blur(5px)", "blur(0px)"],
                  opacity: [0, 0.5, 1],
                  y: [50, -5, 0],
                }
              : { filter: "blur(10px)", opacity: 0, y: 50 }
          }
          transition={{
            duration: 0.7,
            times: [0, 0.5, 1],
            ease: "easeOut",
            delay: delayOffset + index * 0.1,
          }}
          style={{ display: "inline-block", marginRight: "0.28em" }}
        >
          {word}
        </motion.span>
      ))}
    </p>
  );
}

/* ── SECTION REVEAL ────────────────────────────────────────────────────── */
function SectionReveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
      whileInView={{ filter: "blur(0px)", opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{ duration: 0.7, ease: "easeOut", delay }}
    >
      {children}
    </motion.div>
  );
}

/* ── ORBITAL LOADER ────────────────────────────────────────────────────── */
function OrbitalLoader({ visible }: { visible: boolean }) {
  return (
    <motion.div
      initial={false}
      animate={{ opacity: visible ? 1 : 0, pointerEvents: visible ? "auto" : "none" }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="landing-loader"
      aria-hidden={!visible}
    >
      <div className="landing-loader__core">
        <div className="landing-loader__rings">
          <span className="landing-loader__ring landing-loader__ring--outer" />
          <span className="landing-loader__ring landing-loader__ring--middle" />
          <span className="landing-loader__ring landing-loader__ring--inner" />
          <span className="landing-loader__planet" />
        </div>
        <div className="landing-loader__copy">
          <div className="landing-loader__eyebrow">Arming the voice guardian</div>
          <div className="landing-loader__title">Warming the detection cascade</div>
          <div className="landing-loader__bar">
            <span className="landing-loader__barFill" />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── SECTION FRAME ─────────────────────────────────────────────────────── */
function SectionFrame({
  id,
  video,
  className = "",
  children,
  heroScale = false,
  onReady,
  isHero = false,
  mirror = false,
}: {
  id?: string;
  video: string;
  className?: string;
  children: React.ReactNode;
  heroScale?: boolean;
  onReady?: () => void;
  isHero?: boolean;
  mirror?: boolean;
}) {
  return (
    <section
      id={id}
      className={`section-seam relative isolate min-h-screen w-full overflow-x-clip overflow-y-visible bg-black ${className}`}
    >
      <FadingVideo
        src={video}
        onReady={onReady}
        isHero={isHero}
        mirror={mirror}
        className={
          heroScale
            ? "absolute left-1/2 top-0 z-0 -translate-x-1/2 object-cover object-top"
            : "absolute inset-0 z-0 h-full w-full object-cover"
        }
        style={heroScale ? { width: "120%", height: "120%" } : undefined}
      />
      <div className="section-darken pointer-events-none absolute inset-0 z-[1]" aria-hidden="true" />
      <div className="relative z-10 min-h-screen overflow-visible">{children}</div>
    </section>
  );
}

function MetricIcon({ kind }: { kind: string }) {
  const common = {
    className: "h-7 w-7 text-white",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    "aria-hidden": true as const,
  };
  if (kind === "pulse")
    return (
      <svg {...common}>
        <path d="M3 12h4l3-7 4 14 3-7h4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (kind === "globe")
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" />
      </svg>
    );
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v8M9.5 10.5h3.5a1.5 1.5 0 0 1 0 3H10a1.5 1.5 0 0 0 0 3h3.5" strokeLinecap="round" />
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   ROOT LANDING PAGE
   ────────────────────────────────────────────────────────────────────── */
export function LandingPage() {
  const [heroReady, setHeroReady] = useState(false);
  const [loaderVisible, setLoaderVisible] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const navLinks = [
    { label: "Home", href: `#${SECTION_IDS.hero}` },
    { label: "The Cascade", href: `#${SECTION_IDS.capabilities}` },
    { label: "Architecture", href: "/architecture" },
    { label: "Audit Ledger", href: "/ledger" },
    { label: "Research", href: "/research" },
  ];

  useEffect(() => {
    const fallbackTimer = window.setTimeout(() => setLoaderVisible(false), 2600);
    return () => window.clearTimeout(fallbackTimer);
  }, []);

  useEffect(() => {
    if (!heroReady) return;
    const timer = window.setTimeout(() => setLoaderVisible(false), 500);
    return () => window.clearTimeout(timer);
  }, [heroReady]);

  useEffect(() => {
    warmAll([HERO_VIDEO, CAP_VIDEO]);
  }, []);

  return (
    <div className="lp-root font-body relative w-full overflow-x-hidden bg-black">
      <OrbitalLoader visible={loaderVisible} />

      {/* ── FLOATING GLASS NAVBAR ── */}
      <div className="pointer-events-none fixed inset-x-0 top-0 z-[70] px-3 pt-3 sm:px-6 lg:px-10">
        <nav className="landing-nav-shell pointer-events-auto mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-full px-3 py-2 sm:px-4">
          <a
            href={`#${SECTION_IDS.hero}`}
            className="inline-flex items-center gap-3 text-white"
            aria-label="VAANI-RAKSHAK Home"
            onClick={() => setMobileNavOpen(false)}
          >
            <BrandLogo size={40} />
            <span className="hidden text-sm font-semibold tracking-[0.2em] text-white/85 sm:inline">
              VAANI-RAKSHAK
            </span>
          </a>

          <div className="hidden items-center gap-1 md:flex">
            {navLinks.map((item) =>
              item.href.startsWith("#") ? (
                <a
                  key={item.label}
                  href={item.href}
                  className="rounded-full px-3 py-2 text-sm font-medium text-white/90 transition hover:bg-white/10 hover:text-white"
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.label}
                  href={item.href}
                  className="rounded-full px-3 py-2 text-sm font-medium text-white/90 transition hover:bg-white/10 hover:text-white"
                >
                  {item.label}
                </Link>
              )
            )}
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/detect"
              className="liquid-glass-strong hidden items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-white sm:inline-flex"
            >
              Launch Detector
              <ArrowUpRight className="h-4 w-4" />
            </Link>
            <button
              onClick={() => setMobileNavOpen((open) => !open)}
              className="liquid-glass inline-flex h-10 w-10 items-center justify-center rounded-full text-white md:hidden"
              aria-label={mobileNavOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileNavOpen}
            >
              {mobileNavOpen ? <CloseIcon className="h-4 w-4" /> : <MenuIcon className="h-4 w-4" />}
            </button>
          </div>
        </nav>

        <div
          className={`pointer-events-auto mx-auto mt-2 max-w-7xl transition duration-200 md:hidden ${
            mobileNavOpen ? "translate-y-0 opacity-100" : "pointer-events-none -translate-y-2 opacity-0"
          }`}
        >
          <div className="landing-nav-shell rounded-[1.75rem] px-3 py-3">
            <div className="flex flex-col gap-1">
              {navLinks.map((item) =>
                item.href.startsWith("#") ? (
                  <a
                    key={item.label}
                    href={item.href}
                    onClick={() => setMobileNavOpen(false)}
                    className="rounded-2xl px-4 py-3 text-sm font-medium text-white/92 transition hover:bg-white/10"
                  >
                    {item.label}
                  </a>
                ) : (
                  <Link
                    key={item.label}
                    href={item.href}
                    onClick={() => setMobileNavOpen(false)}
                    className="rounded-2xl px-4 py-3 text-sm font-medium text-white/92 transition hover:bg-white/10"
                  >
                    {item.label}
                  </Link>
                )
              )}
              <Link
                href="/detect"
                onClick={() => setMobileNavOpen(false)}
                className="liquid-glass-strong mt-2 inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium text-white"
              >
                Launch Detector
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ────────── SECTION 1 — HERO ────────── */}
      <SectionFrame
        id={SECTION_IDS.hero}
        video={HERO_VIDEO}
        heroScale
        onReady={() => setHeroReady(true)}
        isHero
      >
        <div className="relative flex min-h-[100svh] flex-col">
          <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-4 pb-12 pt-32 text-center sm:px-6 sm:pt-36 md:px-8 md:pb-14 md:pt-32">
            <motion.div
              initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut", delay: 0.4 }}
              className="liquid-glass mb-8 inline-flex items-center gap-2 rounded-full py-1 pl-1 pr-3"
            >
              <span className="rounded-full bg-saffron px-3 py-1 text-xs font-semibold text-ink-950">
                वाणी-रक्षक
              </span>
              <span className="pr-3 text-sm text-white/90">
                Deepfake vishing surged 1,633% — your voice is now an attack surface
              </span>
            </motion.div>

            <BlurText
              text="Catch the Cloned Voice Before It Speaks"
              className="text-6xl md:text-7xl lg:text-[5.5rem] font-heading italic text-white leading-[0.8] max-w-4xl justify-center tracking-[-4px]"
              delayOffset={0.5}
            />

            <motion.p
              initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut", delay: 0.8 }}
              className="mt-5 max-w-2xl font-body text-sm font-light leading-snug text-white md:text-base"
            >
              VAANI-RAKSHAK is a real-time, privacy-first voice-cloning detection framework
              built for India. A three-tier cascade — DSP pre-filter → neural countermeasure →
              deep multilingual SSL — flags AI-cloned voices <i>mid-call</i>, explains{" "}
              <b className="text-white/95">why</b> with SHAP, forces out-of-band verification,
              and anchors every decision to a tamper-evident ledger. 100% free, open-source and
              edge-first — raw audio never leaves the device.
            </motion.p>

            <motion.div
              initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut", delay: 1.1 }}
              className="mt-6 flex flex-wrap items-center justify-center gap-6"
            >
              <Link
                href="/detect"
                className="liquid-glass-strong inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white"
              >
                Launch the Live Detector
                <ArrowUpRight className="h-5 w-5" />
              </Link>
              <a
                href={`#${SECTION_IDS.capabilities}`}
                className="inline-flex items-center gap-2 text-sm font-medium text-white"
              >
                See the Cascade
                <PlayIcon className="h-4 w-4" />
              </a>
            </motion.div>

            {/* KPI-style hero metrics */}
            <motion.div
              initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut", delay: 1.3 }}
              className="hero-metrics-grid mt-8 grid w-full max-w-5xl grid-cols-1 items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-3"
            >
              {HERO_METRICS.map((m) => (
                <div key={m.value} className="liquid-glass min-w-0 rounded-[1.25rem] p-5 text-left">
                  <MetricIcon kind={m.icon} />
                  <div className="mt-3 font-heading text-4xl italic leading-none tracking-[-1px] text-white">
                    {m.value}
                  </div>
                  <div className="mt-2 font-body text-xs font-light text-white/90">{m.label}</div>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div
            initial={{ filter: "blur(10px)", opacity: 0, y: 20 }}
            animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: "easeOut", delay: 1.4 }}
            className="relative z-10 px-4 pb-8 sm:px-6"
          >
            <div className="flex flex-col items-center gap-4 px-4 text-center">
              <div className="liquid-glass rounded-full px-3.5 py-1 text-xs font-medium text-white">
                Built on the VCFAD research lineage · re-architected for production defence
              </div>
              <div className="flex flex-wrap items-center justify-center gap-10 md:gap-16">
                {["IndicWav2Vec", "AASIST3", "ECAPA-TDNN", "SHAP fusion", "Hyperledger audit"].map(
                  (name) => (
                    <span
                      key={name}
                      className="font-heading text-lg italic tracking-tight text-white md:text-2xl"
                    >
                      {name}
                    </span>
                  )
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </SectionFrame>

      {/* ────────── SECTION 2 — CAPABILITIES (mirrored video) ────────── */}
      <SectionFrame
        id={SECTION_IDS.capabilities}
        video={CAP_VIDEO}
        mirror
        className="landing-stack-section"
      >
        <div className="relative flex min-h-screen flex-col px-8 pb-10 pt-24 md:px-16 lg:px-20">
          <header className="mb-auto">
            <SectionReveal>
              <div className="mb-6 text-sm font-body text-white/80">// The cascade-triage core</div>
            </SectionReveal>
            <SectionReveal delay={0.08}>
              <h2 className="font-heading text-6xl italic leading-[0.9] tracking-[-3px] text-white md:text-7xl lg:text-[6rem]">
                Accuracy
                <br />
                without the cost
              </h2>
            </SectionReveal>
            <SectionReveal delay={0.16}>
              <p className="mt-6 max-w-2xl font-body text-sm font-light leading-relaxed text-white/90 md:text-base">
                Not one giant model on every millisecond — a three-tier cascade so expensive
                compute is invoked only when the cheap checks are ambiguous. Simultaneously
                high-accuracy and telecom-scale cheap.
              </p>
            </SectionReveal>
          </header>

          <div className="mt-16 grid grid-cols-1 gap-6 md:grid-cols-3">
            {capabilities.map((card, index) => (
              <SectionReveal key={card.title} delay={0.08 * index}>
                <div className="liquid-glass flex min-h-[360px] flex-col rounded-[1.25rem] p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="liquid-glass flex h-11 w-11 items-center justify-center rounded-[0.75rem]">
                      <svg
                        className="h-6 w-6 text-white"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={1.7}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d={card.iconPath} />
                      </svg>
                    </div>
                    <div className="flex max-w-[70%] flex-wrap justify-end gap-1.5">
                      {card.tags.map((tag) => (
                        <span
                          key={tag}
                          className="liquid-glass whitespace-nowrap rounded-full px-3 py-1 text-[11px] font-body text-white/90"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex-1" />
                  <div className="mt-6">
                    <h3 className="font-heading text-3xl italic leading-none tracking-[-1px] text-white md:text-4xl">
                      {card.title}
                    </h3>
                    <p className="mt-3 max-w-[34ch] font-body text-sm font-light leading-snug text-white/90">
                      {card.body}
                    </p>
                  </div>
                </div>
              </SectionReveal>
            ))}
          </div>

          <SectionReveal delay={0.28} className="mt-10">
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/detect"
                className="liquid-glass-strong inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-white"
              >
                Run it on your own voice
                <ArrowUpRight className="h-5 w-5" />
              </Link>
              <Link
                href="/architecture"
                className="inline-flex items-center gap-2 text-sm font-medium text-white"
              >
                Explore the full architecture
                <PlayIcon className="h-4 w-4" />
              </Link>
            </div>
          </SectionReveal>
        </div>
      </SectionFrame>
    </div>
  );
}
