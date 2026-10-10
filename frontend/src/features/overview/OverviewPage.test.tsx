import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppProviders } from "@/app/AppProviders";
import { AppRoutes } from "@/app/AppRoutes";
import { createFixtureDataSource } from "@/datasource";

function renderOverview(path = "/overview") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders
        initialDataSource="fixtures"
        createSource={() => createFixtureDataSource({ delayMs: 0 })}
      >
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
}

const list = () => screen.findByRole("tree", { name: "Models" });
const details = () => screen.getByRole("region", { name: "Model details" });
// the overview is a lazy route and loads the model list first
const ready = async () => {
  await list();
};

describe("overview", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("lists models by module and finds them by name or description", async () => {
    renderOverview();
    const tree = await list();
    expect(within(tree).getByText("sale")).toBeInTheDocument();
    expect(screen.getByText(/Select a model on the left/)).toBeInTheDocument();

    await userEvent.type(screen.getByRole("searchbox", { name: "Search models" }), "sales order");
    expect(within(tree).getByText("sale.order")).toBeInTheDocument();
    expect(within(tree).queryByText("res.partner")).not.toBeInTheDocument();
  });

  it("opens a model with its inheritance, fields and relations", async () => {
    renderOverview();
    await ready();
    await userEvent.type(screen.getByRole("searchbox", { name: "Search models" }), "sale.order");
    await userEvent.click(within(await list()).getByText("sale.order"));

    const panel = details();
    expect(await within(panel).findByRole("heading", { level: 2 })).toHaveTextContent("sale.order");
    expect(panel).toHaveTextContent("Defined insale");
    expect(panel).toHaveTextContent("Extended bysale_stock → sale_edi_ubl");
    expect(within(panel).getByRole("button", { name: "mail.thread" })).toBeInTheDocument();
    expect(within(panel).getByRole("grid", { name: "Fields" })).toHaveTextContent("partner_id");
    expect(screen.getByRole("region", { name: "Relations of sale.order" })).toBeInTheDocument();
  });

  it("follows a relation to the target model", async () => {
    renderOverview("/overview/sale.order");
    await ready();
    const panel = details();
    const fields = await within(panel).findByRole("grid", { name: "Fields" });
    const partnerRow = within(fields).getByText("partner_id").closest("tr")!;
    await userEvent.click(within(partnerRow).getByRole("button", { name: "res.partner" }));
    expect(await within(panel).findByRole("heading", { level: 2 })).toHaveTextContent(
      "res.partner",
    );
  });

  it("narrows the fields with the field search", async () => {
    renderOverview("/overview/sale.order");
    await ready();
    const fields = await within(details()).findByRole("grid", { name: "Fields" });
    const before = within(fields).getAllByRole("row").length;
    await userEvent.type(screen.getByRole("searchbox", { name: "Search fields" }), "partner");
    const after = within(fields).getAllByRole("row").length;
    expect(after).toBeLessThan(before);
    expect(fields).toHaveTextContent("partner_id");
  });

  it("hides wizards until asked for", async () => {
    renderOverview();
    await ready();
    const search = screen.getByRole("searchbox", { name: "Search models" });
    await userEvent.type(search, "sale.advance.payment.inv");
    expect(screen.getByText("No models match these filters.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: "Wizards" }));
    expect(within(await list()).getByText("sale.advance.payment.inv")).toBeInTheDocument();
  });

  it("explains a model without details in fixture mode", async () => {
    renderOverview("/overview/ir.cron");
    await ready();
    expect(await within(details()).findByRole("alert")).toHaveTextContent(/not in the fixtures/);
  });

  it("sets fields that link to other models apart and points their target out in the graph", async () => {
    renderOverview("/overview/sale.order");
    await ready();
    const fields = await within(details()).findByRole("grid", { name: "Fields" });
    const partnerRow = within(fields).getByText("partner_id").closest("tr")!;
    const amountRow = within(fields).getByText("amount_total").closest("tr")!;
    expect(partnerRow).toHaveClass("relationRow");
    expect(
      within(partnerRow).getByRole("img", { name: "links to res.partner" }),
    ).toBeInTheDocument();
    expect(amountRow).not.toHaveClass("relationRow");

    const graph = screen.getByRole("region", { name: "Relations of sale.order" });
    // res.partner is both a target (right) and a source (left): both are pointed out
    const partnerNodes = () =>
      within(graph)
        .getAllByText("res.partner")
        .map((text) => text.closest(".node")!);
    const highlighted = () => partnerNodes().map((node) => node.classList.contains("highlighted"));
    expect(highlighted()).toEqual([false, false]);
    await userEvent.hover(within(partnerRow).getByText("partner_id"));
    expect(highlighted()).toEqual([true, true]);
    await userEvent.unhover(within(partnerRow).getByText("partner_id"));
    expect(highlighted()).toEqual([false, false]);

    // chosen with a click it stays pointed out
    await userEvent.click(within(partnerRow).getByText("partner_id"));
    expect(highlighted()).toEqual([true, true]);
  });

  it("draws the lines without field labels", async () => {
    renderOverview("/overview/sale.order");
    await ready();
    const graph = await screen.findByRole("region", { name: "Relations of sale.order" });
    expect(within(graph).queryByText("partner_id, partner_invoice_id")).not.toBeInTheDocument();
    expect(within(graph).getAllByText(/^via /).length).toBeGreaterThan(0);
  });

  it("shows inherited models apart from relations", async () => {
    renderOverview("/overview/stock.picking");
    await ready();
    const graph = await screen.findByRole("region", { name: "Relations of stock.picking" });
    expect(within(graph).queryByText("inherited")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: "Inherits" }));
    const parent = within(graph).getByText("mail.activity.mixin").closest(".node")!;
    expect(parent).toHaveClass("inherited");
    expect(parent).toHaveTextContent("inherited");
  });
});
