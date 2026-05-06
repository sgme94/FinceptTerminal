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

export type TerminalStatus = {
  status: BotStatus;
  markets: MarketCandidate[];
  signals: SignalRow[];
  proposals: TradeProposal[];
  auditEvents: AuditEvent[];
  riskLimits: RiskLimit[];
  probabilityHistory: ProbabilityPoint[];
  orderBook: OrderBookSnapshot;
};
