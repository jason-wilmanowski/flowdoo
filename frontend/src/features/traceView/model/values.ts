import type { FieldValue } from "@/generated/trace";

/** A recorded field value as text: strings as recorded, ids as a list, empty as "null". */
export function formatValue(value: FieldValue): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return `[${value.join(", ")}]`;
  return String(value);
}
