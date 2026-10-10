import type { ModelDetail, ModelSummary } from "@/api/types";
import type { TracePayload } from "@/generated/trace";

/**
 * The traces in shared/fixtures. Loaded on demand as text and parsed once: the recorded
 * trace is ~470 KB and must not be type-checked or bundled into the API mode.
 */
export const FIXTURE_FILES = {
  "trace-small": () => import("@shared/fixtures/trace-small.json?raw"),
  "trace-medium": () => import("@shared/fixtures/trace-medium.json?raw"),
  "trace-error": () => import("@shared/fixtures/trace-error.json?raw"),
  "recorded-sale-order-action-confirm": () =>
    import("@shared/fixtures/recorded-sale-order-action-confirm.json?raw"),
} as const;

export type FixtureName = keyof typeof FIXTURE_FILES;

export const FIXTURE_NAMES = Object.keys(FIXTURE_FILES) as FixtureName[];

/** The recorded registry (shared/fixtures/registry-*.json): all models, some in detail. */
export interface RegistryFixture {
  odoo_version: string;
  modules: string[];
  models: ModelSummary[];
  details: Record<string, ModelDetail>;
}

export async function loadRegistryFixture(): Promise<RegistryFixture> {
  const module = await import("@shared/fixtures/registry-sale-stock-account.json?raw");
  return JSON.parse(module.default) as RegistryFixture;
}

export async function loadFixture(name: FixtureName): Promise<TracePayload> {
  const module = await FIXTURE_FILES[name]();
  return JSON.parse(module.default) as TracePayload;
}
