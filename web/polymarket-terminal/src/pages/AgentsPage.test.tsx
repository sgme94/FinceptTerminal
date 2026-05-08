import { render, screen, within } from "@testing-library/react";
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
});
