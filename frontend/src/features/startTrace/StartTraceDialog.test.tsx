import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppProviders } from "@/app/AppProviders";
import { AppRoutes } from "@/app/AppRoutes";
import { createFixtureDataSource } from "@/datasource";

// Fixtures know no parameters; res.partner.write answers like Odoo 19 does.
function createSource() {
  const fixtures = createFixtureDataSource({ delayMs: 0 });
  return {
    ...fixtures,
    describeEntrypoint: (model: string, method: string, call?: { signal?: AbortSignal }) =>
      model === "res.partner" && method === "write"
        ? Promise.resolve({
            model,
            method,
            model_level: false,
            module: "account",
            summary: "Update all records in self with the provided values.",
            parameters: [
              {
                name: "vals",
                kind: "positional_or_keyword",
                required: true,
                default: null,
                annotation: null,
              },
              {
                name: "notify",
                kind: "keyword_only",
                required: false,
                default: "False",
                annotation: null,
              },
              {
                name: "kwargs",
                kind: "var_keyword",
                required: false,
                default: null,
                annotation: null,
              },
            ],
          })
        : fixtures.describeEntrypoint(model, method, call),
  };
}

function renderList() {
  render(
    <MemoryRouter initialEntries={["/traces"]}>
      <AppProviders initialDataSource="fixtures" createSource={createSource}>
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
    expect(await screen.findByRole("region", { name: "Calls" })).toBeInTheDocument();
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

  it("adds parameters to the arguments with a click", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Model" }), "res.partner");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Method" }), "write");
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Add vals to the arguments" }),
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Add notify to the arguments" }),
    );
    expect(within(dialog).getByRole("textbox", { name: /Arguments/ })).toHaveValue(
      '{\n  "vals": null,\n  "notify": false\n}',
    );
    // **kwargs cannot be passed by name
    expect(
      within(dialog).queryByRole("button", { name: "Add kwargs to the arguments" }),
    ).toBeNull();
  });

  it("does not show the error of an earlier attempt when opened again", async () => {
    const dialog = await openDialog();
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Model" }), "sale.order");
    await userEvent.type(within(dialog).getByRole("textbox", { name: "Method" }), "action_confirm");
    await userEvent.click(within(dialog).getByRole("checkbox"));
    await userEvent.click(within(dialog).getByRole("button", { name: "Run and commit" }));
    expect(await within(dialog).findByText(/The run could not be recorded/)).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Start trace" }));
    const again = await screen.findByRole("dialog", { name: "Start a trace" });
    expect(within(again).queryByText(/The run could not be recorded/)).toBeNull();
  });
});
