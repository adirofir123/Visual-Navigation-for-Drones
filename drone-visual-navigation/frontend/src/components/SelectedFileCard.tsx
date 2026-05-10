import type { LucideIcon } from "lucide-react";

import { formatFileSize } from "../utils/formatFileSize";

export type FileSlotStatus = "missing" | "selected" | "valid" | "invalid" | "optional";

interface Props {
  slot: "video" | "telemetry" | "flight_log";
  label: string;
  Icon: LucideIcon;
  file: File | null;
  status: FileSlotStatus;
  error?: string | null;
  disabled?: boolean;
  /** Extra metadata line under size (e.g. duration). */
  detailLine?: string | null;
  onReplaceClick: () => void;
  onRemove: () => void;
}

function statusChip(status: FileSlotStatus): { className: string; text: string } {
  switch (status) {
    case "missing":
      return { className: "chip chip-neutral", text: "Missing" };
    case "optional":
      return { className: "chip chip-neutral", text: "Optional" };
    case "selected":
      return { className: "chip chip-warn", text: "Pending" };
    case "valid":
      return { className: "chip chip-ok", text: "Valid" };
    case "invalid":
      return { className: "chip chip-warn", text: "Invalid" };
    default:
      return { className: "chip chip-neutral", text: "—" };
  }
}

export function SelectedFileCard({
  slot: _slot,
  label,
  Icon,
  file,
  status,
  error,
  disabled,
  detailLine,
  onReplaceClick,
  onRemove,
}: Props) {
  const chip = statusChip(status);

  return (
    <article className="card" aria-label={`${label} slot`}>
      <div className="section-head compact">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div className="drop-zone-icon-wrap" aria-hidden>
            <Icon className="drop-zone-icon" strokeWidth={1.75} />
          </div>
          <div>
            <div className="section-kicker">{label}</div>
            <h2 style={{ margin: "4px 0 0", fontSize: "16px" }}>{file?.name ?? "No file"}</h2>
          </div>
        </div>
        <span className={`${chip.className} flight-meta-sub`}>{chip.text}</span>
      </div>
      {file ? (
        <dl className="drop-zone-meta" style={{ marginTop: "8px" }}>
          <div>
            <dt>Size</dt>
            <dd>{formatFileSize(file.size)}</dd>
          </div>
          {detailLine ? (
            <div className="drop-zone-meta-span">
              <dt>Notes</dt>
              <dd>{detailLine}</dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="muted flight-meta-sub" style={{ margin: "10px 0 0" }}>
          Add via the drop zone above or Replace to browse for a file.
        </p>
      )}
      {error ? (
        <p className="drop-zone-error" role="alert" style={{ marginTop: "10px" }}>
          {error}
        </p>
      ) : null}
      <div className="file-card-actions">
        <button type="button" className="ghost-btn ghost-btn--small" disabled={disabled} onClick={onReplaceClick}>
          Replace
        </button>
        <button type="button" className="link-btn" disabled={disabled || !file} onClick={onRemove}>
          Remove
        </button>
      </div>
    </article>
  );
}
