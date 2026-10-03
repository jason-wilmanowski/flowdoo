import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SplitPanel, type SidePane } from "./SplitPanel";

const pane = (label: string): SidePane => ({
  label,
  content: <p>{label} content</p>,
  defaultWidth: "300px",
  minWidth: 200,
  maxWidth: 400,
});

function renderSplit() {
  return render(
    <SplitPanel id="test" start={pane("Steps")} end={pane("Details")}>
      <p>main</p>
    </SplitPanel>,
  );
}

const handle = (label: string) => screen.getByRole("separator", { name: `Resize ${label}` });
const width = (label: string) => screen.getByRole("region", { name: label }).style.width;

describe("SplitPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders panes, main area and focusable separators", async () => {
    renderSplit();
    expect(screen.getByRole("main")).toHaveTextContent("main");
    expect(width("Steps")).toBe("300px");
    await userEvent.tab();
    expect(handle("Steps")).toHaveFocus();
    expect(handle("Steps")).toHaveAttribute("aria-valuemin", "200");
    expect(handle("Steps")).toHaveAttribute("aria-valuemax", "400");
  });

  it("resizes with Home, End and arrow keys within the limits", async () => {
    renderSplit();
    handle("Steps").focus();
    await userEvent.keyboard("{Home}");
    expect(width("Steps")).toBe("200px");
    await userEvent.keyboard("{ArrowLeft}");
    expect(width("Steps")).toBe("200px");
    await userEvent.keyboard("{ArrowRight}");
    expect(width("Steps")).toBe("216px");
    await userEvent.keyboard("{End}");
    expect(width("Steps")).toBe("400px");
  });

  it("mirrors arrow direction for the end pane", async () => {
    renderSplit();
    handle("Details").focus();
    await userEvent.keyboard("{Home}{ArrowLeft}");
    expect(width("Details")).toBe("216px");
  });

  it("collapses with Enter and double-click", async () => {
    renderSplit();
    handle("Steps").focus();
    await userEvent.keyboard("{Enter}");
    expect(handle("Steps")).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "Steps" })).not.toBeInTheDocument();
    fireEvent.doubleClick(handle("Steps"));
    expect(handle("Steps")).toHaveAttribute("aria-expanded", "true");
  });

  it("restores the stored layout", async () => {
    const { unmount } = renderSplit();
    handle("Steps").focus();
    await userEvent.keyboard("{End}");
    unmount();
    renderSplit();
    expect(width("Steps")).toBe("400px");
  });
});
