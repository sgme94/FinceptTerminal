import { act, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  mockPolyAlphaOpportunities,
  mockPolyAlphaPromotionDecisions,
  mockPolyAlphaScanRuns,
  mockPolyAlphaShadowSignals,
  mockPolyAlphaValidationResults
} from "../data/mockTerminalData";
import { AgentsPage } from "./AgentsPage";

vi.mock("../api/client", () => ({
  fetchPolyAlphaCockpit: vi.fn()
}));

describe("AgentsPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    window.localStorage.clear();
    const client = await import("../api/client");
    vi.mocked(client.fetchPolyAlphaCockpit).mockResolvedValue({
      opportunities: mockPolyAlphaOpportunities,
      scanRuns: mockPolyAlphaScanRuns,
      shadowSignals: mockPolyAlphaShadowSignals,
      validations: mockPolyAlphaValidationResults,
      promotions: [
        {
          ...mockPolyAlphaPromotionDecisions[0],
          id: "poly-promotion-ready",
          decision: "promote",
          proposalId: "prop-poly-ready"
        },
        mockPolyAlphaPromotionDecisions[1]
      ]
    });
  });

  it("renders the Poly Alpha cockpit queues while preserving paper-only agent advisory semantics", async () => {
    render(<AgentsPage />);

    expect(await screen.findByRole("heading", { name: "Poly Alpha Cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Agents cannot trade")).toBeInTheDocument();
    expect(screen.getByText("paper-only")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Today's opportunities" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs research" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Shadow performance" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ready for promotion" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk queue candidates" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Failed and why" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "scheduled scan runs" })).toBeInTheDocument();

    const opportunitiesTable = screen.getByRole("table", { name: "Today's opportunities" });
    expect(within(opportunitiesTable).getByText("Fed June path repricing")).toBeInTheDocument();
    expect(within(opportunitiesTable).getByText("58% -> 64%")).toBeInTheDocument();

    expect((await screen.findAllByText("prop-poly-ready")).length).toBeGreaterThan(0);
    const promotionTable = screen.getByRole("table", { name: "Ready for promotion" });
    expect(within(promotionTable).getByText("prop-poly-ready")).toBeInTheDocument();

    const failedTable = screen.getByRole("table", { name: "Failed and why" });
    expect(within(failedTable).getByText("Momentum evidence is mixed.")).toBeInTheDocument();

    const scansTable = screen.getByRole("table", { name: "Scheduled scan runs" });
    expect(within(scansTable).getByText("poly-scan-001")).toBeInTheDocument();
  });

  it("renders Cockpit handoff rows saved by MarketsPage", async () => {
    window.localStorage.setItem(
      "poly-alpha-cockpit-handoffs",
      JSON.stringify([
        {
          opportunityId: "poly-opp-local",
          venueMarketId: "mkt-local",
          title: "Local handoff"
        }
      ])
    );

    render(<AgentsPage />);

    expect(await screen.findByRole("heading", { name: "Cockpit handoff queue" })).toBeInTheDocument();
    const handoffTable = screen.getByRole("table", { name: "Cockpit handoff queue" });
    expect(within(handoffTable).getByText("mkt-local")).toBeInTheDocument();
    expect(within(handoffTable).getByText("poly-opp-local")).toBeInTheDocument();
  });

  it("updates the Cockpit handoff queue from the MarketsPage handoff event", async () => {
    render(<AgentsPage />);

    expect(await screen.findByRole("heading", { name: "Poly Alpha Cockpit" })).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(
        new CustomEvent("poly-alpha-cockpit-handoff", {
          detail: {
            opportunityId: "poly-opp-event",
            venueMarketId: "mkt-event",
            title: "Event handoff"
          }
        })
      );
    });

    const handoffTable = await screen.findByRole("table", { name: "Cockpit handoff queue" });
    expect(within(handoffTable).getByText("mkt-event")).toBeInTheDocument();
    expect(within(handoffTable).getByText("poly-opp-event")).toBeInTheDocument();
  });

  it("uses shadow signal wording for an empty shadow table", async () => {
    const client = await import("../api/client");
    vi.mocked(client.fetchPolyAlphaCockpit).mockResolvedValue({
      opportunities: mockPolyAlphaOpportunities,
      scanRuns: mockPolyAlphaScanRuns,
      shadowSignals: [],
      validations: [],
      promotions: []
    });

    render(<AgentsPage />);

    expect(await screen.findByText("No shadow signal rows")).toBeInTheDocument();
    expect(screen.queryByText("No shadow signals have validation metrics.")).not.toBeInTheDocument();
  });
});
