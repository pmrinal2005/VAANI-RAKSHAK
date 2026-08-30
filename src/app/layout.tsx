import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { NavBar } from "@/components/NavBar";

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
      <body className="min-h-screen font-sans antialiased">
        <NavBar />
        <main className="mx-auto w-full max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
          {children}
        </main>
        <footer className="border-t border-white/10 py-8 text-center text-xs text-white/40">
          <p>
            VAANI-RAKSHAK · वाणी-रक्षक — Guardian of Voice · 100% free/open-source stack ·
            Edge-first · DPDP-aligned
          </p>
          <p className="mt-1">
            Research &amp; engineering prototype. Deployed on Vercel. Detection runs fully
            client-side (privacy by architecture).
          </p>
        </footer>
      </body>
    </html>
  );
}
