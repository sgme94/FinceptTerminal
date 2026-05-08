import type {
  AuditEvent,
  BotStatus,
  MarketCandidate,
  OrderBookSnapshot,
  PaperPosition,
  PaperTrade,
  ProbabilityPoint,
  PolyAlphaAgentFinding,
  PolyAlphaAuditEvent,
  PolyAlphaConfigVersion,
  PolyAlphaDocument,
  PolyAlphaEvent,
  PolyAlphaEventMarketLink,
  PolyAlphaEvidencePack,
  PolyAlphaExplorationDecision,
  PolyAlphaMarketSnapshot,
  PolyAlphaOpportunity,
  PolyAlphaPromotionDecision,
  PolyAlphaResearchRun,
  PolyAlphaScanResult,
  PolyAlphaScanRun,
  PolyAlphaShadowSignal,
  PolyAlphaSourceSet,
  PolyAlphaStrategyVersion,
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

export const mockPolyAlphaConfigVersions: PolyAlphaConfigVersion[] = [
  {
    source: "mock",
    stale: true,
    id: "config-v1",
    name: "Paper alpha defaults",
    validationFreshnessWindowSec: 300,
    minExplorationSamples: 10,
    minPromotionSamples: 30,
    minPromotionHistoryDays: 90,
    maxDrawdownThreshold: 0.08,
    minHitRate: 0.54,
    minPayoffRatio: 1.2,
    minCapacityMultiple: 3,
    promotionDefaults: { maxSizeUsd: 250 },
    createdAt: "2026-05-06T09:00:00.000Z",
    isActive: true
  }
];

export const mockPolyAlphaSourceSets: PolyAlphaSourceSet[] = [
  {
    source: "mock",
    stale: true,
    id: "sources-v1",
    name: "Official news and CLOB",
    enabledSources: ["official_calendar", "polymarket_clob", "newswire"],
    trustPolicy: { official_calendar: "high", newswire: "medium" },
    createdAt: "2026-05-06T09:00:00.000Z",
    isActive: true
  }
];

export const mockPolyAlphaStrategyVersions: PolyAlphaStrategyVersion[] = [
  {
    source: "mock",
    stale: true,
    id: "strategy-v1",
    strategyFamily: "macro_event",
    strategyName: "Event repricing scout",
    version: "2026.05",
    configVersionId: "config-v1",
    promptVersion: "prompt-v3",
    sourceSetVersion: "sources-v1",
    description: "Find late information repricing in liquid event markets.",
    createdAt: "2026-05-06T09:05:00.000Z",
    isActive: true
  }
];

export const mockPolyAlphaOpportunities: PolyAlphaOpportunity[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-opp-fed-june",
    strategyVersionId: "strategy-v1",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    title: "Fed June path repricing",
    alphaFamily: "macro_event",
    status: "shadow",
    primaryReason: "late_information",
    marketProbability: 58,
    estimatedProbability: 64,
    edge: 0.06,
    confidence: 72,
    createdAt: "2026-05-06T10:10:00.000Z",
    updatedAt: "2026-05-06T10:28:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-opp-btc-may",
    strategyVersionId: "strategy-v1",
    venue: "polymarket",
    venueMarketId: "mkt-btc-100k",
    venueContractId: "condition-btc-100k",
    outcomeId: "no-token-1",
    title: "Bitcoin month-end drift",
    alphaFamily: "crypto_momentum",
    status: "validated",
    primaryReason: "insufficient_edge",
    marketProbability: 37,
    estimatedProbability: 32,
    edge: -0.05,
    confidence: 57,
    createdAt: "2026-05-06T10:12:00.000Z",
    updatedAt: "2026-05-06T10:24:00.000Z"
  }
];

export const mockPolyAlphaScanRuns: PolyAlphaScanRun[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-scan-001",
    triggerType: "deterministic",
    strategyVersionId: "strategy-v1",
    configVersionId: "config-v1",
    sourceSetVersion: "sources-v1",
    status: "completed",
    startedAt: "2026-05-06T10:00:00.000Z",
    completedAt: "2026-05-06T10:03:00.000Z",
    scannedCount: 128,
    ignoredCount: 114,
    watchCount: 12,
    createdOpportunityCount: 2,
    errorMessage: "",
    createdAt: "2026-05-06T10:00:00.000Z"
  }
];

