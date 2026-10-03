import { act, fireEvent, render as rtlRender, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TooltipProvider } from "./Tooltip";
import { CodeValue, COLLAPSE_AFTER_CHARS } from "./CodeValue";

// IconButton shows a tooltip, which needs the provider the app mounts once.
const render = (ui: React.ReactElement) => rtlRender(ui, { wrapper: TooltipProvider });

const LONG = "x".repeat(COLLAPSE_AFTER_CHARS + 1);

describe("CodeValue", () => {
  it("shows short values without an expand control", () => {
    render(<CodeValue value="sale.order" label="model" />);
    expect(screen.getByText("sale.order").tagName).toBe("CODE");
    expect(screen.queryByRole("button", { name: /Expand/ })).not.toBeInTheDocument();
  });

  it("toggles long values with aria-expanded", async () => {
    render(<CodeValue value={LONG} label="args" />);
    const expand = screen.getByRole("button", { name: "Expand args" });
    expect(expand).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(expand);
    const collapse = screen.getByRole("button", { name: "Collapse args" });
    expect(collapse).toHaveAttribute("aria-expanded", "true");
  });

  it("treats multi-line values as long", () => {
    render(<CodeValue value={"a\nb"} />);
    expect(screen.getByRole("button", { name: "Expand value" })).toBeInTheDocument();
  });

  it("copies the exact value and announces it", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<CodeValue value="draft" label="old value" />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy old value" }));
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledWith("draft");
    expect(screen.getByRole("button", { name: "Copied old value" })).toBeInTheDocument();
    expect(screen.getByText("Copied")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByRole("button", { name: "Copy old value" })).toBeInTheDocument();
    vi.useRealTimers();
  });
});
