import { render, screen } from "@testing-library/react";

import { App } from "@/app/App";

describe("App", () => {
  it("renders the app name", () => {
    render(<App />);

    expect(screen.getByRole("main")).toHaveTextContent("Flowdoo");
  });
});
