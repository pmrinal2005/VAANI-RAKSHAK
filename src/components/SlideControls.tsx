import { ChevronLeft, ChevronRight } from "lucide-react";

type Props = {
  index: number;
  total: number;
  label: string;
  onPrev: () => void;
  onNext: () => void;
};

export function SlideControls({ index, total, label, onPrev, onNext }: Props) {
  const n = String(index + 1).padStart(2, "0");
  const t = String(total).padStart(2, "0");

  return (
    <div className="absolute bottom-0 left-0 right-0 z-50 px-8 pb-6 lg:px-12">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs uppercase tracking-[0.2em] text-white/30">
            {n} / {t}
          </span>
          <span className="h-4 w-px bg-white/15" />
          <span className="text-xs text-white/50">{label}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {Array.from({ length: total }).map((_, i) => (
              <span
                key={i}
                className={`h-1 rounded-full transition-all duration-500 ${
                  i === index ? "w-24 bg-white" : "w-8 bg-white/20 hover:bg-white/40"
                }`}
              />
            ))}
          </div>
          <span className="h-4 w-px bg-white/15" />
          <button
            type="button"
            onClick={onPrev}
            disabled={index === 0}
            className="flex h-8 w-8 items-center justify-center rounded-full text-white/50 hover:bg-white/10 hover:text-white disabled:opacity-20"
            aria-label="Previous slide"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={index === total - 1}
            className="flex h-8 w-8 items-center justify-center rounded-full text-white/50 hover:bg-white/10 hover:text-white disabled:opacity-20"
            aria-label="Next slide"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
