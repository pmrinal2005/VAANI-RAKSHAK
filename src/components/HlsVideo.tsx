import { useEffect, useRef } from "react";
import Hls from "hls.js";

type Props = {
  src: string;
  className?: string;
  style?: React.CSSProperties;
};

export function HlsVideo({ src, className, style }: Props) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;

    if (src.endsWith(".m3u8") && Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      return () => {
        hls.destroy();
      };
    }
    video.src = src;
    return undefined;
  }, [src]);

  return (
    <video
      ref={ref}
      className={className}
      style={style}
      autoPlay
      loop
      muted
      playsInline
    />
  );
}
