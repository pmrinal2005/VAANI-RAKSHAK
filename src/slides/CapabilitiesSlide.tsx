import { motion } from "motion/react";
import { HlsVideo } from "@/components/HlsVideo";

const BG =
  "https://stream.mux.com/s8pMcOvMQXc4GD6AX4e1o01xFogFxipmuKltNfSYza0200.m3u8";

const CARDS = [
  {
    title: "Built to catch. Designed to explain.",
    body: "Every score arrives with a reason. VAANI studies the texture of a voice — the tremor, the breath, the pitch — then tells your agent exactly why this call is safe, or why it isn’t.",
    videoSrc:
      "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260302_085844_21a8f4b3-dea5-4ede-be16-d53f6973bb14.mp4",
    hls: false,
  },
  {
    title: "It guards 22 languages. Automatically.",
    body: "One shared backbone. Lightweight adapters per language. Hindi, Tamil, Telugu, Bengali — the clone does not get a free pass just because the caller switched tongues.",
    videoSrc: "https://stream.mux.com/T6oQJQ02cQ6N01TR6iHwZkKFkbepS34dkkIc9iukgy400g.m3u8",
    hls: true,
  },
];

export function CapabilitiesSlide() {
  return (
    <section className="relative h-full w-full overflow-hidden bg-black">
      <HlsVideo
        src={BG}
        className="absolute inset-0 h-full w-full object-cover"
        style={{ opacity: 0.5 }}
      />
      <div className="relative z-10 flex h-full flex-col px-10 py-12 pb-20 lg:px-20">
        <motion.span
          className="mb-4 font-body text-[10px] uppercase tracking-[0.3em] text-white/30"
          initial={{ opacity: 0, x: -15 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          Capabilities
        </motion.span>
        <motion.h2
          className="mb-8 font-heading text-6xl italic leading-[0.85] tracking-tight text-white md:text-8xl lg:mb-auto lg:text-9xl xl:text-[10rem]"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          Pro defence.
          <br />
          Zero complexity.
        </motion.h2>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
          {CARDS.map((c, i) => (
            <motion.div
              key={c.title}
              className="liquid-glass flex flex-col overflow-hidden rounded-2xl"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 + i * 0.15 }}
            >
              <div className="relative h-44 overflow-hidden lg:h-56">
                {c.hls ? (
                  <HlsVideo src={c.videoSrc} className="h-full w-full object-cover" />
                ) : (
                  <video
                    src={c.videoSrc}
                    className="h-full w-full object-cover"
                    autoPlay
                    loop
                    muted
                    playsInline
                  />
                )}
              </div>
              <div className="p-6 lg:p-8">
                <h3 className="mb-2 font-heading text-lg italic leading-tight text-white md:text-xl">
                  {c.title}
                </h3>
                <p className="font-body text-sm font-light leading-relaxed text-white/40">
                  {c.body}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
