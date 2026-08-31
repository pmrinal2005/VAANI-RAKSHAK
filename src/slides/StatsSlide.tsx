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
      <div className="relative z-10 flex h-full flex-col px-10 py-12 pb-20 lg:px-20">
        <div className="mb-auto">
          <motion.span
            className="mb-6 block font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            Traction
          </motion.span>
          <motion.h2
            className="max-w-4xl font-heading text-4xl italic leading-[0.9] tracking-tight text-white md:text-5xl lg:text-7xl"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Numbers that speak for themselves
          </motion.h2>
        </div>

        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {STATS.slice(0, 2).map((s, i) => (
              <Stat key={s.n} {...s} delay={0.35 + i * 0.1} />
            ))}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {STATS.slice(2).map((s, i) => (
              <Stat key={s.n} {...s} delay={0.55 + i * 0.1} />
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
      className="flex flex-col gap-8"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="h-px bg-white/20" />
      <div className="flex items-start gap-10 lg:gap-14">
        <span className="shrink-0 font-heading text-7xl italic leading-none text-white md:text-8xl lg:text-[9.5rem]">
          {n}
        </span>
        <p className="flex-1 pt-3 pr-8 font-body text-base font-normal leading-relaxed text-white md:text-lg lg:pt-4 lg:pr-20 lg:text-2xl">
          {d}
        </p>
      </div>
    </motion.div>
  );
}
