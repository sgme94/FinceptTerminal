import type {
  AuditEvent,
  BotStatus,
  MarketCandidate,
  OrderBookSnapshot,
  PaperPosition,
  PaperTrade,
  ProbabilityPoint,
  PolyAlphaAgentFinding,
  PolyAlphaDocument,
  PolyAlphaEvent,
  PolyAlphaEventMarketLink,
  PolyAlphaEvidencePack,
  PolyAlphaMarketSnapshot,
  PolyAlphaOpportunity,
  PolyAlphaPromotionDecision,
  PolyAlphaResearchRun,
  PolyAlphaScanResult,
  PolyAlphaScanRun,
  PolyAlphaShadowSignal,
  PolyAlphaValidationResult,
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

export const mockPolyAlphaOpportunities: PolyAlphaOpportunity[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-opp-fed-june",
    marketId: "mkt-fed-2026",
    eventId: "poly-event-fomc-june",
    title: "Fed June path repricing",
    thesis: "Rates articles moved faster than market pricing after fresh inflation commentary.",
    score: 82,
    probability: 58,
    volumeUsd: 842000,
    liquidityUsd: 126000,
    edgeBps: 118,
    status: "candidate",
    tags: ["macro", "rates", "fomc"],
    createdAt: "2026-05-06T10:10:00.000Z",
    updatedAt: "2026-05-06T10:28:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-opp-btc-may",
    marketId: "mkt-btc-100k",
    eventId: "poly-event-btc-expiry",
    title: "Bitcoin month-end drift",
    thesis: "Spot momentum is fading while prediction market liquidity remains deep.",
    score: 68,
    probability: 37,
    volumeUsd: 1290000,
    liquidityUsd: 221000,
    edgeBps: 74,
    status: "researching",
    tags: ["crypto", "momentum"],
    createdAt: "2026-05-06T10:12:00.000Z",
    updatedAt: "2026-05-06T10:24:00.000Z"
  }
];

export const mockPolyAlphaScanRuns: PolyAlphaScanRun[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-scan-001",
    status: "completed",
    query: "volume > 500000 and liquidity > 100000",
    totalMarkets: 128,
    matchedMarkets: 14,
    startedAt: "2026-05-06T10:00:00.000Z",
    completedAt: "2026-05-06T10:03:00.000Z",
    error: ""
  }
];

export const mockPolyAlphaScanResults: PolyAlphaScanResult[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-scan-result-fed",
    scanRunId: "poly-scan-001",
    marketId: "mkt-fed-2026",
    title: "Fed funds target above 4% after June meeting?",
    rank: 1,
    score: 82,
    reason: "High liquidity, recent news density, and measurable price dislocation.",
    createdAt: "2026-05-06T10:03:00.000Z"
  }
];

export const mockPolyAlphaDocuments: PolyAlphaDocument[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-doc-fomc-calendar",
    title: "FOMC June meeting calendar",
    url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    sourceName: "Federal Reserve",
    author: "",
    publishedAt: "2026-05-06T09:30:00.000Z",
    summary: "Official calendar confirms the June policy decision window.",
    metadata: { topic: "rates" }
  },
  {
    source: "mock",
    stale: true,
    id: "poly-doc-btc-flows",
    title: "ETF flow tracker",
    url: "https://example.com/bitcoin-etf-flows",
    sourceName: "Mock Research",
    author: "Research desk",
    publishedAt: "2026-05-06T09:45:00.000Z",
    summary: "Daily flow data shows slower spot demand into month end.",
    metadata: { topic: "crypto" }
  }
];

export const mockPolyAlphaEvents: PolyAlphaEvent[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-event-fomc-june",
    title: "June FOMC decision",
    category: "Macro",
    startsAt: "2026-06-17T18:00:00.000Z",
    endsAt: "2026-06-17T20:00:00.000Z",
    importance: 5,
    summary: "Policy decision that resolves several rates-adjacent markets.",
    documentIds: ["poly-doc-fomc-calendar"]
  },
  {
    source: "mock",
    stale: true,
    id: "poly-event-btc-expiry",
    title: "Bitcoin May close",
    category: "Crypto",
    startsAt: "2026-06-01T03:59:00.000Z",
    endsAt: "2026-06-01T03:59:00.000Z",
    importance: 4,
    summary: "Month-end reference price for Bitcoin level markets.",
    documentIds: ["poly-doc-btc-flows"]
  }
];

