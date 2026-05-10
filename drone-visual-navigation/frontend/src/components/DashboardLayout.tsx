import type { ReactNode } from "react";

interface Props {
  video: ReactNode;
  map: ReactNode;
  telemetry: ReactNode;
}

export function DashboardLayout({ video, map, telemetry }: Props) {
  return (
    <main className="dashboard-viewport" aria-label="Flight inspection">
      <div className="dashboard-grid-wrap">
        <div className="dashboard-cell-video">{video}</div>
        <div className="dashboard-cell-map">{map}</div>
        <div className="dashboard-cell-telemetry">{telemetry}</div>
      </div>
    </main>
  );
}
