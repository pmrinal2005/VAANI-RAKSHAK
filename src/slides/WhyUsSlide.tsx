import { motion } from "motion/react";
import { Zap, Eye, Shield, Landmark } from "lucide-react";

const VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260411_104032_69319010-2458-492b-b04d-b40a5dfa4482.mp4";

const CARDS = [
  {
    Icon: Zap,
    title: "Milliseconds, not minutes",
    desc: "A first verdict in under 5 ms. The clone does not get a conversation. Waiting is not a strategy.",
  },
  {
    Icon: Eye,
    title: "Privacy by architecture",
    desc: "Raw audio never leaves the device. Only irreversible hashes and scores travel. DPDP is not a checkbox — it is the design.",
  },
  {
    Icon: Landmark,
    title: "Built for Indian voice",
    desc: "22 scheduled languages. Code-switching. The fraud that hides in Hindi-English mix is the fraud we were born to catch.",
  },
  {
    Icon: Shield,
    title: "Evidence that holds",
    desc: "Every decision is anchored to a tamper-evident ledger. Courts, auditors, CERT-In — the trail is already there.",
  },
];

export function WhyUsSlide() {
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
      <div
        className="pointer-events-none absolute bottom-0 left-0 right-0 z-[1] h-[50%]"
        style={{ background: "linear-gradient(to top, black, transparent)" }}
      />
      <div className="relative z-10 flex h-full flex-col px-10 py-12 pb-20 lg:px-20">
        <div className="mb-auto flex flex-col lg:flex-row lg:items-end lg:justify-between">
          <div>
            <motion.span
              className="mb-4 block font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              Why Us
            </motion.span>
            <motion.h2
              className="font-heading text-3xl italic leading-[0.9] tracking-tight text-white md:text-4xl lg:text-5xl"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              The difference
              <br />
              is everything.
            </motion.h2>
          </div>
          <motion.p
            className="mt-4 max-w-sm font-body text-sm font-light text-white/35 lg:mt-0"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            We do not just flag a fake. We stop the wire, explain the lie, and leave a trail no
            attacker can rewrite.
          </motion.p>
        </div>

        <div className="flex flex-1 items-end">
          <div className="grid w-full grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
            {CARDS.map((c, i) => (
              <motion.div
                key={c.title}
                className="liquid-glass flex flex-col rounded-2xl p-6 lg:p-8"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
              >
                <div className="liquid-glass-strong mb-6 flex h-10 w-10 items-center justify-center rounded-full">
                  <c.Icon className="h-4 w-4 text-white" />
                </div>
                <h3 className="mb-2 font-body text-sm font-semibold text-white md:text-base">
                  {c.title}
                </h3>
                <p className="font-body text-xs font-light leading-relaxed text-white/40">
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
