import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Copy } from "lucide-react";

import { Badge } from "./Badge";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { IconButton } from "./IconButton";
import { Kbd } from "./Kbd";
import { Skeleton } from "./Skeleton";
import { Spinner } from "./Spinner";
import { TooltipProvider } from "./Tooltip";

describe("Button", () => {
  it("is a focusable type=button that reacts to keyboard activation", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Reload</Button>);
    const button = screen.getByRole("button", { name: "Reload" });
    expect(button).toHaveAttribute("type", "button");

    await userEvent.tab();
    expect(button).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("is disabled and busy while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Recording
      </Button>,
    );
    const button = screen.getByRole("button", { name: /Recording/ });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status")).toBeInTheDocument();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is skipped by tab when disabled", async () => {
    render(
      <>
        <Button disabled>Off</Button>
        <Button>On</Button>
      </>,
    );
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "On" })).toHaveFocus();
  });
});

describe("IconButton", () => {
  it("has the label as accessible name and shows it as tooltip on focus", async () => {
    render(
      <TooltipProvider>
        <IconButton icon={Copy} label="Copy value" />
      </TooltipProvider>,
    );
    const button = screen.getByRole("button", { name: "Copy value" });
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Copy value");
  });

  it("closes the tooltip with Escape", async () => {
    render(
      <TooltipProvider>
        <IconButton icon={Copy} label="Copy value" />
      </TooltipProvider>,
    );
    await userEvent.tab();
    await screen.findByRole("tooltip");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("renders without tooltip when disabled via prop", () => {
    render(<IconButton icon={Copy} label="Copy value" tooltip={false} />);
    expect(screen.getByRole("button", { name: "Copy value" })).toBeInTheDocument();
  });
});

describe("Badge, Kbd, Spinner, Skeleton, EmptyState", () => {
  it("renders badge text with decorative icon only", () => {
    render(<Badge tone="danger">failed</Badge>);
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("renders keys as kbd", () => {
    render(<Kbd>Space</Kbd>);
    expect(screen.getByText("Space").tagName).toBe("KBD");
  });

  it("announces loading with or without visible label", () => {
    const { rerender } = render(<Spinner label="Loading trace" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading trace");
    rerender(<Spinner />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("renders skeleton rows behind a labelled status", () => {
    const { container } = render(<Skeleton rows={4} label="Loading traces" />);
    expect(screen.getByRole("status", { name: "Loading traces" })).toBeInTheDocument();
    expect(container.querySelectorAll("[aria-hidden='true']")).toHaveLength(4);
  });

  it("uses alert only for the danger tone", () => {
    const { rerender } = render(<EmptyState message="No traces yet." />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    rerender(
      <EmptyState tone="danger" message="API unreachable." action={<Button>Retry</Button>} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("API unreachable.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
