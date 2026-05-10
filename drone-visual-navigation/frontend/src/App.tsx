import { useCallback, useMemo, useState } from "react";

import { uploadFlight } from "./api/flightApi";

import type { FlightManualMetadata, FlightSession } from "./domain/flight";

import { findTelemetryForTime } from "./domain/sync";

import { formatClock } from "./utils/formatTime";

import { DashboardLayout } from "./components/DashboardLayout";

import { DroneMap } from "./components/DroneMap";

import { ExportTelemetryModal } from "./components/ExportTelemetryModal";

import { HeaderBar } from "./components/HeaderBar";

import { LoadingState } from "./components/LoadingState";

import { TelemetryPanel } from "./components/TelemetryPanel";

import { UploadFlightModal } from "./components/UploadFlightModal";

import { VideoPlayer } from "./components/VideoPlayer";

export default function App() {
  const [session, setSession] = useState<FlightSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(true);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [uploadApiError, setUploadApiError] = useState<string | null>(null);
  const [timeline, setTimeline] = useState(0);

  const sync = useMemo(
    () => (session ? findTelemetryForTime(session.records, timeline) : null),
    [session, timeline],
  );

  const handleUpload = useCallback(async (
    video: File,
    srt: File,
    manual?: Partial<FlightManualMetadata>,
    dat?: File,
  ) => {
    setLoading(true);
    setUploadApiError(null);
    try {
      const sess = await uploadFlight(video, srt, manual, dat);
      setSession(sess);
      setTimeline(0);
      setUploadModalOpen(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong while loading the flight.";
      setUploadApiError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className={`app-shell${!session ? " app-shell-empty" : ""}`}>
      {loading && session ? <LoadingState label="Loading flight…" /> : null}

      <HeaderBar
        session={session}
        onLoadNewData={() => {
          setUploadApiError(null);
          setUploadModalOpen(true);
        }}
        onExport={() => session && setExportModalOpen(true)}
      />

      {session ? (
        <DashboardLayout
          video={
            <section className="card dashboard-card-fill">
              <div className="section-head compact">
                <div>
                  <div className="section-kicker">Video</div>
                  <h2 style={{ margin: "4px 0 0" }}>Flight recording</h2>
                </div>
                <div className="chip chip-neutral">{formatClock(timeline)}</div>
              </div>
              <div className="dashboard-card-inner-grow video-only-stack">
                <VideoPlayer src={session.videoUrl} onTick={(t) => setTimeline(t)} />
              </div>
            </section>
          }
          map={
            <section className="card dashboard-card-fill">
              <div className="section-head compact">
                <div>
                  <div className="section-kicker">Trajectory</div>
                  <h2 style={{ margin: "4px 0 0" }}>OpenStreetMap overlay</h2>
                </div>
              </div>
              <div className="dashboard-card-inner-grow">
                <DroneMap records={session.records} currentRecord={sync?.record} />
              </div>
            </section>
          }
          telemetry={
            <aside className="card dashboard-card-fill telemetry-aside-stack">
              <div className="section-head compact">
                <div>
                  <div className="section-kicker">Telemetry</div>
                  <h2 style={{ margin: "4px 0 0" }}>SRT inspector</h2>
                </div>
              </div>
              <TelemetryPanel
                session={session}
                currentSeconds={timeline}
                record={sync?.record}
                syncMatch={sync}
              />
            </aside>
          }
        />
      ) : (
        <main className="dashboard-viewport dashboard-empty-shell" aria-hidden={uploadModalOpen} />
      )}

      <UploadFlightModal
        open={uploadModalOpen}
        hasExistingSession={Boolean(session)}
        loading={loading}
        apiError={uploadApiError}
        onClose={() => {
          if (!loading) setUploadModalOpen(false);
        }}
        onLoad={handleUpload}
      />

      {session ? (
        <ExportTelemetryModal
          open={exportModalOpen}
          flightId={session.flightId}
          onClose={() => setExportModalOpen(false)}
        />
      ) : null}
    </div>
  );
}
