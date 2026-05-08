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
  strategyVersionId: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  title: string;
  alphaFamily: string;
  status: string;
  primaryReason: string;
  marketProbability: number;
  estimatedProbability: number;
  edge: number;
  confidence: number;
  createdAt: string;
  updatedAt: string;
};

export type PolyAlphaScanRun = DataQuality & {
  id: string;
  triggerType: string;
  strategyVersionId: string;
  configVersionId: string;
  sourceSetVersion: string;
  status: string;
  startedAt: string;
  completedAt: string;
  scannedCount: number;
  ignoredCount: number;
  watchCount: number;
  createdOpportunityCount: number;
  errorMessage: string;
  createdAt: string;
};

export type PolyAlphaScanResult = DataQuality & {
  id: string;
  scanRunId: string;
  strategyVersionId: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  decision: string;
  reason: string;
  sourceSnapshotIds: string[];
  sourceDocumentIds: string[];
  createdOpportunityId: string;
  observedAt: string;
  createdAt: string;
};

export type PolyAlphaDocument = DataQuality & {
  id: string;
  sourceType: string;
  sourceName: string;
  url: string;
  apiEndpoint: string;
  marketId: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  assetSymbol: string;
  topic: string;
  publishedAt: string;
  fetchedAt: string;
  observedAt: string;
  payloadHash: string;
  title: string;
  normalizedText: string;
  rawPayload: Record<string, unknown>;
  trustLevel: string;
  createdAt: string;
};

export type PolyAlphaEvent = DataQuality & {
  id: string;
  eventType: string;
  title: string;
  summary: string;
  primaryAssets: string[];
  eventTime: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type PolyAlphaEventMarketLink = DataQuality & {
  id: string;
  eventId: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  adapterMetadata: Record<string, unknown>;
  outcome: string;
  linkReason: string;
  linkConfidence: number;
  createdAt: string;
};

export type PolyAlphaResearchRun = DataQuality & {
  id: string;
  triggerType: string;
  opportunityId: string;
  evidencePackId: string;
  strategyVersionId: string;
  eventId: string;
  venue: string;
  venueMarketId: string;
  requestedBy: string;
  startedAt: string;
  completedAt: string;
  status: string;
  modelConfig: Record<string, unknown>;
  createdAt: string;
};

export type PolyAlphaAgentFinding = DataQuality & {
  id: string;
  runId: string;
  opportunityId: string;
  evidencePackId: string;
  strategyVersionId: string;
  agentRole: string;
  estimatedProbability: number;
  marketProbability: number;
  edge: number;
  confidence: number;
  recommendation: string;
  thesis: string;
  evidenceIds: string[];
  counterEvidenceIds: string[];
  resolutionRisks: string[];
  blockers: string[];
  createdAt: string;
};

export type PolyAlphaEvidencePack = DataQuality & {
  id: string;
  opportunityId: string;
  strategyVersionId: string;
  documentIds: string[];
  snapshotIds: string[];
  eventIds: string[];
  sourceSetVersion: string;
  latestPublishedAt: string;
  latestFetchedAt: string;
  latestObservedAt: string;
  createdAt: string;
  payloadHash: string;
};

export type PolyAlphaMarketSnapshot = DataQuality & {
  id: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  adapterMetadata: Record<string, unknown>;
  sourceApi: string;
  observedAt: string;
  fetchedAt: string;
  payloadHash: string;
  bestBid: number;
  bestAsk: number;
  spread: number;
  topBidDepth: number;
  topAskDepth: number;
  midPrice: number;
  lastTradePrice: number;
  liquidity: number;
  volume: number;
  rawPayload: Record<string, unknown>;
  createdAt: string;
};

export type PolyAlphaShadowSignalStatus = "shadow" | "validated" | "rejected" | "promoted" | "expired";

export type PolyAlphaShadowSignal = DataQuality & {
  id: string;
  opportunityId: string;
  runId: string;
  strategyVersionId: string;
  strategyFamily: string;
  venue: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  adapterMetadata: Record<string, unknown>;
  side: string;
  observedPrice: number;
  estimatedProbability: number;
  edge: number;
  confidence: number;
  status: PolyAlphaShadowSignalStatus;
  createdAt: string;
  expiresAt: string;
};

export type PolyAlphaValidationResult = DataQuality & {
  id: string;
  opportunityId: string;
  shadowSignalId: string;
  strategyVersionId: string;
  entrySnapshotId: string;
  exitSnapshotId: string;
  validationType: string;
  entryPrice: number;
  exitPrice: number;
  holdingPeriod: string;
  grossReturn: number;
  costAdjustedReturn: number;
  closingLineValue: number;
  brierScore: number;
  calibrationError: number;
  edgeDecay: number;
  informationLagSec: number;
  fetchLagSec: number;
  marketMoveBeforeSignal: number;
  marketMoveAfterSignal: number;
  maxAdverseExcursion: number;
  maxFavorableExcursion: number;
  liquidityAssumption: string;
  slippageAssumption: string;
  passFail: string;
  failureReason: string;
  createdAt: string;
};

export type PolyAlphaPromotionDecisionValue = "watch" | "promote" | "reject";

export type PolyAlphaPromotionDecision = DataQuality & {
  id: string;
  opportunityId: string;
  shadowSignalId: string;
  strategyVersionId: string;
  decision: PolyAlphaPromotionDecisionValue;
  reason: string;
  predictionMetrics: Record<string, unknown>;
  tradingMetrics: Record<string, unknown>;
  metrics: Record<string, unknown>;
  criticBlockers: string[];
  riskChecks: Record<string, unknown>;
  proposalId: string;
  decidedAt: string;
};

export type PolyAlphaConfigVersion = DataQuality & {
  id: string;
  name: string;
  validationFreshnessWindowSec: number;
  minExplorationSamples: number;
  minPromotionSamples: number;
  minPromotionHistoryDays: number;
  maxDrawdownThreshold: number;
  minHitRate: number;
  minPayoffRatio: number;
  minCapacityMultiple: number;
  promotionDefaults: Record<string, unknown>;
  createdAt: string;
  isActive: boolean;
};

export type PolyAlphaSourceSet = DataQuality & {
  id: string;
  name: string;
  enabledSources: string[];
  trustPolicy: Record<string, unknown>;
  createdAt: string;
  isActive: boolean;
};

export type PolyAlphaStrategyVersion = DataQuality & {
  id: string;
  strategyFamily: string;
  strategyName: string;
  version: string;
  configVersionId: string;
  promptVersion: string;
  sourceSetVersion: string;
  description: string;
  createdAt: string;
  isActive: boolean;
};

export type PolyAlphaExplorationDecision = DataQuality & {
  id: string;
  opportunityId: string;
  evidencePackId: string;
  strategyVersionId: string;
  decision: string;
  reason: string;
  metrics: Record<string, unknown>;
  createdAt: string;
};

export type PolyAlphaAuditEvent = DataQuality & {
  id: string;
  action: string;
  entityType: string;
  entityId: string;
  opportunityId: string;
  strategyVersionId: string;
  actorType: string;
  actorId: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  result: string;
  reason: string;
  requestId: string;
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
