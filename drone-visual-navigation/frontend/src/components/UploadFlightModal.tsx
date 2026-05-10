import { Database, FileText, Video as VideoIcon } from "lucide-react";
import { FormEvent, useEffect, useId, useRef, useState } from "react";

import type { FlightManualMetadata } from "../domain/flight";
import {
  isAcceptedDatExtension,
  isAcceptedVideoExtension,
  listUnsupportedDropped,
  pickFirstDat,
  pickFirstSrt,
  pickFirstVideoByExtension,
} from "../domain/fileSelection";
import { formatDurationShort } from "../utils/formatTime";
import { isValidSrtFile, isValidVideoFile } from "../utils/fileValidation";
import { readVideoDurationSeconds } from "../utils/readVideoDuration";
import { CombinedFlightDropZone } from "./CombinedFlightDropZone";
import { SelectedFileCard, type FileSlotStatus } from "./SelectedFileCard";

interface Props {
  open: boolean;
  hasExistingSession: boolean;
  loading: boolean;
  apiError?: string | null;
  onClose: () => void;
  onLoad: (
    video: File,
    srt: File,
    manual?: Partial<FlightManualMetadata>,
    dat?: File,
  ) => Promise<void>;
}

const VIDEO_REPLACE_ACCEPT =
  "video/mp4,video/quicktime,video/webm,video/x-msvideo,video/x-matroska,.mp4,.mov,.avi,.mkv,.webm";

function validateVideoCandidate(f: File): string | null {
  if (!isAcceptedVideoExtension(f.name))
    return "Use MP4, MOV, AVI, MKV, or WebM for video (by file extension).";
  if (!isValidVideoFile(f)) return "This file does not look like a supported video container.";
  return null;
}

function slotStatus(ok: boolean, file: File | null, msg: string | null): FileSlotStatus {
  if (!file) return "missing";
  if (msg) return "invalid";
  return ok ? "valid" : "selected";
}

function manualInputsToPayload(heightStr: string, angleStr: string):
  | { ok: true; value: Partial<FlightManualMetadata> }
  | { ok: false; message: string } {
  const hs = heightStr.trim();
  const as = angleStr.trim();
  const value: Partial<FlightManualMetadata> = {};
  if (hs) {
    const n = Number(hs.replace(",", "."));
    if (!Number.isFinite(n)) {
      return { ok: false, message: "Height above takeoff must be a valid number." };
    }
    value.manual_height_above_takeoff_m = n;
  }
  if (as) {
    const n = Number(as.replace(",", "."));
    if (!Number.isFinite(n)) {
      return { ok: false, message: "Camera angle must be a valid number." };
    }
    if (n < 0 || n > 90) {
      return { ok: false, message: "Camera angle must be between 0 and 90 degrees." };
    }
    value.manual_camera_angle_deg = n;
  }
  return { ok: true, value };
}

function mergeDropBundle(
  incoming: File[],
  prevVideo: File | null,
  prevSrt: File | null,
  prevDat: File | null,
): {
  video: File | null;
  srt: File | null;
  dat: File | null;
  videoErr: string | null;
  srtErr: string | null;
  datErr: string | null;
  unsupportedMessage: string | null;
} {
  let video = prevVideo;
  let srt = prevSrt;
  let dat = prevDat;
  let videoErr: string | null = null;
  let srtErr: string | null = null;
  let datErr: string | null = null;

  const unsupported = listUnsupportedDropped(incoming);
  const unsupportedMessage = unsupported.length
    ? `Ignored ${unsupported.length} unsupported file${unsupported.length > 1 ? "s" : ""}: ${unsupported
        .map((f) => `"${f.name}"`)
        .join(", ")}. Use MP4/MOV/AVI/MKV/WebM, .srt, or optional .dat.`
    : null;

  const vCand = pickFirstVideoByExtension(incoming);
  const sCand = pickFirstSrt(incoming);
  const dCand = pickFirstDat(incoming);

  if (vCand) {
    video = vCand;
    videoErr = validateVideoCandidate(vCand);
  }
  if (sCand) {
    srt = sCand;
    srtErr = isValidSrtFile(sCand) ? null : "Telemetry must be a DJI-style .srt subtitle file.";
  }
  if (dCand) {
    dat = dCand;
    datErr = isAcceptedDatExtension(dCand.name)
      ? null
      : "Optional flight log must use a .dat extension.";
  }

  return { video, srt, dat, videoErr, srtErr, datErr, unsupportedMessage };
}

