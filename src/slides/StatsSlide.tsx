"use client";

import { motion } from "motion/react";
import { HlsVideo } from "@/components/HlsVideo";

const HLS = "https://stream.mux.com/NcU3HlHeF7CUL86azTTzpy3Tlb00d6iF3BmCdFslMJYM.m3u8";

const STATS = [
  { n: "<5 ms", d: "First verdict on every call chunk — CPU-only, no cloud round-trip" },
  { n: "22", d: "Indian languages guarded by one shared backbone — not 22 heavy models" },
  { n: "$0", d: "Cost to run. 100% free, open-source, edge-first. No SaaS tax on trust." },
  { n: "95%", d: "Of live audio exits at the cheap tiers — heavy compute stays rare by design" },
];

export function StatsSlide() {
  return (
    <section className="relative h-full w-full overflow-hidden">
      <HlsVideo
        src={HLS}
        className="absolute inset-0 h-full w-full object-cover"
        style={{ filter: "saturate(0)" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-black/82" />

      <div className="relative z-10 flex h-full min-h-0 flex-col px-5 pb-20 pt-7 sm:px-10 sm:pb-24 sm:pt-10 lg:px-16 xl:px-20">
        <header className="shrink-0">
          <motion.span
            className="mb-3 block font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            Traction
          </motion.span>
          <motion.h2
            className="max-w-4xl font-heading text-[clamp(1.85rem,4.4vw,4.1rem)] italic leading-[0.95] tracking-tight text-white"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Numbers that speak for themselves
          </motion.h2>
        </header>

        <div className="relative mt-5 flex min-h-0 flex-1 flex-col justify-center sm:mt-7">
          <div className="stats-glow-line pointer-events-none absolute left-0 right-0 top-1/2 z-0 hidden h-px -translate-y-1/2 sm:block" />

          <div className="relative z-10 grid min-h-0 grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2 sm:grid-rows-2 sm:gap-x-12 sm:gap-y-10 lg:gap-x-20 lg:gap-y-12">
            {STATS.map((s, i) => (
              <Stat key={s.n} {...s} delay={0.28 + i * 0.08} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ n, d, delay }: { n: string; d: string; delay: number }) {
  return (
    <motion.div
      className="flex min-h-0 min-w-0 flex-col justify-center gap-2 sm:gap-3"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="h-px w-full max-w-lg bg-gradient-to-r from-white/50 via-saffron/55 to-transparent" />
      <p className="font-heading text-[clamp(2.4rem,5.2vw,4.6rem)] italic leading-none text-white">
        {n}
      </p>
      <p className="max-w-[34ch] text-pretty hyphens-none break-words font-body text-[0.95rem] font-normal leading-[1.45] text-white/75 sm:max-w-[36ch] sm:text-base lg:text-lg">
        {d}
      </p>
    </motion.div>
  );
}