export const mockPolyAlphaScanResults: PolyAlphaScanResult[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-scan-result-fed",
    scanRunId: "poly-scan-001",
    strategyVersionId: "strategy-v1",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    decision: "watch",
    reason: "High liquidity, recent news density, and measurable price dislocation.",
    sourceSnapshotIds: ["poly-snapshot-fed"],
    sourceDocumentIds: ["poly-doc-fomc-calendar"],
    createdOpportunityId: "poly-opp-fed-june",
    observedAt: "2026-05-06T10:02:00.000Z",
    createdAt: "2026-05-06T10:03:00.000Z"
  }
];

export const mockPolyAlphaDocuments: PolyAlphaDocument[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-doc-fomc-calendar",
    sourceType: "official",
    sourceName: "Federal Reserve",
    url: "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    apiEndpoint: "",
    marketId: "",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    assetSymbol: "FEDFUNDS",
    topic: "rates",
    publishedAt: "2026-05-06T09:30:00.000Z",
    fetchedAt: "2026-05-06T09:31:00.000Z",
    observedAt: "2026-05-06T09:31:00.000Z",
    payloadHash: "doc-hash-fed",
    title: "FOMC June meeting calendar",
    normalizedText: "Official calendar confirms the June policy decision window.",
    rawPayload: { source: "mock" },
    trustLevel: "high",
    createdAt: "2026-05-06T09:31:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-doc-btc-flows",
    sourceType: "research",
    sourceName: "Mock Research",
    url: "https://example.com/bitcoin-etf-flows",
    apiEndpoint: "",
    marketId: "",
    venue: "polymarket",
    venueMarketId: "mkt-btc-100k",
    venueContractId: "condition-btc-100k",
    outcomeId: "no-token-1",
    assetSymbol: "BTC",
    topic: "crypto",
    publishedAt: "2026-05-06T09:45:00.000Z",
    fetchedAt: "2026-05-06T09:46:00.000Z",
    observedAt: "2026-05-06T09:46:00.000Z",
    payloadHash: "doc-hash-btc",
    title: "ETF flow tracker",
    normalizedText: "Daily flow data shows slower spot demand into month end.",
    rawPayload: { source: "mock" },
    trustLevel: "medium",
    createdAt: "2026-05-06T09:46:00.000Z"
  }
];

export const mockPolyAlphaEvents: PolyAlphaEvent[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-event-fomc-june",
    eventType: "macro_calendar",
    title: "June FOMC decision",
    summary: "Policy decision that resolves several rates-adjacent markets.",
    primaryAssets: ["FEDFUNDS"],
    eventTime: "2026-06-17T18:00:00.000Z",
    status: "scheduled",
    createdAt: "2026-05-06T09:32:00.000Z",
    updatedAt: "2026-05-06T09:32:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-event-btc-expiry",
    eventType: "market_resolution",
    title: "Bitcoin May close",
    summary: "Month-end reference price for Bitcoin level markets.",
    primaryAssets: ["BTC"],
    eventTime: "2026-06-01T03:59:00.000Z",
    status: "scheduled",
    createdAt: "2026-05-06T09:47:00.000Z",
    updatedAt: "2026-05-06T09:47:00.000Z"
  }
];

export const mockPolyAlphaLinks: PolyAlphaEventMarketLink[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-link-fed",
    eventId: "poly-event-fomc-june",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    adapterMetadata: { marketSlug: "fed-june" },
    outcome: "yes",
    linkReason: "The market resolves directly from the FOMC target range.",
    linkConfidence: 0.94,
    createdAt: "2026-05-06T09:33:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-link-btc",
    eventId: "poly-event-btc-expiry",
    venue: "polymarket",
    venueMarketId: "mkt-btc-100k",
    venueContractId: "condition-btc-100k",
    outcomeId: "no-token-1",
    adapterMetadata: { marketSlug: "btc-100k-may" },
    outcome: "no",
    linkReason: "The event timestamp matches the market settlement window.",
    linkConfidence: 0.88,
    createdAt: "2026-05-06T09:48:00.000Z"
  }
];

