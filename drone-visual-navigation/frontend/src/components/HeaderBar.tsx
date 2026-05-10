import { FileDown, Navigation, UploadCloud } from "lucide-react";

import type { FlightSession } from "../domain/flight";

interface Props {
  session: FlightSession | null;
  onLoadNewData: () => void;
  onExport: () => void;
}

export function HeaderBar({ session, onLoadNewData, onExport }: Props) {
  const fid = session ? session.flightId : null;

  return (
    <header className="app-header">
      <div className="brand-cluster">
        <span className="brand-mark" aria-hidden>
          <Navigation className="brand-mark-svg" strokeWidth={2} />
        </span>
        <div className="min-w-0">
          <div className="brand-title">Drone visual navigation inspector</div>
          <div className="muted flight-meta-sub">Telemetry + video • local Milestone&nbsp;1</div>
        </div>
      </div>
      <div className="header-bar-actions">
        {fid ? (
          <span className="chip chip-ok flight-meta-sub">
            Loaded <span title={fid}>{fid.slice(0, 10)}…</span>
          </span>
        ) : (
          <span className="chip chip-neutral flight-meta-sub">No flight loaded</span>
        )}
        <button type="button" className="ghost-btn btn-header" onClick={onLoadNewData}>
          <UploadCloud size={16} strokeWidth={2} aria-hidden />
          Load new data
        </button>
        <button type="button" className="primary-btn btn-header" onClick={onExport} disabled={!session}>
          <FileDown size={16} strokeWidth={2} aria-hidden />
          Export telemetry
        </button>
      </div>
    </header>
  );
}
