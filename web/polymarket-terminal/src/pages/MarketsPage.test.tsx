import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  mockPolyAlphaEvidencePacks,
  mockPolyAlphaLinks,
  mockPolyAlphaMarketSnapshots,
  mockPolyAlphaOpportunities,
  mockTerminalSnapshot
} from "../data/mockTerminalData";
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
  fetchPolyAlphaEvidencePacks: vi.fn(),
  fetchPolyAlphaLinks: vi.fn(),
  fetchPolyAlphaMarketSnapshots: vi.fn(),
  fetchPolyAlphaOpportunities: vi.fn(),
  getTerminalSnapshot: vi.fn()
}));

describe("MarketsPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    window.localStorage.clear();
    const client = await import("../api/client");
    vi.mocked(client.getTerminalSnapshot).mockResolvedValue(mockTerminalSnapshot);
    vi.mocked(client.fetchPolyAlphaOpportunities).mockResolvedValue(mockPolyAlphaOpportunities);
    vi.mocked(client.fetchPolyAlphaLinks).mockResolvedValue(mockPolyAlphaLinks);
    vi.mocked(client.fetchPolyAlphaEvidencePacks).mockResolvedValue(mockPolyAlphaEvidencePacks);
    vi.mocked(client.fetchPolyAlphaMarketSnapshots).mockResolvedValue(mockPolyAlphaMarketSnapshots);
  });

  it("renders filters, candidates, selected market detail, chart, and order book", async () => {
    render(<MarketsPage />);

    expect(await screen.findByRole("heading", { name: "Markets" })).toBeInTheDocument();
    expect(screen.getByLabelText("Market filters")).toBeInTheDocument();

    const candidateTable = screen.getByRole("table", { name: "Market candidates" });
    expect(within(candidateTable).getByText("Fed funds target above 4% after June meeting?")).toBeInTheDocument();
    expect(within(candidateTable).getByText("Macro")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Selected market" })).toBeInTheDocument();
    expect(screen.getAllByText("mkt-fed-2026").length).toBeGreaterThan(0);
    expect(screen.getByTestId("probability-chart")).toHaveAttribute(
      "aria-label",
      "mkt-fed-2026 probability history"
    );
    expect(screen.getByLabelText("Order book summary")).toBeInTheDocument();

    const polyAlphaTable = await screen.findByRole("table", { name: "Poly Alpha market links" });
    expect(within(polyAlphaTable).getAllByText("1 linked event").length).toBeGreaterThan(0);
    expect(within(polyAlphaTable).getByText("2026-05-06T10:28:00.000Z")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("58% vs 64%")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("$126,000")).toBeInTheDocument();
    expect(within(polyAlphaTable).getAllByText("0.02").length).toBeGreaterThan(0);
    expect(within(polyAlphaTable).getByText("2026-05-06T10:28:30.000Z")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("94%")).toBeInTheDocument();
    expect(
      within(polyAlphaTable).getByRole("button", { name: "Send mkt-fed-2026 to research/Cockpit" })
    ).toBeInTheDocument();
  });

  it("matches Poly Alpha links by market, contract, and outcome", async () => {
    const client = await import("../api/client");
    const opportunity = {
      ...mockPolyAlphaOpportunities[0],
      id: "poly-opp-shared-yes",
      venueMarketId: "mkt-shared",
      venueContractId: "condition-shared",
      outcomeId: "yes-token"
    };
    vi.mocked(client.fetchPolyAlphaOpportunities).mockResolvedValue([opportunity]);
    vi.mocked(client.fetchPolyAlphaLinks).mockResolvedValue([
      {
        ...mockPolyAlphaLinks[0],
        id: "poly-link-shared-yes",
        eventId: "poly-event-yes",
        venueMarketId: "mkt-shared",
        venueContractId: "condition-shared",
        outcomeId: "yes-token",
        linkConfidence: 0.61
      },
      {
        ...mockPolyAlphaLinks[0],
        id: "poly-link-shared-no",
        eventId: "poly-event-no",
        venueMarketId: "mkt-shared",
        venueContractId: "condition-shared",
        outcomeId: "no-token",
        linkConfidence: 0.99
      }
    ]);

    render(<MarketsPage />);

    const polyAlphaTable = await screen.findByRole("table", { name: "Poly Alpha market links" });
    expect(within(polyAlphaTable).getByText("1 linked event")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("61%")).toBeInTheDocument();
    expect(within(polyAlphaTable).queryByText("99%")).not.toBeInTheDocument();
  });

  it("updates the selected market detail from the candidate table", async () => {
    const user = userEvent.setup();

    render(<MarketsPage />);
    await screen.findByRole("heading", { name: "Markets" });
    await user.click(screen.getByRole("button", { name: "Select mkt-btc-100k" }));

    expect(screen.getByRole("heading", { name: "Selected market" })).toBeInTheDocument();
    expect(screen.getAllByText("mkt-btc-100k").length).toBeGreaterThan(0);
    expect(screen.getByText("Bitcoin above 100k on May 31?")).toBeInTheDocument();
  });

  it("queues a Poly Alpha market handoff to research/Cockpit without changing the selected market", async () => {
    const user = userEvent.setup();

    render(<MarketsPage />);

    expect(await screen.findByRole("heading", { name: "Markets" })).toBeInTheDocument();
    expect(screen.getByTestId("probability-chart")).toHaveAttribute(
      "aria-label",
      "mkt-fed-2026 probability history"
    );

    await user.click(screen.getByRole("button", { name: "Send mkt-btc-100k to research/Cockpit" }));

    expect(screen.getByText("Sent to Cockpit: mkt-btc-100k")).toBeInTheDocument();
    expect(screen.getByText("queued for cockpit")).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem("poly-alpha-cockpit-handoffs") ?? "[]")).toEqual([
      expect.objectContaining({
        opportunityId: "poly-opp-btc-may",
        venueMarketId: "mkt-btc-100k"
      })
    ]);
    expect(screen.getByTestId("probability-chart")).toHaveAttribute(
      "aria-label",
      "mkt-fed-2026 probability history"
    );
  });
});
