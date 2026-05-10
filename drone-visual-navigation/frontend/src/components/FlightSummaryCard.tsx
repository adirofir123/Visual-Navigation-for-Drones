import type { FlightSession } from "../domain/flight";

interface Props {
  session: FlightSession;
}

/** Compact mission summary badges for telemetry health + ingest stats. */
export function FlightSummaryCard({ session }: Props) {
  const { summary, videoMetadata } = session;
  const gps = summary.gps_point_count ?? 0;
  const duration = summary.duration_seconds_srt_end;

  const chips = [
    { label: "SRT cues", value: `${summary.record_count}`, tone: "ok" },
    {
      label: "GPS fixes",
      value: `${gps}`,
      tone: gps > 1 ? "ok" : "warn",
    },
    {
      label: "Timeline end",
      value: typeof duration === "number" ? `${duration.toFixed(2)} s` : "N/A",
      tone: "neutral",
    },
    {
      label: "Probe",
      value: videoMetadata.probe_source,
      tone: videoMetadata.probe_source === "none" ? "warn" : "neutral",
    },
    {
      label: "Resolution",
      value:
        videoMetadata.width && videoMetadata.height
          ? `${videoMetadata.width}×${videoMetadata.height}`
          : "N/A",
      tone: "neutral",
    },
    {
      label: "Video duration",
      value:
        typeof videoMetadata.duration_seconds === "number"
          ? `${videoMetadata.duration_seconds.toFixed(2)} s`
          : "N/A",
      tone: "neutral",
    },
  ];

  return (
    <div className="summary-grid">
      {chips.map((chip) => (
        <div key={chip.label} className={`summary-chip tone-${chip.tone}`}>
          <div className="summary-chip-label">{chip.label}</div>
          <div className="summary-chip-value">{chip.value}</div>
        </div>
      ))}
      <div className="summary-chip tone-neutral stretch">
        <div className="summary-chip-label">Detected fields ({session.fieldsDetected.length})</div>
        <div className="summary-chip-muted">
          {session.fieldsDetected.slice(0, 8).join(", ")}
          {session.fieldsDetected.length > 8 ? " …" : ""}
        </div>
      </div>
    </div>
  );
}
