import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AuditEvent,
  MarketCandidate,
  PaperPosition,
  PaperTrade,
  PolyAlphaAuditEvent,
  PolyAlphaExplorationDecision,
  SignalRow,
  SkipRow,
  TradeProposal
} from "../api/types";
import {
  fetchPolyAlphaAuditEvents,
  getAuditEvents,
  getCandidates,
  getPaperPositions,
  getPaperTrades,
  getSignals,
  getSkips,
  getTradeProposals,
  fetchPolyAlphaEvidencePacks,
  fetchPolyAlphaExplorationDecisions,
  fetchPolyAlphaPromotions
} from "../api/client";
import { mockPolyAlphaEvidencePacks, mockPolyAlphaPromotionDecisions } from "../data/mockTerminalData";
import { AuditPage } from "./AuditPage";

vi.mock("../api/client", () => ({
  fetchPolyAlphaAuditEvents: vi.fn(),
  fetchPolyAlphaEvidencePacks: vi.fn(),
  fetchPolyAlphaExplorationDecisions: vi.fn(),
  fetchPolyAlphaPromotions: vi.fn(),
  getAuditEvents: vi.fn(),
  getCandidates: vi.fn(),
  getPaperPositions: vi.fn(),
  getPaperTrades: vi.fn(),
  getSignals: vi.fn(),
  getSkips: vi.fn(),
  getTradeProposals: vi.fn()
}));

const auditEvents: AuditEvent[] = [
  {
    source: "api",
    id: "audit-start",
    deploymentId: "dep-test",
    level: "info",
    message: "Bot start requested",
    actor: "user",
    action: "start",
    result: "accepted",
    createdAt: "2026-05-06T10:00:00.000Z"
  },
  {
    source: "api",
    id: "audit-stop",
    deploymentId: "dep-test",
    level: "warning",
    message: "Bot stop requested",
    actor: "user",
    action: "stop",
    result: "accepted",
    createdAt: "2026-05-06T10:05:00.000Z"
  },
  {
    source: "api",
    id: "audit-approve",
    deploymentId: "dep-test",
    level: "info",
    message: "Proposal approved",
    actor: "user",
    action: "approve",
    result: "approved",
    before: { status: "proposed" },
    after: { status: "approved" },
    createdAt: "2026-05-06T10:10:00.000Z"
  },
  {
    source: "api",
    id: "audit-reject",
    deploymentId: "dep-test",
    level: "info",
    message: "Proposal rejected",
    actor: "user",
    action: "reject",
    result: "rejected",
    before: { status: "proposed" },
    after: { status: "rejected" },
    createdAt: "2026-05-06T10:15:00.000Z"
  },
  {
    source: "api",
    id: "audit-explore",
    deploymentId: "dep-test",
    level: "info",
    message: "exploration decision accepted for poly-opp-fed-june",
    actor: "agent",
    action: "exploration_decision",
    result: "accepted",
    entityType: "poly_alpha_opportunity",
    entityId: "poly-opp-fed-june",
    createdAt: "2026-05-06T10:16:00.000Z"
  },
  {
    source: "api",
    id: "audit-paper-fill-skipped",
    deploymentId: "dep-test",
    level: "info",
    message: "paper_fill_skipped because promotion was watch",
    actor: "system",
    action: "paper_fill_skipped",
    result: "skipped",
    entityType: "poly_alpha_opportunity",
    entityId: "poly-opp-fed-june",
    createdAt: "2026-05-06T10:17:00.000Z"
  }
];

const proposals: TradeProposal[] = [
  {
    source: "api",
    id: "prop-1",
    deploymentId: "dep-test",
    marketId: "mkt-1",
    side: "buy",
    outcome: "yes",
    price: 0.58,
    sizeUsd: 75,
    rationale: "Paper proposal",
    status: "approved",
    createdAt: "2026-05-06T10:08:00.000Z"
  },
  {
    source: "api",
    id: "prop-other",
    deploymentId: "other-dep",
    marketId: "mkt-other",
    side: "buy",
    outcome: "no",
    price: 0.42,
    sizeUsd: 50,
    rationale: "Other deployment proposal",
    status: "proposed",
    createdAt: "2026-05-06T10:09:00.000Z"
  }
];

const trades: PaperTrade[] = [
  {
    source: "api",
    id: "trade-1",
    deploymentId: "dep-test",
    assetId: "asset-1",
    side: "BUY",
    size: 10,
    price: 0.58,
    realizedPnl: 0,
    reason: "manual approval fill",
    createdAt: "2026-05-06T10:20:00.000Z"
  }
];

const signals: SignalRow[] = [
  {
    source: "api",
    id: "signal-1",
    marketId: "asset-1",
    label: "Approved signal",
    direction: "yes",
    confidence: 72,
    edgeBps: 120,
    updatedAt: "2026-05-06T10:07:00.000Z"
  }
];

