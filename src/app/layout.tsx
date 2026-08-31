import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Barlow, Instrument_Serif, Inter } from "next/font/google";
import "./globals.css";
import { SiteChrome } from "@/components/SiteChrome";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const barlow = Barlow({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-barlow",
});
const instrument = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument",
});

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

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${barlow.variable} ${instrument.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0&display=swap"
          rel="stylesheet"
        />
        <link rel="prefetch" href="/landing_page.mp4" />
        <link rel="prefetch" href="/section3.mp4" />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <SiteChrome>{children}</SiteChrome>
      </body>
    </html>
  );
}
