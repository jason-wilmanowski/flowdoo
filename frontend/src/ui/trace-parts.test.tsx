import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pencil } from "lucide-react";

import { DiffRow } from "./DiffRow";
import { ReplayControls } from "./ReplayControls";
import { StepRow } from "./StepRow";
import { TooltipProvider } from "./Tooltip";

const wrapper = TooltipProvider;

describe("StepRow", () => {
  it("shows kind, name, module, changes and duration", () => {
    render(
      <StepRow
        kindIcon={Pencil}
        kindLabel="write"
        model="sale.order"
        method="write"
        module={null}
        duration="3 ms"
        changes={2}
      />,
    );
    expect(screen.getByRole("img", { name: "write" })).toBeInTheDocument();
    expect(screen.getByText("core")).toBeInTheDocument();
    expect(screen.getByText(/field changes/)).toBeInTheDocument();
    expect(screen.getByText("3 ms")).toBeInTheDocument();
  });
});

describe("DiffRow", () => {
  it("labels old and new values in text, not only by color", () => {
    render(<DiffRow field="state" oldValue="draft" newValue="sale" />, { wrapper });
    expect(screen.getByText("state").tagName).toBe("CODE");
    expect(screen.getByText("old value")).toBeInTheDocument();
    expect(screen.getByText("new value")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText("sale")).toBeInTheDocument();
  });
});

describe("ReplayControls", () => {
  const handlers = () => ({
    onFirst: vi.fn(),
    onPrevious: vi.fn(),
    onToggle: vi.fn(),
    onNext: vi.fn(),
    onLast: vi.fn(),
    onSeek: vi.fn(),
    onSpeed: vi.fn(),
  });

  it("disables what is not possible at the start and calls the handlers", async () => {
    const h = handlers();
    render(
      <ReplayControls position={0} count={10} playing={false} speed={1} speeds={[1, 2]} {...h} />,
      { wrapper },
    );
    expect(screen.getByRole("button", { name: "First step (Home)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous step (←)" })).toBeDisabled();
    expect(screen.getByText("Step 1 of 10")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Play (Space)" }));
    await userEvent.click(screen.getByRole("button", { name: "Next step (→)" }));
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Replay speed" }), "2");
    expect(h.onToggle).toHaveBeenCalled();
    expect(h.onNext).toHaveBeenCalled();
    expect(h.onSpeed).toHaveBeenCalledWith(2);
  });

  it("shows pause while playing and disables everything without steps", () => {
    const { rerender } = render(
      <ReplayControls position={9} count={10} playing speed={1} speeds={[1]} {...handlers()} />,
      { wrapper },
    );
    expect(screen.getByRole("button", { name: "Pause (Space)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Last step (End)" })).toBeDisabled();
    rerender(
      <ReplayControls
        position={null}
        count={0}
        playing={false}
        speed={1}
        speeds={[1]}
        {...handlers()}
      />,
    );
    expect(screen.getByRole("slider", { name: "Replay position" })).toBeDisabled();
    expect(screen.getByText("Step 0 of 0")).toBeInTheDocument();
  });
});
