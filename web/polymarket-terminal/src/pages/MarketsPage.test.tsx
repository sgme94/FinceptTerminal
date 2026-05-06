import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockTerminalSnapshot } from "../data/mockTerminalData";
import { MarketsPage } from "./MarketsPage";

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn() })),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() }))
  })),
  AreaSeries: {},
  ColorType: {
    Solid: "solid"
  }
}));

vi.mock("../api/client", () => ({
  getTerminalSnapshot: vi.fn()
}));

describe("MarketsPage", () => {
  beforeEach(async () => {
    const client = await import("../api/client");
    vi.mocked(client.getTerminalSnapshot).mockResolvedValue(mockTerminalSnapshot);
  });

  it("renders filters, candidates, selected market detail, chart, and order book", async () => {
    render(<MarketsPage />);

    expect(await screen.findByRole("heading", { name: "Markets" })).toBeInTheDocument();
    expect(screen.getByLabelText("Market filters")).toBeInTheDocument();

    const candidateTable = screen.getByRole("table", { name: "Market candidates" });
    expect(within(candidateTable).getByText("Fed funds target above 4% after June meeting?")).toBeInTheDocument();
    expect(within(candidateTable).getByText("Macro")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Selected market" })).toBeInTheDocument();
    expect(screen.getByText("mkt-fed-2026")).toBeInTheDocument();
    expect(screen.getByTestId("probability-chart")).toHaveAttribute(
      "aria-label",
      "mkt-fed-2026 probability history"
    );
    expect(screen.getByLabelText("Order book summary")).toBeInTheDocument();
  });

  it("updates the selected market detail from the candidate table", async () => {
    const user = userEvent.setup();

    render(<MarketsPage />);
    await screen.findByRole("heading", { name: "Markets" });
    await user.click(screen.getByRole("button", { name: "Select mkt-btc-100k" }));

    expect(screen.getByRole("heading", { name: "Selected market" })).toBeInTheDocument();
    expect(screen.getByText("mkt-btc-100k")).toBeInTheDocument();
    expect(screen.getByText("Bitcoin above 100k on May 31?")).toBeInTheDocument();
  });
});
