import type { LucideIcon } from "lucide-react";
import {
  useCallback,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";

import { formatFileSize } from "../utils/formatFileSize";
import { videoTypeLabel } from "../utils/fileValidation";

export type DropZoneVariant = "hero" | "compact";

interface Props {
  inputId: string;
  /** Visible title, e.g. "Drone video". */
  label: string;
  /** Short accept summary for the empty state, e.g. "MP4, MOV, WebM…". */
  acceptHint: string;
  /** Native `accept` string for the hidden file input. */
  accept: string;
  Icon: LucideIcon;
  file: File | null;
  onFile: (file: File | null) => void;
  disabled?: boolean;
  variant?: DropZoneVariant;
  error?: string | null;
  /** When true, shows MIME/type line using video heuristics. */
  fileKind: "video" | "srt";
  /** Optional extra line under metadata (e.g. parsed duration). */
  detailLine?: string | null;
}

/**
 * Accessible drop / click target with a visually hidden `<input type="file">`.
 * Handles drag-over highlight, validation errors from parent, and replace flow.
 */
export function FileDropZone({
  inputId,
  label,
  acceptHint,
  accept,
  Icon,
  file,
  onFile,
  disabled,
  variant = "hero",
  error,
  fileKind,
  detailLine,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const pickFile = useCallback(
    (next: File | null) => {
      if (disabled) return;
      onFile(next);
    },
    [disabled, onFile],
  );

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.currentTarget.files?.[0] ?? null;
    pickFile(f);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f) pickFile(f);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const rootClass =
    variant === "hero"
      ? `drop-zone drop-zone--hero${dragOver ? " drop-zone--drag" : ""}${error ? " drop-zone--error" : ""}${file && !error ? " drop-zone--ready" : ""}`
      : `drop-zone drop-zone--compact${dragOver ? " drop-zone--drag" : ""}${error ? " drop-zone--error" : ""}${file && !error ? " drop-zone--ready" : ""}`;

  const typeLine =
    file && !error ? (fileKind === "video" ? videoTypeLabel(file) : "SRT telemetry") : null;

  return (
    <div
      className={rootClass}
      onDragEnter={(e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={(e: DragEvent<HTMLDivElement>) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false);
      }}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        id={inputId}
        className="sr-only"
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={onInputChange}
        aria-label={label}
      />

      <label htmlFor={inputId} className="drop-zone-surface">
        <div className="drop-zone-icon-wrap" aria-hidden>
          <Icon className="drop-zone-icon" strokeWidth={1.75} />
        </div>
        <div className="drop-zone-copy">
          <div className="drop-zone-title-row">
            <span className="drop-zone-label">{label}</span>
            {file && !error ? (
              <span className="chip chip-ok drop-zone-ready-pill" aria-hidden>
                Ready
              </span>
            ) : null}
          </div>
          <p className="drop-zone-hint muted">{acceptHint}</p>
          {file && !error ? (
            <dl className="drop-zone-meta">
              <div>
                <dt>File</dt>
                <dd title={file.name}>{file.name}</dd>
              </div>
              <div>
                <dt>Size</dt>
                <dd>{formatFileSize(file.size)}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{typeLine}</dd>
              </div>
              {detailLine ? (
                <div className="drop-zone-meta-span">
                  <dt>Duration</dt>
                  <dd>{detailLine}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}
          {error ? (
            <p className="drop-zone-error" role="alert">
              {error}
            </p>
          ) : null}
          <span className="drop-zone-cta">
            {file ? "Click or drop to replace file" : "Click to browse or drop a file here"}
          </span>
        </div>
      </label>
      {file ? (
        <div className="drop-zone-toolbar">
          <button
            type="button"
            className="link-btn"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            Replace file
          </button>
          <button
            type="button"
            className="ghost-btn ghost-btn--small"
            disabled={disabled}
            onClick={() => {
              if (inputRef.current) inputRef.current.value = "";
              pickFile(null);
            }}
          >
            Remove
          </button>
        </div>
      ) : null}
    </div>
  );
}
