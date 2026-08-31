/// <reference types="vite/client" />

declare global {
  interface Window {
    __vaaniVideoBlobs?: Record<string, string>;
  }
}

export {};
