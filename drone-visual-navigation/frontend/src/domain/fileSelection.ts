import { fileExtensionLower, isValidSrtFile } from "../utils/fileValidation";

/** Allowed video extensions when classifying uploads (MIME hints still allowed via video validator). */
const VIDEO_EXTENSIONS = new Set([".mp4", ".mov", ".avi", ".mkv", ".webm"]);

export function isAcceptedVideoExtension(name: string): boolean {
  return VIDEO_EXTENSIONS.has(fileExtensionLower(name));
}

/** First file that looks like video by extension whitelist. Does not inspect MIME — use validator after selection. */
export function pickFirstVideoByExtension(files: File[]): File | null {
  return files.find((f) => isAcceptedVideoExtension(f.name)) ?? null;
}

export function pickFirstSrt(files: File[]): File | null {
  return files.find((f) => isValidSrtFile(f)) ?? null;
}

export function isAcceptedDatExtension(name: string): boolean {
  return /\.dat$/i.test(name);
}

/** Optional DJI / flight-record binary (.dat). */
export function pickFirstDat(files: File[]): File | null {
  return files.find((f) => isAcceptedDatExtension(f.name)) ?? null;
}

/** Files that match neither telemetry nor accepted video extensions. */
export function listUnsupportedDropped(files: File[]): File[] {
  return files.filter(
    (f) => !isAcceptedVideoExtension(f.name) && !isValidSrtFile(f) && !isAcceptedDatExtension(f.name),
  );
}
