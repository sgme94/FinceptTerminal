import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NewsPage } from "./NewsPage";

describe("NewsPage", () => {
  it("renders a dense advisory news list with impact tags and freshness", () => {
    render(<NewsPage />);

    expect(screen.getByRole("heading", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Advisory read-only feed")).toBeInTheDocument();

    const table = screen.getByRole("table", { name: "Mock news feed" });
    expect(within(table).getByText("High impact")).toBeInTheDocument();
    expect(within(table).getByText("Polymarket blog")).toBeInTheDocument();
    expect(within(table).getByText("fresh 4m")).toBeInTheDocument();
  });
});
