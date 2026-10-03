// @vitest-environment node
// The fixtures and the traces fixture mode produces must follow the trace schema.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import { FIXTURE_NAMES, loadFixture } from "@/datasource/fixtures/catalog";
import { createFixtureDataSource } from "@/datasource/fixtures/fixtureDataSource";

const schemaPath = fileURLToPath(
  new URL("../../../../shared/schemas/trace.schema.json", import.meta.url),
);
const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(JSON.parse(readFileSync(schemaPath, "utf8")) as object);

function errorsOf(payload: unknown): string {
  return validate(payload) ? "" : ajv.errorsText(validate.errors);
}

describe("fixtures follow the trace schema", () => {
  it.each(FIXTURE_NAMES)("%s", async (name) => {
    expect(errorsOf(await loadFixture(name))).toBe("");
  });

  it("a trace started in fixture mode does too", async () => {
    const source = createFixtureDataSource({ delayMs: 0 });

    const trace = await source.startTrace({
      entrypoint_model: "sale.order",
      entrypoint_method: "action_confirm",
      record_ids: [42],
      kwargs: { note: "fixture" },
      dry_run: true,
    });

    expect(errorsOf(trace.payload)).toBe("");
  });
});
