import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // onnxruntime-web is a client-only dependency (loaded inside a "use client"
  // component). Keep it out of the server bundle so its Node/WASM glue isn't
  // traced or bundled during build.
  serverExternalPackages: ["onnxruntime-web"],
};

export default nextConfig;
