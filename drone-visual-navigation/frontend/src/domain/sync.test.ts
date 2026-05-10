import { describe, expect, it } from "vitest";

import { findTelemetryForTime } from "./sync";
import type { TelemetryRecord } from "./telemetry";

function mk(
  index: number,
  start: number,
  end: number,
): TelemetryRecord {
  return {
    block_index: index,
    start_time_raw: "",
    end_time_raw: "",
    start_time_seconds: start,
    end_time_seconds: end,
    raw_text: "",
  };
}

describe("findTelemetryForTime", () => {
  it("picks nearest midpoint", () => {
    const recs = [mk(1, 0, 2), mk(2, 2, 4)];
    const m = findTelemetryForTime(recs, 1.0, 5);
    expect(m?.record.block_index).toBe(1);
  });

  it("returns null when gap too large", () => {
    const recs = [mk(1, 0, 1)];
    const m = findTelemetryForTime(recs, 10, 2);
    expect(m).toBeNull();
  });
});
