import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { Tree, type TreeRow } from "./Tree";

// a ─ b ─ c
//   └ d
const CHILDREN: Record<string, string[]> = { a: ["b", "d"], b: ["c"] };
const PARENT: Record<string, string | null> = { a: null, b: "a", c: "b", d: "a" };

function rowsOf(collapsed: Set<string>): TreeRow[] {
  const rows: TreeRow[] = [];
  const walk = (id: string, depth: number) => {
    const kids = CHILDREN[id] ?? [];
    const expanded = !collapsed.has(id);
    rows.push({ id, depth, parentId: PARENT[id] ?? null, hasChildren: kids.length > 0, expanded });
    if (expanded) for (const kid of kids) walk(kid, depth + 1);
  };
  walk("a", 0);
  return rows;
}

function Example() {
  const [selected, setSelected] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(new Set<string>());
  return (
    <Tree
      label="Calls"
      rows={rowsOf(collapsed)}
      renderRow={(id) => `step ${id}`}
      selectedId={selected}
      onSelect={setSelected}
      onToggle={(id, expanded) => {
        setCollapsed((current) => {
          const next = new Set(current);
          if (expanded) next.delete(id);
          else next.add(id);
          return next;
        });
      }}
    />
  );
}

const item = (id: string) => screen.getByText(`step ${id}`).closest("li")!;

describe("Tree", () => {
  it("exposes tree roles with levels and expanded state", () => {
    render(<Example />);
    expect(screen.getByRole("tree", { name: "Calls" })).toBeInTheDocument();
    expect(screen.getAllByRole("treeitem")).toHaveLength(4);
    expect(item("c")).toHaveAttribute("aria-level", "3");
    expect(item("a")).toHaveAttribute("aria-expanded", "true");
    expect(item("c")).not.toHaveAttribute("aria-expanded");
  });

  it("follows the tree keyboard pattern", async () => {
    render(<Example />);
    await userEvent.tab();
    expect(screen.getByRole("tree")).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(item("a")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowRight}");
    expect(item("b")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowLeft}");
    expect(item("b")).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("step c")).not.toBeInTheDocument();
    await userEvent.keyboard("{ArrowLeft}");
    expect(item("a")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{End}");
    expect(item("d")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Home}{ArrowLeft}");
    expect(item("a")).toHaveAttribute("aria-expanded", "false");
    expect(screen.getAllByRole("treeitem")).toHaveLength(1);
  });

  it("selects on click and toggles with the chevron", async () => {
    render(<Example />);
    await userEvent.click(screen.getByText("step d"));
    expect(item("d")).toHaveAttribute("aria-selected", "true");
    await userEvent.click(item("b").querySelector("svg")!.parentElement!);
    expect(item("b")).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps handled keys away from global listeners", async () => {
    const global = vi.fn((event: KeyboardEvent) => event.defaultPrevented);
    document.addEventListener("keydown", global);
    render(<Example />);
    screen.getByRole("tree").focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(global).toHaveReturnedWith(true);
    document.removeEventListener("keydown", global);
  });
});
