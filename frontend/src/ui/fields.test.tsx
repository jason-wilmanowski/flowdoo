import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Input } from "./Input";
import { Select } from "./Select";

describe("Input and Select", () => {
  it("connects visible labels to the controls", async () => {
    render(
      <>
        <Input label="Model" placeholder="sale.order" mono />
        <Select
          label="Status"
          options={[
            { value: "", label: "All" },
            { value: "failed", label: "failed" },
          ]}
        />
      </>,
    );
    const input = screen.getByRole("textbox", { name: "Model" });
    await userEvent.type(input, "sale.order");
    expect(input).toHaveValue("sale.order");

    const select = screen.getByRole("combobox", { name: "Status" });
    await userEvent.selectOptions(select, "failed");
    expect(select).toHaveValue("failed");
  });

  it("works with an aria-label instead of a visible label", () => {
    render(<Input aria-label="Search" />);
    expect(screen.getByRole("textbox", { name: "Search" })).toBeInTheDocument();
  });
});