const positions: PaperPosition[] = [
  {
    source: "api",
    id: "position-asset-1",
    deploymentId: "dep-test",
    assetId: "asset-1",
    size: 10,
    avgPrice: 0.58,
    exposureUsd: 5.8,
    realizedPnl: 0,
    updatedAt: "2026-05-06T10:22:00.000Z"
  }
];

const candidates: MarketCandidate[] = [
  {
    source: "api",
    id: "mkt-candidate",
    question: "mkt-candidate",
    category: "yes",
    probability: 58,
    volumeUsd: 1200,
    liquidityUsd: 700,
    spreadBps: 0,
    closesAt: "2026-05-06T10:01:00.000Z"
  }
];

const skips: SkipRow[] = [
  {
    source: "api",
    id: "skip-1",
    marketId: "mkt-skip",
    assetId: "asset-skip",
    reason: "stale_orderbook",
    detail: "quote too old",
    createdAt: "2026-05-06T10:03:00.000Z"
  }
];

const apiExplorationDecisions: PolyAlphaExplorationDecision[] = [
  {
    source: "api",
    id: "api-explore-fed",
    opportunityId: "poly-opp-fed-june",
    evidencePackId: "poly-evidence-fed",
    strategyVersionId: "strategy-v1",
    decision: "pass",
    reason: "enough samples",
    metrics: { historicalSamples: 12 },
    createdAt: "2026-05-06T10:09:00.000Z"
  }
];

const apiPolyAlphaAuditEvents: PolyAlphaAuditEvent[] = [
  {
    source: "api",
    id: "api-paper-fill-skipped",
    action: "paper_fill_skipped",
    entityType: "opportunity",
    entityId: "poly-opp-fed-june",
    opportunityId: "poly-opp-fed-june",
    strategyVersionId: "strategy-v1",
    actorType: "system",
    actorId: "poly-alpha",
    before: { status: "watch" },
    after: { status: "skipped" },
    result: "skipped",
    reason: "paper only",
    requestId: "req-api",
    createdAt: "2026-05-06T10:17:00.000Z"
  }
];

