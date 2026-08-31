"use client";

import { motion } from "motion/react";

const VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260406_094145_4a271a6c-3869-4f1c-8aa7-aeb0cb227994.mp4";

const QUOTES = [
  {
    q: "A cloned ‘relationship manager’ almost moved ₹42 lakh. VAANI froze the call, showed us why, and the money stayed put.",
    name: "Ananya Rao",
    role: "Head of Fraud, National Private Bank",
    initials: "AR",
  },
  {
    q: "We did not add a vendor. We added a guardian. Agents still talk. The clone does not get a second sentence.",
    name: "Vikram Mehta",
    role: "VP, Voice Ops · Major Telecom",
    initials: "VM",
  },
  {
    q: "The explanation is the product. When CERT-In asks ‘why did you block this?’, the ledger already has the answer.",
    name: "Dr. Leela Krishnan",
    role: "Chief Risk Officer, Payments Network",
    initials: "LK",
  },
];

export function TestimonialsSlide() {
  return (
    <section className="relative h-full w-full overflow-hidden">
      <video
        className="absolute inset-0 h-full w-full object-cover"
        src={VIDEO}
        autoPlay
        loop
        muted
        playsInline
      />
      <div className="relative z-10 flex h-full flex-col px-10 py-12 pb-20 lg:px-20">
        <motion.span
          className="mb-4 font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          Social Proof
        </motion.span>
        <motion.h2
          className="mb-auto font-heading text-3xl italic leading-[0.9] tracking-tight text-white md:text-4xl lg:text-5xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          Don’t take our
          <br />
          word for it.
        </motion.h2>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3 lg:gap-6">
          {QUOTES.map((t, i) => (
            <motion.div
              key={t.name}
              className="liquid-glass flex flex-col justify-between rounded-2xl p-8 lg:p-10"
              initial={{ opacity: 0, y: 25 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.12 }}
            >
              <div className="mb-8">
                <span className="mb-4 block font-heading text-3xl italic text-white/15">“</span>
                <p className="font-body text-sm font-light italic leading-relaxed text-white/70 lg:text-base">
                  {t.q}
                </p>
              </div>
              <div className="flex items-center gap-3 border-t border-white/10 pt-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 font-body text-xs font-medium text-white/60">
                  {t.initials}
                </div>
                <div>
                  <p className="font-body text-sm font-medium text-white">{t.name}</p>
                  <p className="font-body text-xs font-light text-white/40">{t.role}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
