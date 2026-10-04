import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppProviders } from "@/app/AppProviders";
import { AppRoutes } from "@/app/AppRoutes";
import { createFixtureDataSource } from "@/datasource";

function renderList() {
  render(
    <MemoryRouter initialEntries={["/traces"]}>
      <AppProviders
        initialDataSource="fixtures"
        createSource={() => createFixtureDataSource({ delayMs: 0 })}
      >
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
}

async function openDialog() {
  renderList();
  await screen.findByRole("grid", { name: "Traces" });
  await userEvent.click(screen.getByRole("button", { name: "Start trace" }));
  return screen.findByRole("dialog", { name: "Start a trace" });
}

describe("start trace dialog", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("opens with the N shortcut", async () => {
    renderList();
    await screen.findByRole("grid", { name: "Traces" });
    await userEvent.keyboard("n");
    expect(await screen.findByRole("dialog", { name: "Start a trace" })).toBeInTheDocument();
  });

  it("shows field errors instead of starting", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Record IDs" }), "x");
    await userEvent.click(within(dialog).getByRole("button", { name: "Start dry run" }));
    const alerts = within(dialog)
      .getAllByRole("alert")
      .map((a) => a.textContent);
    expect(alerts).toEqual(
      expect.arrayContaining([
        "Enter a model, e.g. sale.order.",
        "Enter a method, e.g. action_confirm.",
        expect.stringMatching(/"x" is not a record ID/),
      ]),
    );
  });

  it("looks up the method and records a dry run, then opens the trace", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Model" }), "sale.order");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Method" }), "action_confirm");
    expect(await within(dialog).findByText(/called on records/)).toBeInTheDocument();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Record IDs" }), "1");

    await userEvent.click(within(dialog).getByRole("button", { name: "Start dry run" }));
    expect(await screen.findByRole("region", { name: "Steps" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("explains an unknown method", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Model" }), "res.partner");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Method" }), "nope");
    expect(await within(dialog).findByText(/is not in the fixtures/)).toBeInTheDocument();
  });

  it("marks a non-dry run as dangerous and shows the refusal", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Model" }), "sale.order");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Method" }), "action_confirm");
    await userEvent.click(within(dialog).getByRole("checkbox"));
    expect(within(dialog).getByText(/cannot be undone by Flowdoo/)).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "Run and commit" }));
    expect(await within(dialog).findByText(/The run could not be recorded/)).toBeInTheDocument();
  });

  it("closes with Cancel", async () => {
    const dialog = await openDialog();
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
