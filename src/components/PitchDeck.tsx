import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { TitleSlide } from "@/slides/TitleSlide";
import { ProblemSlide } from "@/slides/ProblemSlide";
import { CapabilitiesSlide } from "@/slides/CapabilitiesSlide";
import { WhyUsSlide } from "@/slides/WhyUsSlide";
import { StatsSlide } from "@/slides/StatsSlide";
import { TestimonialsSlide } from "@/slides/TestimonialsSlide";
import { CtaSlide } from "@/slides/CtaSlide";
import { SlideControls } from "@/components/SlideControls";

const SLIDES = [
  { id: "intro", label: "Introduction", Comp: TitleSlide },
  { id: "process", label: "The Process", Comp: ProblemSlide },
  { id: "caps", label: "Capabilities", Comp: CapabilitiesSlide },
  { id: "why", label: "Differentiators", Comp: WhyUsSlide },
  { id: "traction", label: "Traction", Comp: StatsSlide },
  { id: "proof", label: "Social Proof", Comp: TestimonialsSlide },
  { id: "next", label: "Next Steps", Comp: CtaSlide },
];

const variants = {
  enter: (d: number) => ({
    x: d > 0 ? "100%" : "-100%",
    opacity: 0,
    scale: 0.95,
  }),
  center: { x: 0, opacity: 1, scale: 1 },
  exit: (d: number) => ({
    x: d > 0 ? "-30%" : "30%",
    opacity: 0,
    scale: 0.95,
  }),
};

export function PitchDeck() {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(1);
  const lock = useRef(false);
  const root = useRef<HTMLElement>(null);
  const inView = useRef(false);
  const touchX = useRef<number | null>(null);

  const go = useCallback((nextIdx: number, direction: number) => {
    if (lock.current) return;
    if (nextIdx < 0 || nextIdx >= SLIDES.length) return;
    lock.current = true;
    setDir(direction);
    setIndex(nextIdx);
    window.setTimeout(() => {
      lock.current = false;
    }, 800);
  }, []);

  const next = useCallback(() => go(index + 1, 1), [go, index]);
  const prev = useCallback(() => go(index - 1, -1), [go, index]);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        inView.current = e.isIntersecting && e.intersectionRatio > 0.45;
      },
      { threshold: [0.45, 0.7] }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      if (!inView.current) return;
      if (Math.abs(e.deltaY) < 30 && Math.abs(e.deltaX) < 30) return;
      const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (delta > 0 && index < SLIDES.length - 1) {
        e.preventDefault();
        next();
      } else if (delta < 0 && index > 0) {
        e.preventDefault();
        prev();
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (!inView.current) return;
      if (["ArrowRight", "ArrowDown", " "].includes(e.key)) {
        e.preventDefault();
        next();
      } else if (["ArrowLeft", "ArrowUp"].includes(e.key)) {
        e.preventDefault();
        prev();
      }
    };
    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKey);
    };
  }, [index, next, prev]);

  const Slide = SLIDES[index].Comp;

  return (
    <section
      ref={root}
      id="pitch"
      className="relative h-screen w-full overflow-hidden bg-black"
    >
      <AnimatePresence mode="wait" custom={dir}>
        <motion.div
          key={SLIDES[index].id}
          className="absolute inset-0"
          custom={dir}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.65, ease: [0.4, 0, 0.2, 1] }}
          onTouchStart={(e) => {
            touchX.current = e.changedTouches[0]?.clientX ?? null;
          }}
          onTouchEnd={(e) => {
            if (touchX.current == null) return;
            const dx = (e.changedTouches[0]?.clientX ?? 0) - touchX.current;
            touchX.current = null;
            if (Math.abs(dx) < 60) return;
            if (dx < 0) next();
            else prev();
          }}
        >
          <Slide />
        </motion.div>
      </AnimatePresence>
      <SlideControls
        index={index}
        total={SLIDES.length}
        label={SLIDES[index].label}
        onPrev={prev}
        onNext={next}
      />
    </section>
  );
}
