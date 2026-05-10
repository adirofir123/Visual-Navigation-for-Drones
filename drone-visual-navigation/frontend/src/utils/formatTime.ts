/** Compact duration for file metadata (e.g. "3:42" or "1:05:02"). */
export function formatDurationShort(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

/** Render seconds as HH:MM:SS.ms (nearest millisecond under 999). */

export function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds)) {
    return "N/A";
  }
  const clamped = Math.max(0, seconds);
  const msTotal = Math.floor(clamped * 1000);
  const hrs = Math.floor(msTotal / 3_600_000);
  const mins = Math.floor((msTotal % 3_600_000) / 60_000);
  const secs = Math.floor((msTotal % 60_000) / 1000);
  const ms = msTotal % 1000;
  const pad = (n: number, w = 2) => `${n}`.padStart(w, "0");
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}.${pad(ms, 3)}`;
}
