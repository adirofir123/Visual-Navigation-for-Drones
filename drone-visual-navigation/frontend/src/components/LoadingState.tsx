interface Props {
  label?: string;
}

/** Full-panel loading treatment used during multipart upload / server parsing. */
export function LoadingState({ label }: Props) {
  return (
    <div className="loading-overlay" aria-live="polite">
      <div className="spinner" />
      <div className="loading-text">{label ?? "Working…"}</div>
    </div>
  );
}
