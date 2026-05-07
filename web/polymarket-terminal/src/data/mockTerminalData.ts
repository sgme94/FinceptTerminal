import type {
  AuditEvent,
  BotStatus,
  MarketCandidate,
  OrderBookSnapshot,
  PaperPosition,
  PaperTrade,
  ProbabilityPoint,
  RiskLimit,
  SignalRow,
  SkipRow,
  TerminalStatus,
  TradeProposal
} from "../api/types";

export const mockBotStatus: BotStatus = {
  source: "mock",
  stale: true,
  deploymentId: "mock-deploy-001",
  state: "paused",
  mode: "paper",
  lastHeartbeat: "2026-05-06T10:30:00.000Z",
  activeMarkets: 3,
  pendingProposals: 2,
  exposureUsd: 1280,
  liveEnabled: false
};

export const mockMarketCandidates: MarketCandidate[] = [
  {
    source: "mock",
    stale: true,
    id: "mkt-fed-2026",
    question: "Fed funds target above 4% after June meeting?",
    category: "Macro",
    probability: 58,
    volumeUsd: 842000,
    liquidityUsd: 126000,
    spreadBps: 42,
    closesAt: "2026-06-17T20:00:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "mkt-btc-100k",
    question: "Bitcoin above 100k on May 31?",
    category: "Crypto",
    probability: 37,
    volumeUsd: 1290000,
    liquidityUsd: 221000,
    spreadBps: 35,
    closesAt: "2026-06-01T03:59:00.000Z"
  }
];

export const mockSignals: SignalRow[] = [
  {
    source: "mock",
    stale: true,
    id: "sig-fed-001",
    marketId: "mkt-fed-2026",
    label: "Rate path repricing",
    direction: "yes",
    confidence: 64,
    edgeBps: 118,
    updatedAt: "2026-05-06T10:28:00.000Z",
    reason: "Fed implied path moved faster than market price.",
    features: {
      "macro repricing": 0.42,
      liquidity: 0.21
    },
    evidence: ["CME odds update", "Polymarket spread stable"],
    freshnessLabel: "fresh 2m"
  },
  {
    source: "mock",
    stale: true,
    id: "sig-btc-001",
    marketId: "mkt-btc-100k",
    label: "Spot momentum fading",
    direction: "no",
    confidence: 57,
    edgeBps: 74,
    updatedAt: "2026-05-06T10:24:00.000Z",
    reason: "Momentum and liquidity disagree with the displayed probability.",
    features: {
      momentum: 0.33,
      "book imbalance": 0.18
    },
    evidence: ["Spot tape fade", "Order book ask depth"],
    freshnessLabel: "fresh 6m"
  }
];

export const mockTradeProposals: TradeProposal[] = [
  {
    source: "mock",
    stale: true,
    id: "prop-proposed",
    deploymentId: "mock-deploy-001",
    marketId: "mkt-fed-2026",
    side: "buy",
    outcome: "yes",
    price: 0.58,
    sizeUsd: 250,
    rationale: "Mock advisory signal only. No order placement is connected.",
    status: "proposed",
    createdAt: "2026-05-06T10:29:00.000Z"
  },
  ...(["approved", "rejected", "expired", "cancelled", "filled", "failed"] as TradeProposal["status"][]).map(
    (status, index) => ({
      source: "mock" as const,
      stale: true,
      id: `prop-${status}`,
      deploymentId: "mock-deploy-001",
      marketId: index % 2 === 0 ? "mkt-fed-2026" : "mkt-btc-100k",
      side: "buy" as const,
      outcome: "yes" as const,
      price: 0.5 + index / 100,
      sizeUsd: 100 + index * 25,
      rationale: `Mock ${status} proposal for lifecycle display.`,
      status,
      createdAt: `2026-05-06T10:2${index}:00.000Z`
    })
  )
];

export const mockPaperTrades: PaperTrade[] = [
  {
    source: "mock",
    stale: true,
    id: "trade-mock-1",
    deploymentId: "mock-deploy-001",
    assetId: "yes-token-1",
    side: "BUY",
    size: 10,
    price: 0.58,
    realizedPnl: 0,
    reason: "Mock paper fill.",
    createdAt: "2026-05-06T10:25:00.000Z"
  }
];

