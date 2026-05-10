interface Props {
  src: string;
  onTick: (timeSeconds: number) => void;
}

/**
 * Thin wrapper over the HTML5 `<video>` element emitting timeline ticks during playback.
 *
 * input: authenticated media URL; output: emits `currentTime` as seconds.
 */
export function VideoPlayer({ src, onTick }: Props) {
  return (
    <video
      className="video-surface"
      controls
      src={src}
      onTimeUpdate={(e) => onTick(e.currentTarget.currentTime)}
      onSeeking={(e) => onTick(e.currentTarget.currentTime)}
      preload="metadata"
    />
  );
}
