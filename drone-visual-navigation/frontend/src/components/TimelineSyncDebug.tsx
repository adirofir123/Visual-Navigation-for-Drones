import type { SyncMatch } from "../domain/sync";

interface Props {
  match: SyncMatch | null;
}

/** Secondary diagnostic footer describing sync residuals for researchers. */
export function TimelineSyncDebug({ match }: Props) {
  return (
    <div className="debug-inline">
      {match ? (
        <>
          <span className="chip chip-ok">
            Δ {match.deltaSeconds >= 0 ? "+" : ""}
            {match.deltaSeconds.toFixed(3)} s
          </span>
          <span className="muted">Nearest cue midpoint match (see domain/sync).</span>
        </>
      ) : (
        <span className="chip chip-warn">No synced telemetry (gap exceeds threshold).</span>
      )}
    </div>
  );
}
