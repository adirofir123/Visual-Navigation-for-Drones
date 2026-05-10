const VIDEO_EXTENSIONS = new Set([
  ".mp4",
  ".mov",
  ".m4v",
  ".webm",
  ".mkv",
  ".avi",
  ".wmv",
  ".mpg",
  ".mpeg",
  ".3gp",
]);

export function fileExtensionLower(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

/** True if the file looks like a common drone/web video (extension or MIME). */
export function isValidVideoFile(file: File): boolean {
  const ext = fileExtensionLower(file.name);
  if (ext && VIDEO_EXTENSIONS.has(ext)) return true;
  if (file.type.startsWith("video/")) return true;
  return false;
}

/** DJI SRT telemetry must use a .srt file. */
export function isValidSrtFile(file: File): boolean {
  return fileExtensionLower(file.name) === ".srt";
}

export function videoTypeLabel(file: File): string {
  if (file.type && file.type.startsWith("video/")) return file.type;
  const ext = fileExtensionLower(file.name);
  return ext ? ext.replace(".", "").toUpperCase() + " video" : "Video";
}
