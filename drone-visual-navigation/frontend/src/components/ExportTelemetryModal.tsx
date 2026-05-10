import { useId, useState } from "react";

import { exportHref } from "../api/flightApi";

type ExportKind = "csv" | "json" | "kml";

interface Props {
  open: boolean;
  flightId: string;
  onClose: () => void;
}

function triggerDownload(url: string, suggestedName: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = suggestedName;
  a.rel = "noreferrer";
  a.target = "_blank";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

const OPTIONS: { kind: ExportKind; title: string; desc: string; filename: string }[] = [
  {
    kind: "csv",
    title: "CSV",
    filename: "{id}_telemetry.csv",
    desc: "Spreadsheet-ready table of parsed cues and scalar fields.",
  },
  {
    kind: "json",
    title: "JSON",
    filename: "{id}_telemetry.json",
    desc: "Structured telemetry records plus summary envelope for tooling.",
  },
  {
    kind: "kml",
    title: "KML (Google Earth)",
    filename: "{id}_path.kml",
    desc: "Drone GPS path overlay for desktop or web Earth viewers.",
  },
];

export function ExportTelemetryModal({ open, flightId, onClose }: Props) {
  const reactId = useId();
  const [kind, setKind] = useState<ExportKind>("csv");

  if (!open) return null;

  const resolvedName = OPTIONS.find((o) => o.kind === kind)?.filename.replace("{id}", flightId) ?? `${flightId}_export`;

  const doExport = () => {
    const url = exportHref(flightId, kind);
    triggerDownload(url, resolvedName);
  };

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div role="dialog" aria-modal aria-labelledby={`${reactId}-export-title`} className="card modal-dialog">
        <header className="modal-dialog-head">
          <div className="section-kicker">Export</div>
          <h2 id={`${reactId}-export-title`} style={{ margin: "4px 0 0", fontSize: "20px" }}>
            Download telemetry
          </h2>
          <p className="muted flight-meta-sub" style={{ margin: "8px 0 0" }}>
            Your browser saves to the default Downloads folder. The server suggests <code style={{ color: "#cbd5e1" }}>{resolvedName}</code>.
          </p>
        </header>

        <div className="export-options" role="radiogroup" aria-label="Export format">
          {OPTIONS.map((opt) => (
            <label key={opt.kind} className="export-option-label">
              <input
                type="radio"
                className="export-option-radio"
                name={`${reactId}-fmt`}
                checked={kind === opt.kind}
                onChange={() => setKind(opt.kind)}
              />
              <span className="export-option-copy">
                <strong>{opt.title}</strong>
                <span>{opt.desc}</span>
              </span>
            </label>
          ))}
        </div>

        <footer className="modal-dialog-footer">
          <button type="button" className="ghost-btn" onClick={onClose}>
            Close
          </button>
          <button type="button" className="primary-btn" onClick={doExport}>
            Download
          </button>
        </footer>
      </div>
    </div>
  );
}