export const mockPolyAlphaResearchRuns: PolyAlphaResearchRun[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-research-001",
    triggerType: "manual_task",
    opportunityId: "poly-opp-fed-june",
    evidencePackId: "poly-evidence-fed",
    strategyVersionId: "strategy-v1",
    eventId: "poly-event-fomc-june",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    requestedBy: "local-user",
    startedAt: "2026-05-06T10:04:00.000Z",
    completedAt: "2026-05-06T10:08:00.000Z",
    status: "completed",
    modelConfig: { model: "mock-researcher" },
    createdAt: "2026-05-06T10:04:00.000Z"
  }
];

export const mockPolyAlphaFindings: PolyAlphaAgentFinding[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-finding-fed-001",
    runId: "poly-research-001",
    opportunityId: "poly-opp-fed-june",
    evidencePackId: "poly-evidence-fed",
    strategyVersionId: "strategy-v1",
    agentRole: "macro-news",
    estimatedProbability: 64,
    marketProbability: 58,
    edge: 0.06,
    confidence: 73,
    recommendation: "watch",
    thesis: "Policy commentary increased the probability of a higher-for-longer outcome.",
    evidenceIds: ["poly-doc-fomc-calendar"],
    counterEvidenceIds: [],
    resolutionRisks: ["ambiguous_resolution"],
    blockers: [],
    createdAt: "2026-05-06T10:07:00.000Z"
  }
];

export const mockPolyAlphaEvidencePacks: PolyAlphaEvidencePack[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-evidence-fed",
    opportunityId: "poly-opp-fed-june",
    strategyVersionId: "strategy-v1",
    documentIds: ["poly-doc-fomc-calendar"],
    snapshotIds: ["poly-snapshot-fed"],
    eventIds: ["poly-event-fomc-june"],
    sourceSetVersion: "sources-v1",
    latestPublishedAt: "2026-05-06T09:30:00.000Z",
    latestFetchedAt: "2026-05-06T09:31:00.000Z",
    latestObservedAt: "2026-05-06T10:28:00.000Z",
    createdAt: "2026-05-06T10:08:00.000Z",
    payloadHash: "evidence-hash-fed"
  }
];

export const mockPolyAlphaExplorationDecisions: PolyAlphaExplorationDecision[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-explore-fed",
    opportunityId: "poly-opp-fed-june",
    evidencePackId: "poly-evidence-fed",
    strategyVersionId: "strategy-v1",
    decision: "pass",
    reason: "Enough samples and fresh evidence to enter shadow tracking.",
    metrics: { historicalSamples: 42 },
    createdAt: "2026-05-06T10:09:00.000Z"
  }
];

export const mockPolyAlphaMarketSnapshots: PolyAlphaMarketSnapshot[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-snapshot-fed",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    adapterMetadata: { marketSlug: "fed-june" },
    sourceApi: "clob",
    observedAt: "2026-05-06T10:28:00.000Z",
    fetchedAt: "2026-05-06T10:28:30.000Z",
    payloadHash: "snapshot-hash-fed",
    bestBid: 0.57,
    bestAsk: 0.59,
    spread: 0.02,
    topBidDepth: 820,
    topAskDepth: 760,
    midPrice: 0.58,
    lastTradePrice: 0.575,
    liquidity: 126000,
    volume: 842000,
    rawPayload: { market: "mkt-fed-2026" },
    createdAt: "2026-05-06T10:28:30.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-snapshot-btc",
    venue: "polymarket",
    venueMarketId: "mkt-btc-100k",
    venueContractId: "condition-btc-100k",
    outcomeId: "no-token-1",
    adapterMetadata: { marketSlug: "btc-100k-may" },
    sourceApi: "clob",
    observedAt: "2026-05-06T10:24:00.000Z",
    fetchedAt: "2026-05-06T10:24:30.000Z",
    payloadHash: "snapshot-hash-btc",
    bestBid: 0.36,
    bestAsk: 0.38,
    spread: 0.02,
    topBidDepth: 910,
    topAskDepth: 870,
    midPrice: 0.37,
    lastTradePrice: 0.365,
    liquidity: 221000,
    volume: 1290000,
    rawPayload: { market: "mkt-btc-100k" },
    createdAt: "2026-05-06T10:24:30.000Z"
  }
];

