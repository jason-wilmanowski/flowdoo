import { formatDateTime, formatDuration, formatSpan, shortId } from "./format";

describe("format", () => {
  it("formats local date and time", () => {
    const local = new Date(2026, 9, 3, 7, 5, 9).toISOString();
    expect(formatDateTime(local)).toBe("2026-10-03 07:05:09");
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("not a date")).toBe("not a date");
  });

  it("formats durations", () => {
    expect(formatDuration(12.4)).toBe("12 ms");
    expect(formatDuration(1430)).toBe("1.4 s");
    expect(formatDuration(125_000)).toBe("2 min 5 s");
  });

  it("formats the span between two timestamps", () => {
    expect(formatSpan("2026-10-03T11:58:00Z", "2026-10-03T11:58:00.120Z")).toBe("120 ms");
    expect(formatSpan("2026-10-03T11:58:00Z", null)).toBe("—");
    expect(formatSpan("2026-10-03T11:58:01Z", "2026-10-03T11:58:00Z")).toBe("—");
  });

  it("shortens uuids", () => {
    expect(shortId("00000000-0000-4000-8000-0000000000f1")).toBe("00000000");
  });
});