export function UploadFlightModal({
  open,
  hasExistingSession,
  loading,
  apiError,
  onClose,
  onLoad,
}: Props) {
  const reactId = useId();
  const videoInputId = `${reactId}-replace-video`;
  const srtInputId = `${reactId}-replace-srt`;
  const datInputId = `${reactId}-replace-dat`;
  const videoInputRef = useRef<HTMLInputElement | null>(null);
  const srtInputRef = useRef<HTMLInputElement | null>(null);
  const datInputRef = useRef<HTMLInputElement | null>(null);
  const wasOpenRef = useRef(false);

  const [video, setVideo] = useState<File | null>(null);
  const [srt, setSrt] = useState<File | null>(null);
  const [dat, setDat] = useState<File | null>(null);
  const [videoErr, setVideoErr] = useState<string | null>(null);
  const [srtErr, setSrtErr] = useState<string | null>(null);
  const [datErr, setDatErr] = useState<string | null>(null);
  const [dropHint, setDropHint] = useState<string | null>(null);
  const [durationSec, setDurationSec] = useState<number | null>(null);
  const [manualHeight, setManualHeight] = useState("");
  const [manualAngle, setManualAngle] = useState("");
  const [manualParseError, setManualParseError] = useState<string | null>(null);

  useEffect(() => {
    if (open && !wasOpenRef.current) {
      setVideo(null);
      setSrt(null);
      setDat(null);
      setVideoErr(null);
      setSrtErr(null);
      setDatErr(null);
      setDropHint(null);
      setDurationSec(null);
      setManualHeight("");
      setManualAngle("");
      setManualParseError(null);
    }
    wasOpenRef.current = open;
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, loading, onClose]);

  useEffect(() => {
    if (!video || !open) {
      setDurationSec(null);
      return undefined;
    }
    const vErr = validateVideoCandidate(video);
    if (!isValidVideoFile(video) || vErr) {
      setDurationSec(null);
      return undefined;
    }
    let cancelled = false;
    readVideoDurationSeconds(video).then((d) => {
      if (!cancelled && d !== undefined && Number.isFinite(d)) setDurationSec(d);
      else if (!cancelled) setDurationSec(null);
    });
    return () => {
      cancelled = true;
    };
  }, [video, open]);

  if (!open) return null;

  const applyBundle = (files: File[]) => {
    const merged = mergeDropBundle(files, video, srt, dat);
    setVideo(merged.video);
    setVideoErr(merged.videoErr);
    setSrt(merged.srt);
    setSrtErr(merged.srtErr);
    setDat(merged.dat);
    setDatErr(merged.datErr);
    setDropHint(merged.unsupportedMessage);
  };

  const replaceVideoPick = (f: File | null) => {
    if (!f) return;
    if (!isAcceptedVideoExtension(f.name)) {
      setVideo(f);
      setVideoErr(
        validateVideoCandidate(f) ?? "Use MP4, MOV, AVI, MKV, or WebM for video (by file extension).",
      );
      setDurationSec(null);
      return;
    }
    setVideo(f);
    setVideoErr(validateVideoCandidate(f));
  };

  const replaceSrtPick = (f: File | null) => {
    if (!f) return;
    setSrt(f);
    setSrtErr(isValidSrtFile(f) ? null : "Telemetry must be a DJI-style .srt subtitle file.");
  };

  const replaceDatPick = (f: File | null) => {
    if (!f) return;
    setDat(f);
    setDatErr(isAcceptedDatExtension(f.name) ? null : "Optional flight log must use a .dat extension.");
  };

  function datSlotStatus(ok: boolean, file: File | null, msg: string | null): FileSlotStatus {
    if (!file) return "optional";
    if (msg) return "invalid";
    return ok ? "valid" : "selected";
  }

  const durationLine =
    durationSec != null && !videoErr ? formatDurationShort(durationSec) : null;

  const videoOk =
    !!video &&
    videoErr === null &&
    isAcceptedVideoExtension(video.name) &&
    isValidVideoFile(video) &&
    validateVideoCandidate(video) === null;
  const srtOk = !!srt && srtErr === null && isValidSrtFile(srt);
  const canSubmit = Boolean(videoOk && srtOk && video && srt && !loading);

  const missingParts: string[] = [];
  if (!video) missingParts.push("video");
  if (!srt) missingParts.push("SRT telemetry");
  const missingText =
    missingParts.length === 2
      ? "Add a video file and its matching .srt."
      : missingParts.length === 1
        ? `Still needed: ${missingParts[0] === "video" ? "video file" : ".srt telemetry file"}.`
        : "";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !video || !srt) return;
    const parsed = manualInputsToPayload(manualHeight, manualAngle);
    if (!parsed.ok) {
      setManualParseError(parsed.message);
      return;
    }
    setManualParseError(null);
    const hasAny =
      parsed.value.manual_height_above_takeoff_m !== undefined ||
      parsed.value.manual_camera_angle_deg !== undefined;
    await onLoad(video, srt, hasAny ? parsed.value : undefined, dat ?? undefined);
  };

  const readinessNote = (() => {
    const parts: string[] = [];
    if (missingParts.length) parts.push(missingText);
    if (video && videoErr) parts.push(`Video — ${videoErr}`);
    if (srt && srtErr) parts.push(`Telemetry — ${srtErr}`);
    return parts.join(" ");
  })();

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal
        aria-labelledby={`${reactId}-title`}
        className="card modal-dialog modal-dialog-wide modal-dialog-upload"
      >
        <header className="modal-dialog-head">
          <div className="section-kicker">Load flight</div>
          <h2 id={`${reactId}-title`} style={{ margin: "4px 0 0", fontSize: "20px" }}>
            Pair recording + telemetry
          </h2>
        </header>

        {hasExistingSession ? (
          <p className="modal-replace-banner" style={{ flexShrink: 0 }}>
            Loading new data will replace the current flight in the viewer. Existing playback and map state will refresh.
          </p>
        ) : null}

        <form className="modal-upload-form upload-form" onSubmit={submit}>
          <div className="modal-body-scroll">
            <CombinedFlightDropZone disabled={loading} onPickFiles={applyBundle} />

            {dropHint ? (
              <p className="muted flight-meta-sub" role="status" style={{ margin: 0 }}>
                {dropHint}
              </p>
            ) : null}

            {apiError ? (
              <p className="drop-zone-error" role="alert">
                {apiError}
              </p>
            ) : null}

            {manualParseError ? (
              <p className="drop-zone-error" role="alert">
                {manualParseError}
              </p>
            ) : null}

            {canSubmit ? (
              <p className="muted flight-meta-sub" style={{ margin: 0 }}>
                Ready to parse — press <strong>Load flight</strong> below.
              </p>
            ) : readinessNote ? (
              <p className="muted flight-meta-sub" role="status" style={{ margin: 0 }}>
                {readinessNote}
              </p>
            ) : (
              !dropHint &&
              !apiError &&
              !loading && (
                <p className="muted flight-meta-sub" style={{ margin: 0 }}>
                  Drag video + matching <strong>.srt</strong> (optional <strong>.dat</strong>) onto the zone, or browse
                  with <strong>Replace</strong>.
                </p>
              )
            )}

            <section className="manual-meta-section" aria-label="Optional manual metadata">
              <h3 className="manual-meta-title">Optional manual metadata</h3>
              <div className="manual-meta-grid">
                <div className="upload-field">
                  <label className="field-label" htmlFor={`${reactId}-manual-h`}>
                    Height above takeoff point, meters
                  </label>
                  <input
                    id={`${reactId}-manual-h`}
                    type="number"
                    inputMode="decimal"
                    step="any"
                    placeholder="119"
                    className="manual-meta-input"
                    value={manualHeight}
                    disabled={loading}
                    onChange={(e) => {
                      setManualHeight(e.target.value);
                      setManualParseError(null);
                    }}
                  />
                  <p className="muted flight-meta-sub" style={{ margin: "6px 0 0" }}>
                    Used later as fallback/validation. SRT relative altitude is preferred when available.
                  </p>
                </div>
                <div className="upload-field">
                  <label className="field-label" htmlFor={`${reactId}-manual-a`}>
                    Camera angle, degrees
                  </label>
                  <input
                    id={`${reactId}-manual-a`}
                    type="number"
                    inputMode="decimal"
                    step="any"
                    placeholder="45"
                    title="Examples: 45 or 60"
                    className="manual-meta-input"
                    value={manualAngle}
                    disabled={loading}
                    onChange={(e) => {
                      setManualAngle(e.target.value);
                      setManualParseError(null);
                    }}
                  />
                  <p className="muted flight-meta-sub" style={{ margin: "6px 0 0" }}>
                    Used later for center-point projection if the SRT does not include camera/gimbal angle.
                  </p>
                </div>
              </div>
            </section>

            <input
              ref={videoInputRef}
              id={videoInputId}
              type="file"
              className="sr-only"
              accept={VIDEO_REPLACE_ACCEPT}
              disabled={loading}
              onChange={(e) => {
                const f = e.currentTarget.files?.[0] ?? null;
                e.currentTarget.value = "";
                replaceVideoPick(f);
              }}
            />
            <input
              ref={srtInputRef}
              id={srtInputId}
              type="file"
              className="sr-only"
              accept=".srt"
              disabled={loading}
              onChange={(e) => {
                const f = e.currentTarget.files?.[0] ?? null;
                e.currentTarget.value = "";
                replaceSrtPick(f);
              }}
            />
            <input
              ref={datInputRef}
              id={datInputId}
              type="file"
              className="sr-only"
              accept=".dat,.DAT"
              disabled={loading}
              onChange={(e) => {
                const f = e.currentTarget.files?.[0] ?? null;
                e.currentTarget.value = "";
                replaceDatPick(f);
              }}
            />

            <div className="modal-file-cards">
              <SelectedFileCard
                slot="video"
                label="Video recording"
                Icon={VideoIcon}
                file={video}
                status={slotStatus(videoOk, video, videoErr)}
                error={videoErr}
                disabled={loading}
                detailLine={durationLine}
                onReplaceClick={() => videoInputRef.current?.click()}
                onRemove={() => {
                  setVideo(null);
                  setVideoErr(null);
                  setDurationSec(null);
                }}
              />
              <SelectedFileCard
                slot="telemetry"
                label="SRT telemetry"
                Icon={FileText}
                file={srt}
                status={slotStatus(srtOk, srt, srtErr)}
                error={srtErr}
                disabled={loading}
                onReplaceClick={() => srtInputRef.current?.click()}
                onRemove={() => {
                  setSrt(null);
                  setSrtErr(null);
                }}
              />
              <SelectedFileCard
                slot="flight_log"
                label="DJI flight log (optional)"
                Icon={Database}
                file={dat}
                status={datSlotStatus(
                  Boolean(dat && isAcceptedDatExtension(dat.name) && !datErr),
                  dat,
                  datErr,
                )}
                error={datErr}
                disabled={loading}
                onReplaceClick={() => datInputRef.current?.click()}
                onRemove={() => {
                  setDat(null);
                  setDatErr(null);
                }}
              />
            </div>
          </div>

          <footer className="modal-footer-sticky">
            <button type="button" className="ghost-btn" disabled={loading} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className={`primary-btn${loading ? " primary-btn--busy" : ""}`} disabled={!canSubmit} aria-busy={loading}>
              {loading ? (
                <span className="primary-btn-inner">
                  <span className="spinner spinner--inline" aria-hidden />
                  Loading flight…
                </span>
              ) : (
                "Load flight"
              )}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
