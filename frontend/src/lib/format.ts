const pad = (value: number) => String(value).padStart(2, "0");

/** Local date and time, e.g. "2026-10-03 13:58:00"; sortable and unambiguous. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return (
    `${String(date.getFullYear())}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  );
}

/** Milliseconds as "12 ms", "1.4 s" or "2 min 5 s". */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${String(Math.round(ms))} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${String(minutes)} min ${String(seconds)} s`;
}

/** Duration between two timestamps, "—" while one is missing. */
export function formatSpan(
  start: string | null | undefined,
  end: string | null | undefined,
): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Number.isNaN(ms) || ms < 0 ? "—" : formatDuration(ms);
}

/** First block of a UUID, enough to tell traces apart in a list. */
export function shortId(id: string): string {
  return id.split("-")[0] ?? id;
}
