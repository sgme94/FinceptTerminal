import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TerminalStatus } from "../api/types";
import { getTerminalSnapshot } from "../api/client";
import { OverviewPage } from "./OverviewPage";

vi.mock("../api/client", () => ({
  getTerminalSnapshot: vi.fn()
}));

const snapshot: TerminalStatus = {
  status: {
    source: "api",
    deploymentId: "dep-test",
    state: "paused",
    mode: "paper",
    lastHeartbeat: "2026-05-06T10:30:00.000Z",
    activeMarkets: 2,
    pendingProposals: 1,
    exposureUsd: 420,
    liveEnabled: false
  },
  markets: [],
  signals: [
    {
      source: "api",
      id: "sig-1",
      marketId: "mkt-1",
      label: "Momentum skip after risk check",
      direction: "yes",
      confidence: 61,
      edgeBps: 48,
      updatedAt: "2026-05-06T10:20:00.000Z"
    },
    {
      source: "api",
      id: "sig-2",
      marketId: "mkt-2",
      label: "Older signal two",
      direction: "no",
      confidence: 55,
      edgeBps: 32,
      updatedAt: "2026-05-06T10:19:00.000Z"
    },
    {
      source: "api",
      id: "sig-3",
      marketId: "mkt-3",
      label: "Older signal three",
      direction: "yes",
      confidence: 58,
      edgeBps: 36,
      updatedAt: "2026-05-06T10:18:00.000Z"
    },
    {
      source: "api",
      id: "sig-4",
      marketId: "mkt-4",
      label: "Newest signal beyond initial slice",
      direction: "yes",
      confidence: 67,
      edgeBps: 51,
      updatedAt: "2026-05-06T10:29:00.000Z"
    }
  ],
  proposals: [
    {
      source: "api",
      id: "prop-1",
      deploymentId: "dep-test",
      marketId: "mkt-1",
      side: "buy",
      outcome: "yes",
      price: 0.57,
      sizeUsd: 150,
      rationale: "Proposed from paper signal",
      status: "proposed",
      createdAt: "2026-05-06T10:25:00.000Z"
    }
  ],
  auditEvents: [
    {
      source: "api",
      id: "audit-fill-1",
      deploymentId: "dep-test",
      level: "info",
      message: "Paper fill simulated for mkt-1",
      actor: "agent",
      action: "fill_simulated",
      result: "filled",
      createdAt: "2026-05-06T10:27:00.000Z"
    },
    {
      source: "api",
      id: "audit-skip-1",
      deploymentId: "dep-test",
      level: "info",
      message: "Skipped order placement because live trading is disabled",
      actor: "agent",
      action: "skip",
      result: "skipped",
      createdAt: "2026-05-06T10:26:00.000Z"
    }
  ],
  riskLimits: [],
  probabilityHistory: [],
  orderBook: {
    source: "api",
    marketId: "mkt-1",
    bids: [],
    asks: []
  }
};

describe("OverviewPage", () => {
  beforeEach(() => {
    vi.mocked(getTerminalSnapshot).mockResolvedValue(snapshot);
  });

  it("displays paper mode, live disabled, PnL, positions, proposals, recent skips, and composer placeholder", async () => {
    render(<OverviewPage />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText(/paper mode/i)).toBeInTheDocument();
    expect(screen.getByText(/live disabled/i)).toBeInTheDocument();
    expect(screen.getAllByText(/PnL/i).length).toBeGreaterThan(0);
    expect(screen.getByText("$0.00")).toBeInTheDocument();
    expect(screen.getAllByText(/exposure/i).length).toBeGreaterThan(0);
    expect(screen.getByText("$420.00")).toBeInTheDocument();
    expect(screen.getAllByText(/open positions/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/pending proposals/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/proposed/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/recent signals\/fills\/skips/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Newest signal beyond initial slice/i)).toBeInTheDocument();
    expect(screen.getByText(/Paper fill simulated for mkt-1/i)).toBeInTheDocument();
    expect(screen.getByText("fill")).toBeInTheDocument();
    expect(screen.getByText(/Skipped order placement because live trading is disabled/i)).toBeInTheDocument();
    expect(screen.getAllByText(/agent composer placeholder/i).length).toBeGreaterThan(0);
  });

  it("does not display paper proposals as open positions when no positions endpoint is available", async () => {
    render(<OverviewPage />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();

    const openPositionsSection = screen.getByText("Open positions").closest(".page-section");
    expect(openPositionsSection).not.toBeNull();
    expect(within(openPositionsSection as HTMLElement).getByText(/No open positions/i)).toBeInTheDocument();
    expect(within(openPositionsSection as HTMLElement).queryByText("mkt-1")).not.toBeInTheDocument();
  });
});
