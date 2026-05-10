import { UploadCloud } from "lucide-react";
import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react";

const INPUT_ACCEPT =
  ".mp4,.mov,.avi,.mkv,.webm,.srt,.DAT,.dat,video/mp4,video/quicktime,video/webm,video/x-msvideo,video/x-matroska";

interface Props {
  disabled?: boolean;
  onPickFiles: (files: File[]) => void;
}

export function CombinedFlightDropZone({ disabled, onPickFiles }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = useCallback(
    (list: FileList | null | undefined) => {
      if (disabled || !list?.length) return;
      onPickFiles(Array.from(list));
    },
    [disabled, onPickFiles],
  );

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    pick(e.currentTarget.files);
    e.currentTarget.value = "";
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    pick(e.dataTransfer.files);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const rootCls = `combined-drop${dragOver ? " combined-drop--drag" : ""}`;

  return (
    <section className={rootCls}>
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        accept={INPUT_ACCEPT}
        multiple
        disabled={disabled}
        onChange={onInputChange}
        aria-label="Browse for drone video and SRT telemetry"
      />
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        aria-label="Drag and drop drone video plus SRT, or activate to browse"
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false);
        }}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onClick={() => {
          if (!disabled) inputRef.current?.click();
        }}
      >
        <UploadCloud size={36} strokeWidth={1.5} style={{ color: "#7dd3fc", marginBottom: "10px" }} aria-hidden />
        <p className="combined-drop-title">Drop video + SRT here</p>
        <p className="combined-drop-hint">
          Accepted: MP4, MOV, AVI, MKV, WEBM • one <strong>.srt</strong> telemetry file • optional DJI{" "}
          <strong>.dat</strong> flight log.
        </p>
        <p className="combined-drop-cta">Click to browse from disk</p>
      </div>
    </section>
  );
}
