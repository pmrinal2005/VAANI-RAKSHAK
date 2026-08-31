import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1120",
          850: "#0f1728",
          800: "#131c30",
          700: "#1c2740",
        },
        saffron: "#ff9933",
        indiagreen: "#138808",
        chakra: "#0b3d91",
        danger: "#ef4444",
        warn: "#f59e0b",
        safe: "#22c55e",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        // Akashara design-system typefaces (ported for landing + shared chrome)
        heading: ['"Instrument Serif"', "serif"],
        body: ['"Barlow"', '"Inter"', "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(255,153,51,0.35)",
      },
      keyframes: {
        pulseline: {
          "0%,100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        pulseline: "pulseline 1.6s ease-in-out infinite",
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
