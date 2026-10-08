import {
  addParameter,
  jsonFromPythonDefault,
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

describe("adding parameters to kwargs", () => {
  it("converts Python defaults to JSON", () => {
    expect(jsonFromPythonDefault("None")).toBeNull();
    expect(jsonFromPythonDefault("True")).toBe(true);
    expect(jsonFromPythonDefault("False")).toBe(false);
    expect(jsonFromPythonDefault("3")).toBe(3);
    expect(jsonFromPythonDefault("'notification'")).toBe("notification");
    expect(jsonFromPythonDefault("{}")).toEqual({});
    expect(jsonFromPythonDefault("SomeConstant")).toBeNull();
  });

  it("adds a parameter and keeps what is there", () => {
    expect(addParameter("", "vals", true, null)).toEqual({ text: '{\n  "vals": null\n}' });
    const result = addParameter('{"res_id": 2}', "force_send", false, "False");
    expect(result).toEqual({ text: '{\n  "res_id": 2,\n  "force_send": false\n}' });
  });

  it("leaves existing parameters and invalid text alone", () => {
    expect(addParameter('{"res_id": 2}', "res_id", true, null)).toEqual({ text: '{"res_id": 2}' });
    expect(addParameter("{", "x", true, null)).toEqual({
      error: expect.stringMatching(/^Not valid JSON/) as unknown,
    });
  });
});
