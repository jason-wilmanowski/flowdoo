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

const tree = () => screen.findByRole("tree", { name: "Calls" });
const details = () => screen.getByRole("region", { name: "Step details" });
const selectedItem = () =>
  within(screen.getByRole("tree", { name: "Calls" }))
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
    expect(within(details()).getByRole("heading", { level: 2 })).toHaveTextContent(
      "sale.order.action_confirm",
    );
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
    expect(details()).toHaveTextContent("Modulesale_stock");
    expect(details()).toHaveTextContent("MRO0 (most derived)");
    expect(details()).toHaveTextContent("Supercalls super()");

    await userEvent.click(within(details()).getByText("Call path"));
    const path = within(details()).getByRole("list", { name: "Call path" });
    expect(within(path).getAllByRole("button")).toHaveLength(2);
  });

  it("shows what a call changed including its children and jumps to the writer", async () => {
    renderTrace(MEDIUM);
    await tree();
    const order = within(details()).getByRole("region", { name: "sale.order 7" });
    expect(order).toHaveTextContent("state");
    expect(order).toHaveTextContent("delivery_count");
    const move = within(details()).getByRole("region", { name: "stock.move 301" });
    expect(within(move).getByText("created")).toBeInTheDocument();

    await userEvent.click(within(order).getAllByRole("button", { name: "written in step 3" })[0]!);
    expect(screen.getByText("Step 3 of 10")).toBeInTheDocument();
  });

  it("says when a call changed nothing", async () => {
    renderTrace(MEDIUM);
    await tree();
    await userEvent.keyboard("{ArrowRight}");
    expect(details()).toHaveTextContent("No field changed in this call or in the calls it made.");
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
    const summary = () =>
      screen.getByText(
        (_, element) => element?.tagName === "P" && /changes applied/.test(element.textContent),
      );
    expect(summary()).toHaveTextContent("0 of 5 changes applied up to step 1.");
    const upcoming = screen.getByRole("button", {
      name: /^Step 7: sale.order 7 delivery_count 0 to 1/,
    });
    expect(upcoming).toHaveAccessibleName(/not applied yet$/);
    await userEvent.click(upcoming);
    expect(screen.getByText("Step 7 of 10")).toBeInTheDocument();
    expect(summary()).toHaveTextContent("5 of 5 changes applied up to step 7.");
    expect(screen.getByRole("button", { name: /^Step 7:/ })).toHaveAttribute(
      "aria-current",
      "step",
    );
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

  it("opens the 879-step recording with only the relevant calls unfolded", async () => {
    renderTrace(RECORDED);
    const initial = within(await tree()).getAllByRole("treeitem").length;
    expect(initial).toBeLessThan(200);
    await userEvent.click(screen.getByRole("button", { name: "Expand all" }));
    const all = within(screen.getByRole("tree")).getAllByRole("treeitem").length;
    expect(all).toBeGreaterThan(initial);
    await userEvent.click(screen.getByRole("button", { name: "Relevant only" }));
    expect(within(screen.getByRole("tree")).getAllByRole("treeitem")).toHaveLength(initial);
  });

  it("marks the folded call that holds the replay position without unfolding it", async () => {
    renderTrace(MEDIUM);
    await tree();
    await userEvent.keyboard("{End}");
    expect(screen.getByText("Step 10 of 10")).toBeInTheDocument();
    expect(selectedItem()).toHaveTextContent("_send_order_confirmation_mail");
    expect(selectedItem()).toHaveAttribute("aria-expanded", "false");
    expect(within(details()).getByRole("heading", { level: 2 })).toHaveTextContent(
      "mail.mail.send",
    );
  });

  it("shows a super() chain as one call and lists its implementations", async () => {
    renderTrace(MEDIUM);
    const row = within(await tree())
      .getAllByRole("treeitem")
      .find((li) => li.textContent.includes("sale_stock → sale"));
    expect(row).toHaveTextContent("_action_confirm");
    await userEvent.click(row!);
    const chain = within(details()).getByRole("list", { name: "Implementation chain" });
    const layers = within(chain).getAllByRole("button");
    expect(layers.map((b) => b.textContent)).toEqual([
      expect.stringMatching(/0sale_stockcalls super\(\)/),
      expect.stringMatching(/1saleno super\(\)/),
    ]);
    // sale is the base implementation of _action_confirm: not calling super() is normal
    expect(details()).not.toHaveTextContent("does not call super()");

    // the open chain shows its implementations as a stack in the tree
    const items = within(screen.getByRole("tree")).getAllByRole("treeitem");
    const layerRows = items.filter((li) => li.getAttribute("aria-level") === "3");
    expect(layerRows.slice(0, 2).map((li) => li.textContent)).toEqual([
      expect.stringMatching(/^0sale_stockcalls super\(\)/),
      expect.stringMatching(/^1saleno super\(\)/),
    ]);

    // a layer in the details jumps to its step and selects its row in the tree
    await userEvent.click(layers[1]!);
    expect(screen.getByText("Step 8 of 10")).toBeInTheDocument();
    expect(selectedItem()).toHaveTextContent(/^1saleno super\(\)/);
  });
});
