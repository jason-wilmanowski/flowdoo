import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { createApiClient } from "@/api/client";
import { AppProviders } from "@/app/AppProviders";
import { AppRoutes } from "@/app/AppRoutes";
import { createApiDataSource, createFixtureDataSource, type DataSourceKind } from "@/datasource";

import { TooltipProvider } from "@/ui";

import { TracePagination } from "./TracePagination";

const FAILED_RECORDING_ID = "00000000-0000-4000-8000-0000000000f1";

function createSource(kind: DataSourceKind) {
  if (kind === "fixtures") return createFixtureDataSource({ delayMs: 0 });
  const offline = () => Promise.reject(new TypeError("Failed to fetch"));
  return createApiDataSource(createApiClient({ baseUrl: "http://api.invalid", fetch: offline }));
}

function renderList(kind: DataSourceKind = "fixtures") {
  render(
    <MemoryRouter initialEntries={["/traces"]}>
      <AppProviders initialDataSource={kind} createSource={createSource}>
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
}

const grid = () => screen.findByRole("grid", { name: "Traces" });
const bodyRows = (table: HTMLElement) => within(table).getAllByRole("row").slice(1);
const details = () => screen.getByRole("region", { name: "Trace details" });

describe("trace list", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("shows a skeleton first, then all traces newest first", async () => {
    renderList();
    expect(screen.getByRole("status", { name: "Loading traces" })).toBeInTheDocument();
    const table = await grid();
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["Status", "Entrypoint", "Run", "Started", "Duration", "ID"]);
    expect(bodyRows(table)).toHaveLength(5);
    expect(screen.getByText("1–5 of 5")).toBeInTheDocument();
    expect(details()).toHaveTextContent("Select a trace to see its details.");
  });

  it("shows the details of the selected trace, including a failed recording", async () => {
    renderList();
    const table = await grid();
    const failedRow = within(table).getByTitle(FAILED_RECORDING_ID).closest("tr")!;
    await userEvent.click(failedRow);
    expect(failedRow).toHaveAttribute("aria-selected", "true");
    expect(within(details()).getByText("failed")).toBeInTheDocument();
    expect(within(details()).getByRole("alert")).toHaveTextContent(
      /Recording failed: Cannot reach Odoo/,
    );
    expect(within(details()).getByText(FAILED_RECORDING_ID)).toBeInTheDocument();
    expect(within(details()).getByRole("link", { name: "Open trace" })).toHaveAttribute(
      "href",
      `/traces/${FAILED_RECORDING_ID}`,
    );
  });

  it("filters by status at once and by model on Apply, and clears filters", async () => {
    renderList();
    await grid();
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Status" }), "failed");
    expect(bodyRows(await grid())).toHaveLength(1);

    await userEvent.type(screen.getByRole("textbox", { name: "Model" }), "res.partner");
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(await screen.findByText("No traces match these filters.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(bodyRows(await grid())).toHaveLength(5);
    expect(screen.getByRole("combobox", { name: "Status" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Model" })).toHaveValue("");
  });

  it("deletes the selected trace after confirmation", async () => {
    renderList();
    const table = await grid();
    table.focus();
    await userEvent.keyboard("{ArrowDown}");
    await userEvent.click(within(details()).getByRole("button", { name: "Delete…" }));

    const dialog = await screen.findByRole("dialog", { name: "Delete trace?" });
    expect(dialog).toHaveTextContent("Your Odoo database is not affected.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete trace" }));

    expect(await screen.findByText("1–4 of 4")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(details()).toHaveTextContent("Select a trace to see its details.");
  });

  it("keeps the trace when the dialog is cancelled", async () => {
    renderList();
    (await grid()).focus();
    await userEvent.keyboard("{ArrowDown}");
    await userEvent.click(within(details()).getByRole("button", { name: "Delete…" }));
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(screen.getByText("1–5 of 5")).toBeInTheDocument();
  });

  it("opens the selected trace with Enter", async () => {
    renderList();
    (await grid()).focus();
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(await screen.findByRole("region", { name: "Calls" })).toBeInTheDocument();
  });

  it("shows the error with a retry when the API is unreachable", async () => {
    renderList("api");
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => /Could not load the traces/.test(a.textContent))).toBe(true);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("TracePagination", () => {
  it("shows the range and disables what is not possible", async () => {
    const onOffset = vi.fn();
    const { rerender } = render(
      <TracePagination total={42} limit={25} offset={0} onOffset={onOffset} />,
      { wrapper: TooltipProvider },
    );
    expect(screen.getByText("1–25 of 42")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(onOffset).toHaveBeenCalledWith(25);

    rerender(<TracePagination total={42} limit={25} offset={25} onOffset={onOffset} />);
    expect(screen.getByText("26–42 of 42")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  });
});
