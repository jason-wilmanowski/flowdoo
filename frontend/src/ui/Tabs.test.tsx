import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "./Tabs";

function Example() {
  return (
    <Tabs defaultValue="changes">
      <TabsList aria-label="Step details">
        <TabsTrigger value="changes">Changes</TabsTrigger>
        <TabsTrigger value="overrides">Overrides</TabsTrigger>
        <TabsTrigger value="raw">Arguments</TabsTrigger>
      </TabsList>
      <TabsContent value="changes">changes panel</TabsContent>
      <TabsContent value="overrides">overrides panel</TabsContent>
      <TabsContent value="raw">raw panel</TabsContent>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("exposes tab roles with the default selected", () => {
    render(<Example />);
    expect(screen.getByRole("tablist", { name: "Step details" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Changes" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("changes panel");
  });

  it("moves between tabs with arrow keys, Home and End", async () => {
    render(<Example />);
    await userEvent.tab();
    expect(screen.getByRole("tab", { name: "Changes" })).toHaveFocus();

    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Overrides" })).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("overrides panel");

    await userEvent.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Arguments" })).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Changes" })).toHaveFocus();
  });
});