export const mockPolyAlphaShadowSignals: PolyAlphaShadowSignal[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-shadow-fed",
    opportunityId: "poly-opp-fed-june",
    runId: "poly-research-001",
    strategyVersionId: "strategy-v1",
    strategyFamily: "macro_event",
    venue: "polymarket",
    venueMarketId: "mkt-fed-2026",
    venueContractId: "condition-fed-2026",
    outcomeId: "yes-token-1",
    adapterMetadata: { marketSlug: "fed-june" },
    side: "yes",
    observedPrice: 0.58,
    estimatedProbability: 64,
    edge: 0.06,
    confidence: 64,
    status: "shadow",
    createdAt: "2026-05-06T10:13:00.000Z",
    expiresAt: "2026-05-07T10:13:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-shadow-btc",
    opportunityId: "poly-opp-btc-may",
    runId: "poly-research-001",
    strategyVersionId: "strategy-v1",
    strategyFamily: "crypto_momentum",
    venue: "polymarket",
    venueMarketId: "mkt-btc-100k",
    venueContractId: "condition-btc-100k",
    outcomeId: "no-token-1",
    adapterMetadata: { marketSlug: "btc-100k-may" },
    side: "no",
    observedPrice: 0.37,
    estimatedProbability: 32,
    edge: -0.05,
    confidence: 57,
    status: "validated",
    createdAt: "2026-05-06T10:14:00.000Z",
    expiresAt: "2026-05-07T10:14:00.000Z"
  }
];

export const mockPolyAlphaValidationResults: PolyAlphaValidationResult[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-validation-fed",
    opportunityId: "poly-opp-fed-june",
    shadowSignalId: "poly-shadow-fed",
    strategyVersionId: "strategy-v1",
    entrySnapshotId: "poly-snapshot-fed",
    exitSnapshotId: "poly-snapshot-fed-exit",
    validationType: "fixed_horizon",
    entryPrice: 0.58,
    exitPrice: 0.61,
    holdingPeriod: "1h",
    grossReturn: 0.03,
    costAdjustedReturn: 0.026,
    closingLineValue: 0.02,
    brierScore: 0.19,
    calibrationError: 0.04,
    edgeDecay: 0.01,
    informationLagSec: 45,
    fetchLagSec: 4,
    marketMoveBeforeSignal: 0.004,
    marketMoveAfterSignal: 0.03,
    maxAdverseExcursion: -0.01,
    maxFavorableExcursion: 0.04,
    liquidityAssumption: "top_of_book",
    slippageAssumption: "half_spread",
    passFail: "pass",
    failureReason: "",
    createdAt: "2026-05-06T10:29:00.000Z"
  }
];

export const mockPolyAlphaPromotionDecisions: PolyAlphaPromotionDecision[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-promotion-fed",
    opportunityId: "poly-opp-fed-june",
    shadowSignalId: "poly-shadow-fed",
    strategyVersionId: "strategy-v1",
    decision: "watch",
    reason: "Strong signal, but wait for the next liquidity refresh before promotion.",
    predictionMetrics: { hitRate: 0.56 },
    tradingMetrics: { capacityUsd: 750 },
    metrics: { score: 0.81 },
    criticBlockers: [],
    riskChecks: { maxSizeUsd: 250 },
    proposalId: "",
    decidedAt: "2026-05-06T10:30:00.000Z"
  },
  {
    source: "mock",
    stale: true,
    id: "poly-promotion-btc",
    opportunityId: "poly-opp-btc-may",
    shadowSignalId: "poly-shadow-btc",
    strategyVersionId: "strategy-v1",
    decision: "reject",
    reason: "Momentum evidence is mixed.",
    predictionMetrics: { hitRate: 0.49 },
    tradingMetrics: { capacityUsd: 0 },
    metrics: { score: 0.43 },
    criticBlockers: ["mixed_evidence"],
    riskChecks: { maxSizeUsd: 0 },
    proposalId: "",
    decidedAt: "2026-05-06T10:25:00.000Z"
  }
];

export const mockPolyAlphaAuditEvents: PolyAlphaAuditEvent[] = [
  {
    source: "mock",
    stale: true,
    id: "poly-audit-shadow",
    action: "shadow_signal_created",
    entityType: "shadow_signal",
    entityId: "poly-shadow-fed",
    opportunityId: "poly-opp-fed-june",
    strategyVersionId: "strategy-v1",
    actorType: "system",
    actorId: "poly-alpha",
    before: {},
    after: { status: "shadow" },
    result: "success",
    reason: "Mock shadow signal created for fallback data.",
    requestId: "",
    createdAt: "2026-05-06T10:13:00.000Z"
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