export const mockPolyAlphaLinks: PolyAlphaEventMarketLink[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-link-fed",
    eventId: "poly-event-fomc-june",
    marketId: "mkt-fed-2026",
    marketTitle: "Fed funds target above 4% after June meeting?",
    relevanceScore: 0.94,
    rationale: "The market resolves directly from the FOMC target range."
  },
  {
    source: "mock",
    stale: true,
    id: "poly-link-btc",
    eventId: "poly-event-btc-expiry",
    marketId: "mkt-btc-100k",
    marketTitle: "Bitcoin above 100k on May 31?",
    relevanceScore: 0.88,
    rationale: "The event timestamp matches the market settlement window."
  }
];

export const mockPolyAlphaResearchRuns: PolyAlphaResearchRun[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-research-001",
    opportunityId: "poly-opp-fed-june",
    status: "completed",
    agent: "macro-news",
    startedAt: "2026-05-06T10:04:00.000Z",
    completedAt: "2026-05-06T10:08:00.000Z",
    findingCount: 2,
    error: ""
  }
];

export const mockPolyAlphaFindings: PolyAlphaAgentFinding[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-finding-fed-001",
    researchRunId: "poly-research-001",
    opportunityId: "poly-opp-fed-june",
    agent: "macro-news",
    summary: "Policy commentary increased the probability of a higher-for-longer outcome.",
    confidence: 73,
    evidenceIds: ["poly-doc-fomc-calendar"],
    createdAt: "2026-05-06T10:07:00.000Z"
  }
];

export const mockPolyAlphaEvidencePacks: PolyAlphaEvidencePack[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-evidence-fed",
    opportunityId: "poly-opp-fed-june",
    title: "Fed path evidence pack",
    summary: "Calendar, liquidity, and policy commentary supporting the rates opportunity.",
    documentIds: ["poly-doc-fomc-calendar"],
    findingIds: ["poly-finding-fed-001"],
    createdAt: "2026-05-06T10:08:00.000Z",
    updatedAt: "2026-05-06T10:09:00.000Z"
  }
];

export const mockPolyAlphaMarketSnapshots: PolyAlphaMarketSnapshot[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-snapshot-fed",
    marketId: "mkt-fed-2026",
    question: "Fed funds target above 4% after June meeting?",
    probability: 58,
    volumeUsd: 842000,
    liquidityUsd: 126000,
    spreadBps: 42,
    timestamp: "2026-05-06T10:28:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-snapshot-btc",
    marketId: "mkt-btc-100k",
    question: "Bitcoin above 100k on May 31?",
    probability: 37,
    volumeUsd: 1290000,
    liquidityUsd: 221000,
    spreadBps: 35,
    timestamp: "2026-05-06T10:24:00.000Z"
  }
];

export const mockPolyAlphaShadowSignals: PolyAlphaShadowSignal[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-shadow-fed",
    opportunityId: "poly-opp-fed-june",
    marketId: "mkt-fed-2026",
    status: "active",
    direction: "yes",
    confidence: 64,
    edgeBps: 118,
    rationale: "Shadow signal is active while validation checks replay recent pricing.",
    createdAt: "2026-05-06T10:13:00.000Z",
    updatedAt: "2026-05-06T10:28:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-shadow-btc",
    opportunityId: "poly-opp-btc-may",
    marketId: "mkt-btc-100k",
    status: "validated",
    direction: "no",
    confidence: 57,
    edgeBps: 74,
    rationale: "Signal passed liquidity checks but remains below promotion threshold.",
    createdAt: "2026-05-06T10:14:00.000Z",
    updatedAt: "2026-05-06T10:24:00.000Z"
  }
];

export const mockPolyAlphaValidationResults: PolyAlphaValidationResult[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-validation-fed",
    shadowSignalId: "poly-shadow-fed",
    marketId: "mkt-fed-2026",
    status: "passed",
    score: 81,
    notes: "Liquidity, spread, and stale-data checks passed.",
    rules: { minLiquidityUsd: 100000, maxSpreadBps: 75 },
    validatedAt: "2026-05-06T10:29:00.000Z"
  }
];

export const mockPolyAlphaPromotionDecisions: PolyAlphaPromotionDecision[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-promotion-fed",
    shadowSignalId: "poly-shadow-fed",
    marketId: "mkt-fed-2026",
    decision: "watch",
    reason: "Strong signal, but wait for the next liquidity refresh before promotion.",
    sizeUsd: 0,
    decidedAt: "2026-05-06T10:30:00.000Z",
    createdAt: "2026-05-06T10:30:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-promotion-btc",
    shadowSignalId: "poly-shadow-btc",
    marketId: "mkt-btc-100k",
    decision: "defer",
    reason: "Momentum evidence is mixed.",
    sizeUsd: 0,
    decidedAt: "2026-05-06T10:25:00.000Z",
    createdAt: "2026-05-06T10:25:00.000Z"
  }
];

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