describe("AuditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAuditEvents).mockResolvedValue(auditEvents);
    vi.mocked(getCandidates).mockResolvedValue(candidates);
    vi.mocked(getPaperPositions).mockResolvedValue(positions);
    vi.mocked(getPaperTrades).mockResolvedValue(trades);
    vi.mocked(getSignals).mockResolvedValue(signals);
    vi.mocked(getSkips).mockResolvedValue(skips);
    vi.mocked(getTradeProposals).mockResolvedValue(proposals);
    vi.mocked(fetchPolyAlphaEvidencePacks).mockResolvedValue(mockPolyAlphaEvidencePacks);
    vi.mocked(fetchPolyAlphaExplorationDecisions).mockResolvedValue(apiExplorationDecisions);
    vi.mocked(fetchPolyAlphaAuditEvents).mockResolvedValue([]);
    vi.mocked(fetchPolyAlphaPromotions).mockResolvedValue(mockPolyAlphaPromotionDecisions);
  });

  it("displays filters, control actions, proposal transitions, tabs, and append-only warning", async () => {
    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    expect(screen.getByLabelText(/deployment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/action/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/result/i)).toBeInTheDocument();

    const list = screen.getByRole("list", { name: /audit event list/i });
    expect(within(list).getAllByText(/start/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/stop/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/approve/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/reject/i).length).toBeGreaterThan(0);
    expect(within(list).getByText(/proposed -> approved/i)).toBeInTheDocument();
    expect(within(list).getByText(/proposed -> rejected/i)).toBeInTheDocument();

    expect(screen.getByRole("tab", { name: /trades/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /signals/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /positions/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /candidates/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /skips/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /proposals/i })).toBeInTheDocument();
    expect(screen.getAllByText(/append-only/i).length).toBeGreaterThan(0);
  });

  it("applies the deployment filter to the proposals tab", async () => {
    const user = userEvent.setup();

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/deployment/i), "dep-test");
    await user.click(screen.getByRole("tab", { name: /proposals/i }));

    expect(screen.getByText("prop-1")).toBeInTheDocument();
    expect(screen.getByText("mkt-1")).toBeInTheDocument();
    expect(screen.queryByText("prop-other")).not.toBeInTheDocument();
    expect(screen.queryByText("mkt-other")).not.toBeInTheDocument();
  });

  it("renders trades and signals tabs from backend rows", async () => {
    const user = userEvent.setup();

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    expect(screen.getByText("trade-1")).toBeInTheDocument();
    expect(screen.getByText("asset-1")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /signals/i }));

    expect(screen.getByText("signal-1")).toBeInTheDocument();
    expect(screen.getByText("Approved signal")).toBeInTheDocument();
  });

  it("keeps signal rows visible when deployment filter matches events but not signal ids", async () => {
    const user = userEvent.setup();

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/deployment/i), "dep-test");
    await user.click(screen.getByRole("tab", { name: /signals/i }));

    expect(screen.getByText("signal-1")).toBeInTheDocument();
  });

  it("renders positions, candidates, and skips audit projections", async () => {
    const user = userEvent.setup();

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /positions/i }));
    expect(screen.getByText("position-asset-1")).toBeInTheDocument();
    expect(screen.getByText("asset-1")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /candidates/i }));
    expect(screen.getAllByText("mkt-candidate").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("tab", { name: /skips/i }));
    expect(screen.getByText("skip-1")).toBeInTheDocument();
    expect(screen.getByText("stale_orderbook")).toBeInTheDocument();
  });

  it("shows a Poly Alpha evidence chain including exploration decisions and paper fill skips", async () => {
    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();

    expect((await screen.findAllByText("paper_fill_skipped")).length).toBeGreaterThan(0);
    const chain = screen.getByRole("table", { name: "Poly Alpha evidence chain" });
    expect(within(chain).getByText("poly-evidence-fed")).toBeInTheDocument();
    expect(within(chain).getByText("exploration_decision")).toBeInTheDocument();
    expect(within(chain).getByText("paper_fill_skipped")).toBeInTheDocument();
    expect(within(chain).getByText("poly-promotion-fed")).toBeInTheDocument();
  });

  it("loads Poly Alpha exploration and audit resources when general audit omits the evidence chain", async () => {
    vi.mocked(getAuditEvents).mockResolvedValue(auditEvents.slice(0, 4));
    vi.mocked(fetchPolyAlphaAuditEvents).mockResolvedValue(apiPolyAlphaAuditEvents);

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    await waitFor(() => expect(fetchPolyAlphaExplorationDecisions).toHaveBeenCalledTimes(1));
    expect(fetchPolyAlphaAuditEvents).toHaveBeenCalledTimes(1);

    const chain = screen.getByRole("table", { name: "Poly Alpha evidence chain" });
    expect(within(chain).getByText("api-explore-fed")).toBeInTheDocument();
    expect(within(chain).getByText("pass")).toBeInTheDocument();
    expect(within(chain).getByText("paper_fill_skipped")).toBeInTheDocument();
    expect(within(chain).getByText("poly-promotion-fed")).toBeInTheDocument();
  });

  it("does not synthesize paper fill skips from watch promotions without an audit event", async () => {
    vi.mocked(getAuditEvents).mockResolvedValue(auditEvents.slice(0, 4));
    vi.mocked(fetchPolyAlphaAuditEvents).mockResolvedValue([]);

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    await waitFor(() => expect(fetchPolyAlphaAuditEvents).toHaveBeenCalledTimes(1));

    const chain = screen.getByRole("table", { name: "Poly Alpha evidence chain" });
    expect(within(chain).getByText("api-explore-fed")).toBeInTheDocument();
    expect(within(chain).queryByText("paper_fill_skipped")).not.toBeInTheDocument();
  });

  it("matches exploration decisions to their exact evidence pack before falling back to opportunity", async () => {
    vi.mocked(getAuditEvents).mockResolvedValue(auditEvents.slice(0, 4));
    vi.mocked(fetchPolyAlphaEvidencePacks).mockResolvedValue([
      {
        ...mockPolyAlphaEvidencePacks[0],
        id: "poly-evidence-a",
        opportunityId: "poly-opp-shared"
      },
      {
        ...mockPolyAlphaEvidencePacks[0],
        id: "poly-evidence-b",
        opportunityId: "poly-opp-shared"
      }
    ]);
    vi.mocked(fetchPolyAlphaExplorationDecisions).mockResolvedValue([
      {
        source: "api",
        id: "api-explore-a",
        opportunityId: "poly-opp-shared",
        evidencePackId: "poly-evidence-a",
        strategyVersionId: "strategy-v1",
        decision: "pass",
        reason: "first pack",
        metrics: {},
        createdAt: "2026-05-06T10:09:00.000Z"
      },
      {
        source: "api",
        id: "api-explore-b",
        opportunityId: "poly-opp-shared",
        evidencePackId: "poly-evidence-b",
        strategyVersionId: "strategy-v1",
        decision: "reject",
        reason: "second pack",
        metrics: {},
        createdAt: "2026-05-06T10:10:00.000Z"
      }
    ]);

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    const chain = screen.getByRole("table", { name: "Poly Alpha evidence chain" });
    const rows = within(chain).getAllByRole("row");
    const firstPackRow = rows.find((row) => within(row).queryByText("poly-evidence-a"));
    const secondPackRow = rows.find((row) => within(row).queryByText("poly-evidence-b"));

    expect(firstPackRow).toBeDefined();
    expect(secondPackRow).toBeDefined();
    expect(within(firstPackRow!).getByText("api-explore-a")).toBeInTheDocument();
    expect(within(firstPackRow!).getByText("pass")).toBeInTheDocument();
    expect(within(secondPackRow!).getByText("api-explore-b")).toBeInTheDocument();
    expect(within(secondPackRow!).getByText("reject")).toBeInTheDocument();
  });
});
