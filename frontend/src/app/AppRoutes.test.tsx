import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { createApiClient } from "@/api/client";
import { createApiDataSource, createFixtureDataSource, type DataSourceKind } from "@/datasource";

import { AppProviders } from "./AppProviders";
import { AppRoutes } from "./AppRoutes";

const FAILED_RECORDING_ID = "00000000-0000-4000-8000-0000000000f1";

// "api" points at a server that cannot be reached; "fixtures" answers without delay.
function createSource(kind: DataSourceKind) {
  if (kind === "fixtures") return createFixtureDataSource({ delayMs: 0 });
  const offline = () => Promise.reject(new TypeError("Failed to fetch"));
  return createApiDataSource(createApiClient({ baseUrl: "http://api.invalid", fetch: offline }));
}

function renderApp(path: string, kind: DataSourceKind = "fixtures", onDataSourceChange = vi.fn()) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AppProviders
        initialDataSource={kind}
        createSource={createSource}
        onDataSourceChange={onDataSourceChange}
      >
        <AppRoutes />
      </AppProviders>
    </MemoryRouter>,
  );
  return { onDataSourceChange };
}

describe("app shell", () => {
  afterEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("redirects / to the traces and shows connection, data source and dry run", async () => {
    renderApp("/");
    expect(await screen.findByText("Fixture data")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Traces" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Dry run")).toBeInTheDocument();
    const notices = screen.getByRole("region", { name: "Connection notices" });
    expect(notices).toHaveTextContent(/Warning.*Fixture mode/);
  });

  it("names the product with its logo, one image per theme", () => {
    renderApp("/");
    const logos = screen.getAllByRole("img", { name: "Flowdoo" });
    expect(logos).toHaveLength(2);
    expect(logos[0]?.getAttribute("src")).toMatch(/flowdoo-logo-dark/);
    expect(logos[1]?.getAttribute("src")).toMatch(/flowdoo-logo-light/);
  });

  it("shows problems as text when the API is unreachable and switches to fixtures", async () => {
    const { onDataSourceChange } = renderApp("/traces", "api");
    expect(await screen.findByText("API unreachable")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Connection notices" })).toHaveTextContent(
      /Problem.*The API did not answer/,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(/Could not load the traces/);

    await userEvent.click(screen.getByRole("button", { name: "Settings (,)" }));
    const sheet = await screen.findByRole("dialog", { name: "Settings" });
    await userEvent.click(within(sheet).getByRole("radio", { name: "Fixtures" }));
    expect(await screen.findByText("Fixture data")).toBeInTheDocument();
    expect(onDataSourceChange).toHaveBeenCalledWith("fixtures");
    await userEvent.keyboard("{Escape}");
    expect(await screen.findByRole("grid", { name: "Traces" })).toBeInTheDocument();
  });

  it("goes from the trace list to the trace view with its panels", async () => {
    renderApp("/traces");
    const grid = await screen.findByRole("grid", { name: "Traces" });
    grid.focus();
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(await screen.findByRole("tree", { name: "Calls" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Step details" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Replay controls" })).toBeInTheDocument();
    expect(screen.getByRole("separator", { name: "Resize Calls" })).toBeInTheDocument();
  });

  it("explains an unknown trace id and a failed recording", async () => {
    renderApp("/traces/nope");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "There is no trace with the id nope.",
    );
    expect(screen.getByRole("link", { name: "Back to traces" })).toBeInTheDocument();
  });

  it("shows a failed recording without steps", async () => {
    renderApp(`/traces/${FAILED_RECORDING_ID}`);
    expect(await screen.findByText("failed")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/The recording failed/);
  });

  it("opens the overview with the model list", async () => {
    renderApp("/overview");
    expect(await screen.findByRole("tree", { name: "Models" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("renders a not-found page inside the shell", () => {
    renderApp("/nope");
    expect(screen.getByText("There is no page at /nope.")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });

  it("switches and remembers the theme", async () => {
    document.documentElement.dataset.theme = "light";
    renderApp("/overview");
    await userEvent.click(screen.getByRole("button", { name: "Settings (,)" }));
    const sheet = await screen.findByRole("dialog", { name: "Settings" });
    expect(within(sheet).getByRole("radio", { name: "System" })).toBeChecked();
    await userEvent.click(within(sheet).getByRole("radio", { name: "Dark" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("flowdoo.theme")).toBe("dark");
    await userEvent.click(within(sheet).getByRole("radio", { name: "System" }));
    expect(localStorage.getItem("flowdoo.theme")).toBeNull();
  });
});

describe("keyboard shortcuts", () => {
  it("opens the help with ? and closes it with Escape, returning focus", async () => {
    renderApp("/nope");
    const trigger = screen.getByRole("link", { name: "Go to traces" });
    trigger.focus();
    await userEvent.keyboard("?");
    const dialog = await screen.findByRole("dialog", { name: "Keyboard shortcuts" });
    expect(within(dialog).getByText("Show keyboard shortcuts")).toBeInTheDocument();
    expect(within(dialog).getByText("?").tagName).toBe("KBD");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("opens the settings with the comma key; they list connection and shortcuts", async () => {
    renderApp("/overview");
    await screen.findByText("Fixture data");
    await userEvent.keyboard(",");
    const sheet = await screen.findByRole("dialog", { name: "Settings" });
    const shortcuts = within(sheet).getByRole("region", { name: "Keyboard shortcuts" });
    expect(shortcuts).toHaveTextContent("Show keyboard shortcuts");
    expect(shortcuts).toHaveTextContent("Open settings");
    expect(within(sheet).getByRole("region", { name: "Connection" })).toHaveTextContent("Database");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ignores ? typed into a text field", async () => {
    renderApp("/overview");
    const input = document.createElement("input");
    document.body.append(input);
    input.focus();
    await userEvent.keyboard("?");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(input).toHaveValue("?");
    input.remove();
  });
});
