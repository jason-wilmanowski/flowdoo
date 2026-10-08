import {
  argumentsToSend,
  kwargsTemplate,
  REQUIRED,
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

describe("arguments template", () => {
  const PARAMETERS = [
    { name: "res_id", kind: "positional_or_keyword", required: true, default: null },
    { name: "force_send", kind: "positional_or_keyword", required: false, default: "False" },
    { name: "email_values", kind: "positional_or_keyword", required: false, default: "None" },
    { name: "notify", kind: "keyword_only", required: false, default: "'comment'" },
    { name: "kwargs", kind: "var_keyword", required: false, default: null },
  ];

  it("lists every named argument: required ones as a placeholder, the rest with defaults", () => {
    const template = kwargsTemplate(PARAMETERS);
    expect(JSON.parse(template.text)).toEqual({
      res_id: REQUIRED,
      force_send: false,
      email_values: null,
      notify: "comment",
    });
    expect(template.defaults).toEqual({ force_send: false, email_values: null, notify: "comment" });
  });

  it("converts Python defaults to JSON (None as null)", () => {
    expect(jsonFromPythonDefault("None")).toBeNull();
    expect(jsonFromPythonDefault("True")).toBe(true);
    expect(jsonFromPythonDefault("False")).toBe(false);
    expect(jsonFromPythonDefault("3")).toBe(3);
    expect(jsonFromPythonDefault("'notification'")).toBe("notification");
    expect(jsonFromPythonDefault("{}")).toEqual({});
    expect(jsonFromPythonDefault("SomeConstant")).toBeNull();
  });

  it("is empty for methods without named arguments", () => {
    expect(kwargsTemplate([{ name: "kwargs", kind: "var_keyword", required: false }])).toEqual({
      text: "",
      defaults: {},
    });
  });

  it("refuses unfilled required arguments and drops unchanged optional ones", () => {
    const { defaults } = kwargsTemplate(PARAMETERS);
    expect(argumentsToSend({ res_id: REQUIRED, force_send: false }, defaults)).toEqual({
      error: "Fill in the required argument: res_id.",
    });
    expect(
      argumentsToSend(
        { res_id: 2, force_send: true, email_values: null, notify: "comment" },
        defaults,
      ),
    ).toEqual({ kwargs: { res_id: 2, force_send: true } });
  });

  it("builds the command with only the arguments that matter", () => {
    const template = kwargsTemplate(PARAMETERS);
    const form = {
      ...EMPTY_FORM,
      model: "mail.template",
      method: "send_mail",
      recordIds: "16",
      kwargs: template.text.replace(JSON.stringify(REQUIRED), "2"),
    };
    expect(buildCommand(form, template.defaults).command?.kwargs).toEqual({ res_id: 2 });
    expect(buildCommand({ ...form, kwargs: template.text }, template.defaults).errors?.kwargs).toBe(
      "Fill in the required argument: res_id.",
    );
  });
});
