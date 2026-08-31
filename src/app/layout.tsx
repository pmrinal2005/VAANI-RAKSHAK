import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SiteChrome } from "@/components/SiteChrome";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "VAANI-RAKSHAK — AI Voice Cloning Detection Framework",
  description:
    "वाणी-रक्षक · Zero-cost, privacy-first, multilingual real-time voice-cloning detection with cascade-triage AI, explainable risk scoring, and blockchain-anchored audit for Indian banking & telecom.",
  keywords: [
    "deepfake voice detection",
    "voice cloning",
    "AASIST",
    "IndicWav2Vec",
    "anti-spoofing",
    "blockchain audit",
    "DPDP",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        {/* Akashara design-system typefaces */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Barlow:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
        {/* Cinematic landing background clips — prefetched so they decode
            instantly when the landing page mounts. Uses `prefetch` (not the
            non-standard `as="video"` preload, which browsers warn about). */}
        <link rel="prefetch" href="/landing_page.mp4" />
        <link rel="prefetch" href="/section3.mp4" />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <SiteChrome>{children}</SiteChrome>
      </body>
    </html>
  );
}
