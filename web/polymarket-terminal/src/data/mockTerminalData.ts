import type {
  AuditEvent,
  BotStatus,
  MarketCandidate,
  OrderBookSnapshot,
  ProbabilityPoint,
  RiskLimit,
  SignalRow,
  TerminalStatus,
  TradeProposal
} from "../api/types";

export const mockBotStatus: BotStatus = {
  source: "mock",
  stale: true,
  deploymentId: "mock-deploy-001",
  state: "paused",
  mode: "advisory",
  lastHeartbeat: "2026-05-06T10:30:00.000Z",
  activeMarkets: 3,
  pendingProposals: 2,
  exposureUsd: 1280
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
    updatedAt: "2026-05-06T10:28:00.000Z"
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
    updatedAt: "2026-05-06T10:24:00.000Z"
  }
];

export const mockTradeProposals: TradeProposal[] = [
  {
    source: "mock",
    stale: true,
    id: "prop-001",
    deploymentId: "mock-deploy-001",
    marketId: "mkt-fed-2026",
    side: "buy",
    outcome: "yes",
    price: 0.58,
    sizeUsd: 250,
    rationale: "Mock advisory signal only. No order placement is connected.",
    status: "proposed",
    createdAt: "2026-05-06T10:29:00.000Z"
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
  auditEvents: mockAuditEvents,
  riskLimits: mockRiskLimits,
  probabilityHistory: mockProbabilityHistory,
  orderBook: mockOrderBook
};
