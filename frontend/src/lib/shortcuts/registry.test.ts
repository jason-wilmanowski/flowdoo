import { groupShortcuts, isEditableTarget, shortcutFor, type Shortcut } from "./registry";

const shortcut = (id: string, key: string, group = "General"): Shortcut => ({
  id,
  key,
  label: key,
  description: id,
  group,
  run: () => undefined,
});

const event = (key: string, extra: Partial<KeyboardEvent> = {}) => ({
  key,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  target: document.body,
  ...extra,
});

describe("shortcutFor", () => {
  const all = [shortcut("help", "?"), shortcut("play", " ", "Replay")];

  it("matches by key", () => {
    expect(shortcutFor(event("?"), all)?.id).toBe("help");
    expect(shortcutFor(event(" "), all)?.id).toBe("play");
    expect(shortcutFor(event("x"), all)).toBeUndefined();
  });

  it("leaves Ctrl, Meta and Alt combinations to the browser", () => {
    expect(shortcutFor(event("?", { ctrlKey: true }), all)).toBeUndefined();
    expect(shortcutFor(event("?", { metaKey: true }), all)).toBeUndefined();
    expect(shortcutFor(event("?", { altKey: true }), all)).toBeUndefined();
  });

  it("ignores keys typed into text fields", () => {
    const input = document.createElement("input");
    expect(shortcutFor(event("?", { target: input }), all)).toBeUndefined();
  });
});

describe("activation keys", () => {
  it("leaves Space and Enter on buttons and links to the element", () => {
    const all = [shortcut("play", " "), shortcut("open", "Enter"), shortcut("next", "ArrowRight")];
    const button = document.createElement("button");
    const link = document.createElement("a");
    expect(shortcutFor(event(" ", { target: button }), all)).toBeUndefined();
    expect(shortcutFor(event("Enter", { target: link }), all)).toBeUndefined();
    expect(shortcutFor(event("ArrowRight", { target: button }), all)?.id).toBe("next");
    expect(shortcutFor(event(" "), all)?.id).toBe("play");
  });
});

describe("isEditableTarget", () => {
  it("treats every form control as editable", () => {
    const text = document.createElement("input");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    const editable = document.createElement("div");
    editable.contentEditable = "true";
    expect(isEditableTarget(text)).toBe(true);
    expect(isEditableTarget(document.createElement("textarea"))).toBe(true);
    expect(isEditableTarget(checkbox)).toBe(true);
    expect(isEditableTarget(document.createElement("select"))).toBe(true);
    expect(isEditableTarget(document.createElement("button"))).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});

describe("groupShortcuts", () => {
  it("keeps groups and entries in registration order", () => {
    const grouped = groupShortcuts([
      shortcut("a", "a", "General"),
      shortcut("b", "b", "Replay"),
      shortcut("c", "c", "General"),
    ]);
    expect(grouped.map(([group, items]) => [group, items.map((s) => s.id)])).toEqual([
      ["General", ["a", "c"]],
      ["Replay", ["b"]],
    ]);
  });
});
