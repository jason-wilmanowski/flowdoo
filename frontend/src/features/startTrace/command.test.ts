import {
  buildCommand,
  EMPTY_FORM,
  formFromCommand,
  parseJsonObject,
  parseRecordIds,
} from "./command";

describe("parseRecordIds", () => {
  it("accepts commas, spaces and semicolons", () => {
    expect(parseRecordIds("1, 2 3;4")).toEqual([1, 2, 3, 4]);
    expect(parseRecordIds("  ")).toEqual([]);
  });

  it("explains what is wrong", () => {
    expect(parseRecordIds("1, x")).toMatch(/"x" is not a record ID/);
    expect(parseRecordIds("0")).toMatch(/"0" is not a record ID/);
    expect(parseRecordIds("-3")).toMatch(/is not a record ID/);
  });
});

describe("parseJsonObject", () => {
  it("returns objects and an empty object for empty text", () => {
    expect(parseJsonObject('{"vals": {"name": "A"}}')).toEqual({ vals: { name: "A" } });
    expect(parseJsonObject("")).toEqual({});
  });

  it("rejects invalid JSON and non-objects", () => {
    expect(parseJsonObject("{")).toMatch(/^Not valid JSON/);
    expect(parseJsonObject("[1]")).toMatch(/Must be a JSON object/);
    expect(parseJsonObject("3")).toMatch(/Must be a JSON object/);
  });
});

describe("buildCommand", () => {
  const form = { ...EMPTY_FORM, model: " sale.order ", method: "action_confirm", recordIds: "1" };

  it("builds a dry-run command by default", () => {
    expect(buildCommand(form)).toEqual({
      command: {
        entrypoint_model: "sale.order",
        entrypoint_method: "action_confirm",
        record_ids: [1],
        kwargs: {},
        context: {},
        dry_run: true,
      },
    });
  });

  it("only turns off the dry run when commit is chosen", () => {
    expect(buildCommand({ ...form, commit: true }).command?.dry_run).toBe(false);
  });

  it("collects every field error", () => {
    const result = buildCommand({ ...EMPTY_FORM, recordIds: "a", kwargs: "{", context: "[]" });
    expect(Object.keys(result.errors ?? {}).sort()).toEqual([
      "context",
      "kwargs",
      "method",
      "model",
      "recordIds",
    ]);
  });

  it("rejects names that cannot be Odoo identifiers", () => {
    expect(buildCommand({ ...form, model: "sale order" }).errors?.model).toMatch(
      /not a model name/,
    );
    expect(buildCommand({ ...form, method: "a.b" }).errors?.method).toMatch(/not a method name/);
  });

  it("round-trips through the form", () => {
    const command = buildCommand({ ...form, kwargs: '{"a": 1}' }).command!;
    expect(buildCommand(formFromCommand(command)).command).toEqual(command);
  });
});
