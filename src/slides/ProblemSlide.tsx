"use client";

import { motion } from "motion/react";
import { HlsVideo } from "@/components/HlsVideo";

const HLS =
  "https://stream.mux.com/9JXDljEVWYwWu01PUkAemafDugK89o01BR6zqJ3aS9u00A.m3u8";

const CARDS = [
  {
    icon: "query_stats",
    title: "Instant acoustic verdict",
    desc: "Every call chunk is scored in under 5 milliseconds — so obvious clones never wait for a heavy model, and genuine voices are never delayed.",
  },
  {
    icon: "psychology",
    title: "Decisions you can defend",
    desc: "A plain-language ‘why’ rides with every score. Frontline staff, auditors and courts see the evidence — not a black box.",
  },
  {
    icon: "integration_instructions",
    title: "Drops into the call path",
    desc: "Softphone, SIP, or upload. No new hardware. No voice leaving the device. Privacy by architecture, not by promise.",
  },
];

export function ProblemSlide() {
  return (
    <section className="relative h-full w-full overflow-hidden">
      <HlsVideo src={HLS} className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 z-[1] bg-black/60" />
      <div className="relative z-10 flex h-full px-10 py-12 pb-20 lg:px-20">
        <div className="my-auto flex w-full flex-col items-start gap-12 lg:flex-row lg:gap-20">
          <div className="flex-1">
            <motion.span
              className="mb-6 block font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
            >
              The Process
            </motion.span>
            <motion.h2
              className="mb-8 font-heading text-4xl italic leading-[0.9] tracking-tight text-white md:text-5xl lg:text-6xl xl:text-7xl"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              Our cascade catches the clone, explains why, and locks the transfer
            </motion.h2>
            <motion.p
              className="max-w-xl font-body text-sm font-light leading-relaxed text-white/40 md:text-base"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              Cheap checks run first. Heavy models wake only when the call is suspicious or
              high-stakes. Most audio exits in milliseconds. The rest is stopped, explained, and
              written to a tamper-evident ledger.
            </motion.p>
          </div>

          <div className="flex w-full shrink-0 flex-col gap-4 lg:w-[420px]">
            {CARDS.map((c, i) => (
              <motion.div
                key={c.title}
                className="liquid-glass rounded-2xl p-6 lg:p-7"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.12 }}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-white/15 to-white/5">
                    <span className="material-symbols-rounded text-xl text-white/80">
                      {c.icon}
                    </span>
                  </div>
                  <h3 className="font-body text-base font-semibold text-white">{c.title}</h3>
                </div>
                <p className="pl-[52px] font-body text-sm font-light leading-relaxed text-white/40">
                  {c.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
