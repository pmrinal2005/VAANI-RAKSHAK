import { motion } from "motion/react";
import { ArrowUpRight } from "lucide-react";
import { BlurText } from "@/components/BlurText";
import { Link } from "react-router-dom";

const VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260411_104229_49794008-3d16-4cb6-9a8c-73d7751b0e79.mp4";

export function TitleSlide() {
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
      <div className="relative z-10 flex h-full flex-col justify-between px-10 py-12 pb-20 lg:px-20">
        <motion.div
          className="flex items-center"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white">
            <span className="font-heading text-sm italic text-black">V</span>
          </div>
          <span className="ml-2 font-heading text-lg italic text-white/80">VAANI</span>
          <span className="mx-2 h-5 w-px bg-white/20" />
          <span className="font-body text-[10px] uppercase tracking-[0.2em] text-white/30">
            Pitch Deck 2026
          </span>
        </motion.div>

        <div className="flex max-w-3xl flex-1 flex-col justify-center">
          <motion.div
            className="liquid-glass mb-6 inline-flex w-fit items-center gap-2 rounded-full px-2 py-1.5"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span className="rounded-full bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-black">
              Live
            </span>
            <span className="pr-3 text-xs font-light text-white/70">
              Real-time voice-clone defence
            </span>
          </motion.div>

          <h1 className="mb-8 text-5xl leading-[0.85] tracking-[-3px] text-white md:text-7xl lg:text-8xl xl:text-[6.5rem] font-heading italic">
            <BlurText text="Catch the Clone Before It Speaks" delay={80} />
          </h1>

          <motion.p
            className="mb-10 max-w-xl font-body text-base font-light leading-relaxed text-white/50 md:text-lg"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.9 }}
          >
            A 30-second deepfake can empty an account. VAANI-RAKSHAK hears the lie, explains it in
            plain language, and locks the transaction — before a rupee moves.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 1.1 }}
          >
            <Link
              to="/detect"
              className="liquid-glass-strong inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-white"
            >
              Open Live Detector
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </motion.div>
        </div>

        <motion.div
          className="flex flex-wrap items-center gap-x-6 gap-y-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4 }}
        >
          <span className="text-[10px] uppercase tracking-[0.2em] text-white/30">Built for</span>
          {["Indian Banking", "Telecom", "CERT-In", "DPDP Act", "₹0 stack"].map((n) => (
            <span key={n} className="font-heading text-lg italic text-white/20 md:text-xl">
              {n}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
