import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppProviders } from "@/app/AppProviders";
import { AppRoutes } from "@/app/AppRoutes";
import { createFixtureDataSource } from "@/datasource";

const MEDIUM = "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e02";
const ERROR = "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e03";
const FAILED_RECORDING = "00000000-0000-4000-8000-0000000000f1";
const RECORDED = "22585514-6fae-4c9b-96ee-3f431ba1035a";

function renderTrace(id: string) {
  render(
    <MemoryRouter initialEntries={[`/traces/${id}`]}>
      <AppProviders
        initialDataSource="fixtures"
        createSource={() => createFixtureDataSource({ delayMs: 0 })}
      >
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
}

const tree = () => screen.findByRole("tree", { name: "Steps" });
const details = () => screen.getByRole("region", { name: "Step details" });
const selectedItem = () =>
  within(screen.getByRole("tree", { name: "Steps" }))
    .getAllByRole("treeitem")
    .find((item) => item.getAttribute("aria-selected") === "true");

describe("trace view", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("shows header, step tree, details and replay controls", async () => {
    renderTrace(MEDIUM);
    await tree();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "sale.order.action_confirm",
    );
    expect(screen.getByText("succeeded")).toBeInTheDocument();
    expect(selectedItem()).toHaveTextContent("sale.order.action_confirm");
    expect(within(details()).getByRole("tab", { name: "Changes (0)" })).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 10")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Models of the run: 4 models/ })).toBeInTheDocument();
  });

  it("steps with the arrow keys and shows the field changes of the step", async () => {
    renderTrace(MEDIUM);
    await tree();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(screen.getByText("Step 3 of 10")).toBeInTheDocument();
    expect(selectedItem()).toHaveTextContent("sale.order.write");
    const changes = within(details()).getByRole("region", { name: "sale.order 7" });
    expect(within(changes).getByText("state")).toBeInTheDocument();
    expect(within(changes).getByText("draft")).toBeInTheDocument();
    expect(within(changes).getByText("sale")).toBeInTheDocument();

    await userEvent.keyboard("{End}");
    expect(screen.getByText("Step 10 of 10")).toBeInTheDocument();
    await userEvent.keyboard("{Home}{ArrowLeft}");
    expect(screen.getByText("Step 1 of 10")).toBeInTheDocument();
  });

  it("selects a step in the tree and shows implementation facts", async () => {
    renderTrace(MEDIUM);
    const item = within(await tree())
      .getAllByRole("treeitem")
      .find((li) => /_action_confirm/.test(li.textContent) && /sale_stock/.test(li.textContent));
    await userEvent.click(item!);
    await userEvent.click(within(details()).getByRole("tab", { name: "Call" }));
    const facts = within(details()).getByRole("tabpanel");
    expect(facts).toHaveTextContent("sale_stock");
    expect(facts).toHaveTextContent("MRO position0 (most derived)");
    expect(facts).toHaveTextContent("Calls super()yes");

    await userEvent.click(within(details()).getByRole("tab", { name: "Path" }));
    const path = within(details()).getByRole("list", { name: "Call path" });
    expect(within(path).getAllByRole("button")).toHaveLength(2);
  });

  it("plays and pauses with Space", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    renderTrace(MEDIUM);
    await tree();
    await userEvent.keyboard(" ");
    expect(screen.getByRole("button", { name: "Pause (Space)" })).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByText("Step 3 of 10")).toBeInTheDocument();
    await userEvent.keyboard(" ");
    expect(screen.getByRole("button", { name: "Play (Space)" })).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("lists every change over time and jumps to its step", async () => {
    renderTrace(MEDIUM);
    await tree();
    await userEvent.click(screen.getByRole("tab", { name: "Changes over time" }));
    expect(screen.getByText(/0 of 5 changes happened/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^#7/ }));
    expect(screen.getByText("Step 7 of 10")).toBeInTheDocument();
    expect(screen.getByText(/5 of 5 changes happened/)).toBeInTheDocument();
  });

  it("lists the replay keys in the shortcut help", async () => {
    renderTrace(MEDIUM);
    await tree();
    await userEvent.keyboard("?");
    const dialog = await screen.findByRole("dialog", { name: "Keyboard shortcuts" });
    expect(within(dialog).getByText("Play or pause")).toBeInTheDocument();
    expect(within(dialog).getByText("Previous step")).toBeInTheDocument();
  });

  it("shows the Odoo exception and marks the failed step", async () => {
    renderTrace(ERROR);
    await tree();
    expect(screen.getByText(/Odoo raised odoo.exceptions.UserError/)).toBeInTheDocument();
    expect(within(screen.getByRole("tree")).getByText("error")).toBeInTheDocument();
  });

  it("explains a failed recording and offers to run it again", async () => {
    renderTrace(FAILED_RECORDING);
    expect(await screen.findByText(/The recording failed/)).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: /Run again/ })[0]!);
    const dialog = await screen.findByRole("dialog", { name: "Start a trace" });
    expect(within(dialog).getByRole("textbox", { name: "Model" })).toHaveValue("account.move");
  });

  it("opens the 879-step recording with collapsed depth", async () => {
    renderTrace(RECORDED);
    const items = within(await tree()).getAllByRole("treeitem");
    expect(items.length).toBeLessThan(879);
    await userEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(within(screen.getByRole("tree")).getAllByRole("treeitem")).toHaveLength(879);
  });
});