export const mockPaperPositions: PaperPosition[] = [
  {
    source: "mock",
    stale: true,
    id: "position-yes-token-1",
    deploymentId: "mock-deploy-001",
    assetId: "yes-token-1",
    size: 10,
    avgPrice: 0.58,
    exposureUsd: 5.8,
    realizedPnl: 0,
    updatedAt: "2026-05-06T10:25:00.000Z"
  }
];

export const mockAuditEvents: AuditEvent[] = [
  {
    source: "mock",
    stale: true,
    id: "audit-001",
    deploymentId: "mock-deploy-001",
    level: "warning",
    message: "API unavailable; terminal is displaying mock fallback data.",
    actor: "system",
    createdAt: "2026-05-06T10:30:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-start",
    deploymentId: "mock-deploy-001",
    level: "info",
    message: "Paper bot start requested.",
    actor: "user",
    action: "start",
    result: "accepted",
    createdAt: "2026-05-06T10:20:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-stop",
    deploymentId: "mock-deploy-001",
    level: "warning",
    message: "Paper bot stop requested.",
    actor: "user",
    action: "stop",
    result: "accepted",
    createdAt: "2026-05-06T10:21:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-approve",
    deploymentId: "mock-deploy-001",
    level: "info",
    message: "Proposal approved for paper tracking.",
    actor: "user",
    action: "approve",
    result: "approved",
    before: { status: "proposed" },
    after: { status: "approved" },
    createdAt: "2026-05-06T10:22:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-reject",
    deploymentId: "mock-deploy-001",
    level: "info",
    message: "Proposal rejected before paper tracking.",
    actor: "user",
    action: "reject",
    result: "rejected",
    before: { status: "proposed" },
    after: { status: "rejected" },
    createdAt: "2026-05-06T10:23:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-skip-001",
    deploymentId: "mock-deploy-001",
    level: "info",
    message: "Skipped order placement because live trading is disabled.",
    actor: "agent",
    action: "skip",
    result: "skipped",
    createdAt: "2026-05-06T10:24:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "audit-fill-001",
    deploymentId: "mock-deploy-001",
    level: "info",
    message: "Paper fill simulated for mock proposal.",
    actor: "agent",
    action: "fill_simulated",
    result: "filled",
    createdAt: "2026-05-06T10:25:00.000Z"
  }
];

export const mockRiskLimits: RiskLimit[] = [
  {
    source: "mock",
    stale: true,
    id: "risk-total",
    label: "Total exposure",
    limitUsd: 5000,
    usedUsd: 1280,
    status: "ok"
  },
  {
    source: "mock",
    stale: true,
    id: "risk-market",
    label: "Single market",
    limitUsd: 1000,
    usedUsd: 620,
    status: "warn"
  }
];

export const mockSkips: SkipRow[] = [
  {
    source: "mock",
    stale: true,
    id: "skip-thin-001",
    marketId: "mkt-thin-001",
    assetId: "asset-thin-001",
    reason: "liquidity_below_threshold",
    detail: "Book liquidity is below the paper strategy threshold.",
    createdAt: "2026-05-06T10:18:00.000Z"
  }
];

export const mockProbabilityHistory: ProbabilityPoint[] = [
  { time: "2026-05-01", value: 41 },
  { time: "2026-05-02", value: 44 },
  { time: "2026-05-03", value: 48 },
  { time: "2026-05-04", value: 52 },
  { time: "2026-05-05", value: 55 },
  { time: "2026-05-06", value: 58 }
];

export const mockOrderBook: OrderBookSnapshot = {
  source: "mock",
  stale: true,
  marketId: "mkt-fed-2026",
  bids: [
    { price: 0.57, size: 820 },
    { price: 0.56, size: 1140 }
  ],
  asks: [
    { price: 0.59, size: 760 },
    { price: 0.6, size: 980 }
  ]
};

export const mockTerminalSnapshot: TerminalStatus = {
  status: mockBotStatus,
  markets: mockMarketCandidates,
  signals: mockSignals,
  proposals: mockTradeProposals,
  trades: mockPaperTrades,
  positions: mockPaperPositions,
  auditEvents: mockAuditEvents,
  riskLimits: mockRiskLimits,
  probabilityHistory: mockProbabilityHistory,
  orderBook: mockOrderBook
};
