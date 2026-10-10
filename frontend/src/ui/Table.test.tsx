import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { Table, type TableColumn } from "./Table";

interface Row {
  id: string;
  name: string;
}
const ROWS: Row[] = [
  { id: "a", name: "alpha" },
  { id: "b", name: "beta" },
  { id: "c", name: "gamma" },
];
const COLUMNS: TableColumn<Row>[] = [
  { id: "name", header: "Name", cell: (row) => row.name },
  { id: "id", header: "Id", cell: (row) => row.id, shrink: true },
];

function Example({ onActivate }: { onActivate: (id: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <Table
      label="Things"
      columns={COLUMNS}
      rows={ROWS}
      rowId={(row) => row.id}
      selectedId={selected}
      onSelect={setSelected}
      onActivate={onActivate}
    />
  );
}

const row = (name: string) => screen.getByText(name).closest("tr")!;

describe("Table", () => {
  it("renders a labelled grid with column headers", () => {
    render(<Example onActivate={vi.fn()} />);
    expect(screen.getByRole("grid", { name: "Things" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").map((th) => th.textContent)).toEqual(["Name", "Id"]);
    expect(screen.getAllByRole("row")).toHaveLength(4);
  });

  it("is one tab stop; arrows, Home and End move the selection, Enter activates", async () => {
    const onActivate = vi.fn();
    render(<Example onActivate={onActivate} />);
    await userEvent.tab();
    const grid = screen.getByRole("grid");
    expect(grid).toHaveFocus();

    await userEvent.keyboard("{ArrowDown}");
    expect(row("alpha")).toHaveAttribute("aria-selected", "true");
    expect(grid).toHaveAttribute("aria-activedescendant", row("alpha").id);
    await userEvent.keyboard("{ArrowDown}{ArrowDown}{ArrowDown}");
    expect(row("gamma")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Home}");
    expect(row("alpha")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{End}{ArrowUp}");
    expect(row("beta")).toHaveAttribute("aria-selected", "true");

    await userEvent.keyboard("{Enter}");
    expect(onActivate).toHaveBeenCalledWith("b");
  });

  it("selects on click and activates on double-click", async () => {
    const onActivate = vi.fn();
    render(<Example onActivate={onActivate} />);
    await userEvent.click(screen.getByText("gamma"));
    expect(row("gamma")).toHaveAttribute("aria-selected", "true");
    await userEvent.dblClick(screen.getByText("alpha"));
    expect(onActivate).toHaveBeenCalledWith("a");
  });

  it("does nothing on Enter without a selection", async () => {
    const onActivate = vi.fn();
    render(<Example onActivate={onActivate} />);
    screen.getByRole("grid").focus();
    await userEvent.keyboard("{Enter}");
    expect(onActivate).not.toHaveBeenCalled();
  });
});

describe("Table row extras", () => {
  it("adds row classes and reports the hovered row", async () => {
    const onRowHover = vi.fn();
    render(
      <Table
        label="Things"
        columns={COLUMNS}
        rows={ROWS}
        rowId={(row) => row.id}
        rowClassName={(row) => (row.id === "b" ? "special" : undefined)}
        onRowHover={onRowHover}
      />,
    );
    expect(row("beta")).toHaveClass("special");
    expect(row("alpha")).not.toHaveClass("special");
    await userEvent.hover(screen.getByText("gamma"));
    expect(onRowHover).toHaveBeenLastCalledWith("c");
    await userEvent.unhover(screen.getByText("gamma"));
    expect(onRowHover).toHaveBeenLastCalledWith(null);
  });
});
