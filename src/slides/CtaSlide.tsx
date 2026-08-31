import { motion } from "motion/react";
import { ArrowUpRight, Mail } from "lucide-react";
import { Link } from "react-router-dom";

const VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260324_024928_1efd0b0d-6c02-45a8-8847-1030900c4f63.mp4";

export function CtaSlide() {
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
          Next Steps
        </motion.span>

        <div className="flex flex-1 flex-col items-start gap-12 lg:flex-row lg:items-center lg:gap-20">
          <div className="max-w-2xl flex-1">
            <motion.h2
              className="mb-6 font-heading text-5xl italic leading-[0.85] tracking-tight text-white md:text-6xl lg:text-7xl xl:text-8xl"
              initial={{ opacity: 0, x: -25 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              Your next call
              <br />
              is already a target.
            </motion.h2>
            <motion.p
              className="mb-10 max-w-md font-body text-sm font-light leading-relaxed text-white/40 md:text-base"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
            >
              Open the live detector. Hear a clone get caught. No commitment, no cloud, no raw
              audio leaving the browser. Just the guardian, running.
            </motion.p>
            <motion.div
              className="flex items-center gap-4"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Link
                to="/detect"
                className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 font-body text-sm font-semibold text-black"
              >
                Open Live Detector
                <ArrowUpRight className="h-4 w-4" />
              </Link>
              <Link
                to="/architecture"
                className="liquid-glass-strong inline-flex rounded-full px-6 py-3 font-body text-sm font-medium text-white"
              >
                See the blueprint
              </Link>
            </motion.div>
          </div>

          <motion.div
            className="liquid-glass w-full max-w-xs rounded-2xl p-8 lg:p-10"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
          >
            <div className="mb-5 flex items-center gap-3">
              <div className="liquid-glass-strong flex h-10 w-10 items-center justify-center rounded-full">
                <Mail className="h-4 w-4 text-white" />
              </div>
              <span className="font-body text-sm font-medium text-white">Get in touch</span>
            </div>
            <p className="font-body text-sm text-white/70">hello@vaani-rakshak.in</p>
            <p className="font-body text-sm text-white/70">वाणी-रक्षक · Guardian of Voice</p>
            <div className="mt-4 border-t border-white/10 pt-4 text-xs text-white/30">
              <p>Bengaluru, IN</p>
              <p>New Delhi, IN</p>
            </div>
          </motion.div>
        </div>

        <motion.div
          className="mt-8 flex justify-between border-t border-white/10 pt-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0 }}
        >
          <span className="text-xs text-white/30">
            © 2026 VAANI-RAKSHAK. All rights reserved.
          </span>
          <div className="flex gap-4 text-xs text-white/30">
            <Link to="/research" className="hover:text-white/60">
              Research
            </Link>
            <Link to="/ledger" className="hover:text-white/60">
              Ledger
            </Link>
            <Link to="/colab" className="hover:text-white/60">
              Models
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
