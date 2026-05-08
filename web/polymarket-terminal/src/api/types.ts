export type DataSource = "api" | "mock";

export type DataQuality = {
  source: DataSource;
  stale?: boolean;
};

export type BotStatus = DataQuality & {
  deploymentId: string;
  state: "online" | "paused" | "offline";
  mode: "advisory" | "paper";
  lastHeartbeat: string;
  activeMarkets: number;
  pendingProposals: number;
  exposureUsd: number;
  liveEnabled?: boolean;
  approvalMode?: string;
  apiStatus?: string;
  healthy?: boolean;
  dbPath?: string;
};

export type MarketCandidate = DataQuality & {
  id: string;
  question: string;
  category: string;
  probability: number;
  volumeUsd: number;
  liquidityUsd: number;
  spreadBps: number;
  closesAt: string;
};

export type SignalRow = DataQuality & {
  id: string;
  marketId: string;
  label: string;
  direction: "yes" | "no";
  confidence: number;
  edgeBps: number;
  updatedAt: string;
  reason?: string;
  features?: Record<string, number>;
  evidence?: string[];
  freshnessLabel?: string;
};

export type TradeProposal = DataQuality & {
  id: string;
  deploymentId: string;
  marketId: string;
  side: "buy" | "sell";
  outcome: "yes" | "no";
  price: number;
  sizeUsd: number;
  rationale: string;
  status: "proposed" | "approved" | "rejected" | "expired" | "cancelled" | "filled" | "failed";
  createdAt: string;
  apiStatus?: string;
  strategyId?: string;
  conditionId?: string;
  assetId?: string;
};

export type PaperTrade = DataQuality & {
  id: string;
  deploymentId: string;
  assetId: string;
  side: string;
  size: number;
  price: number;
  realizedPnl: number;
  reason: string;
  createdAt: string;
};

export type PaperPosition = DataQuality & {
  id: string;
  deploymentId: string;
  assetId: string;
  size: number;
  avgPrice: number;
  exposureUsd: number;
  realizedPnl: number;
  updatedAt: string;
};

export type AuditEvent = DataQuality & {
  id: string;
  deploymentId: string;
  level: "info" | "warning" | "error";
  message: string;
  actor: "system" | "agent" | "user";
  createdAt: string;
  strategyId?: string;
  actorType?: string;
  actorId?: string;
  action?: string;
  entityType?: string;
  entityId?: string;
  before?: unknown;
  after?: unknown;
  result?: string;
  reason?: string;
  requestId?: string;
};

export type RiskLimit = DataQuality & {
  id: string;
  label: string;
  limitUsd: number;
  usedUsd: number;
  status: "ok" | "warn" | "breached";
};

export type SkipRow = DataQuality & {
  id: string;
  marketId: string;
  assetId?: string;
  reason: string;
  detail: string;
  createdAt: string;
};

export type ProbabilityPoint = {
  time: string;
  value: number;
};

export type OrderBookLevel = {
  price: number;
  size: number;
};

export type OrderBookSnapshot = DataQuality & {
  marketId: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
};

export type PolyAlphaOpportunity = DataQuality & {
  id: string;
  marketId: string;
  eventId?: string;
  title: string;
  thesis: string;
  score: number;
  probability: number;
  volumeUsd: number;
  liquidityUsd: number;
  edgeBps: number;
  status: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
};

export type PolyAlphaScanRun = DataQuality & {
  id: string;
  status: string;
  query: string;
  totalMarkets: number;
  matchedMarkets: number;
  startedAt: string;
  completedAt: string;
  error: string;
};

export type PolyAlphaScanResult = DataQuality & {
  id: string;
  scanRunId: string;
  marketId: string;
  title: string;
  rank: number;
  score: number;
  reason: string;
  createdAt: string;
};

export type PolyAlphaDocument = DataQuality & {
  id: string;
  title: string;
  url: string;
  sourceName: string;
  author: string;
  publishedAt: string;
  summary: string;
  metadata: Record<string, unknown>;
};

export type PolyAlphaEvent = DataQuality & {
  id: string;
  title: string;
  category: string;
  startsAt: string;
  endsAt: string;
  importance: number;
  summary: string;
  documentIds: string[];
};

export type PolyAlphaEventMarketLink = DataQuality & {
  id: string;
  eventId: string;
  marketId: string;
  marketTitle: string;
  relevanceScore: number;
  rationale: string;
};

export type PolyAlphaResearchRun = DataQuality & {
  id: string;
  opportunityId: string;
  status: string;
  agent: string;
  startedAt: string;
  completedAt: string;
  findingCount: number;
  error: string;
};

export type PolyAlphaAgentFinding = DataQuality & {
  id: string;
  researchRunId: string;
  opportunityId: string;
  agent: string;
  summary: string;
  confidence: number;
  evidenceIds: string[];
  createdAt: string;
};

export type PolyAlphaEvidencePack = DataQuality & {
  id: string;
  opportunityId: string;
  title: string;
  summary: string;
  documentIds: string[];
  findingIds: string[];
  createdAt: string;
  updatedAt: string;
};

export type PolyAlphaMarketSnapshot = DataQuality & {
  id: string;
  marketId: string;
  question: string;
  probability: number;
  volumeUsd: number;
  liquidityUsd: number;
  spreadBps: number;
  timestamp: string;
};

export type PolyAlphaShadowSignalStatus = "active" | "validated" | "rejected" | "expired";

export type PolyAlphaShadowSignal = DataQuality & {
  id: string;
  opportunityId: string;
  marketId: string;
  status: PolyAlphaShadowSignalStatus;
  direction: "yes" | "no";
  confidence: number;
  edgeBps: number;
  rationale: string;
  createdAt: string;
  updatedAt: string;
};

export type PolyAlphaValidationResult = DataQuality & {
  id: string;
  shadowSignalId: string;
  marketId: string;
  status: string;
  score: number;
  notes: string;
  rules: Record<string, unknown>;
  validatedAt: string;
};

export type PolyAlphaPromotionDecisionValue = "watch" | "promote" | "reject" | "defer";

export type PolyAlphaPromotionDecision = DataQuality & {
  id: string;
  shadowSignalId: string;
  marketId: string;
  decision: PolyAlphaPromotionDecisionValue;
  reason: string;
  sizeUsd: number;
  decidedAt: string;
  createdAt: string;
};

export type PolyAlphaCockpit = {
  opportunities: PolyAlphaOpportunity[];
  scanRuns: PolyAlphaScanRun[];
  shadowSignals: PolyAlphaShadowSignal[];
  validations: PolyAlphaValidationResult[];
  promotions: PolyAlphaPromotionDecision[];
};

export type PolyAlphaSignalFilters = {
  shadowStatuses: PolyAlphaShadowSignalStatus[];
  promotionDecisions: PolyAlphaPromotionDecisionValue[];
};

export type TerminalStatus = {
  status: BotStatus;
  markets: MarketCandidate[];
  signals: SignalRow[];
  proposals: TradeProposal[];
  trades: PaperTrade[];
  positions: PaperPosition[];
  auditEvents: AuditEvent[];
  riskLimits: RiskLimit[];
  probabilityHistory: ProbabilityPoint[];
  orderBook: OrderBookSnapshot;
};
