/// <reference types="vite/client" />

import {
  mockAuditEvents,
  mockBotStatus,
  mockMarketCandidates,
  mockPaperPositions,
  mockPaperTrades,
  mockPolyAlphaDocuments,
  mockPolyAlphaEvents,
  mockPolyAlphaEvidencePacks,
  mockPolyAlphaFindings,
  mockPolyAlphaLinks,
  mockPolyAlphaMarketSnapshots,
  mockPolyAlphaOpportunities,
  mockPolyAlphaPromotionDecisions,
  mockPolyAlphaResearchRuns,
  mockPolyAlphaScanResults,
  mockPolyAlphaScanRuns,
  mockPolyAlphaShadowSignals,
  mockPolyAlphaValidationResults,
  mockRiskLimits,
  mockSignals,
  mockSkips,
  mockTerminalSnapshot,
  mockTradeProposals
} from "../data/mockTerminalData";
import type {
  AuditEvent,
  BotStatus,
  MarketCandidate,
  PaperPosition,
  PaperTrade,
  PolyAlphaAgentFinding,
  PolyAlphaCockpit,
  PolyAlphaDocument,
  PolyAlphaEvent,
  PolyAlphaEventMarketLink,
  PolyAlphaEvidencePack,
  PolyAlphaMarketSnapshot,
  PolyAlphaOpportunity,
  PolyAlphaPromotionDecision,
  PolyAlphaPromotionDecisionValue,
  PolyAlphaResearchRun,
  PolyAlphaScanResult,
  PolyAlphaScanRun,
  PolyAlphaShadowSignal,
  PolyAlphaShadowSignalStatus,
  PolyAlphaSignalFilters,
  PolyAlphaValidationResult,
  RiskLimit,
  SignalRow,
  SkipRow,
  TerminalStatus,
  TradeProposal
} from "./types";

const API_BASE = import.meta.env.VITE_POLYMARKET_API_BASE ?? "http://localhost:8765";

type BotStatusResponse = {
  mode?: string;
  live_enabled?: boolean;
  approval_mode?: string;
  status?: string;
  healthy?: boolean;
  db_path?: string;
};

type AuditEventResponse = {
  event_id?: string;
  deployment_id?: string;
  strategy_id?: string;
  actor_type?: string;
  actor_id?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  before?: unknown;
  after?: unknown;
  result?: string;
  reason?: string;
  request_id?: string;
  created_at?: string;
};

type AuditEventsResponse = {
  events: AuditEventResponse[];
};

type TradeProposalResponse = {
  proposal_id?: string;
  deployment_id?: string;
  strategy_id?: string;
  condition_id?: string;
  asset_id?: string;
  market_id?: string;
  side?: string;
  outcome?: string;
  price?: number;
  size?: number;
  status?: string;
  reason?: string;
  created_at?: string;
};

type TradeProposalsResponse = {
  proposals: TradeProposalResponse[];
};

type CandidateResponse = {
  market_id?: string;
  outcome?: string;
  price?: number;
  volume?: number;
  liquidity?: number;
  created_at?: string;
};

type CandidateListResponse = {
  candidates: CandidateResponse[];
};

type SignalResponse = {
  id?: number;
  asset_id?: string;
  action?: string;
  estimated_probability?: number;
  edge?: number;
  confidence?: number;
  reason?: string;
  features?: Record<string, unknown>;
  created_at?: string;
};

type SignalListResponse = {
  signals: SignalResponse[];
};

type SkipResponse = {
  id?: number;
  market_id?: string;
  asset_id?: string;
  reason?: string;
  detail?: string;
  created_at?: string;
};

type SkipListResponse = {
  skips: SkipResponse[];
};

type PaperTradeResponse = {
  id?: number;
  deployment_id?: string;
  asset_id?: string;
  side?: string;
  size?: number;
  price?: number;
  realized_pnl?: number;
  reason?: string;
  created_at?: string;
};

type PaperTradeListResponse = {
  trades: PaperTradeResponse[];
};

type PaperPositionResponse = {
  deployment_id?: string;
  asset_id?: string;
  size?: number;
  avg_price?: number;
  realized_pnl?: number;
  updated_at?: string;
};

type PaperPositionListResponse = {
  positions: PaperPositionResponse[];
};

type PolyAlphaItemResponse = Record<string, unknown>;

type PolyAlphaListResponse = {
  items?: PolyAlphaItemResponse[];
};

export type ControlActionPayload = {
  deployment_id: string;
  strategy_id?: string;
  actor_id?: string;
  reason?: string;
  request_id?: string;
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function mapBotState(status?: string, healthy?: boolean): BotStatus["state"] {
  if (healthy === false) {
    return "offline";
  }

  if (status === "paused") {
    return "paused";
  }

  if (status === "offline" || status === "failed" || status === "stopped") {
    return "offline";
  }

  if (healthy === true || status === "running" || status === "online") {
    return "online";
  }

  return "offline";
}

function mapBotStatus(body: BotStatusResponse): BotStatus {
  return {
    deploymentId: "default",
    state: mapBotState(body.status, body.healthy),
    mode: body.mode === "paper" ? "paper" : "advisory",
    lastHeartbeat: "",
    activeMarkets: 0,
    pendingProposals: 0,
    exposureUsd: 0,
    liveEnabled: body.live_enabled,
    approvalMode: body.approval_mode,
    apiStatus: body.status,
    healthy: body.healthy,
    dbPath: body.db_path,
    source: "api"
  };
}

function mapAuditActor(actorType?: string): AuditEvent["actor"] {
  if (actorType === "agent" || actorType === "bot" || actorType === "strategy") {
    return "agent";
  }

  if (actorType === "user" || actorType === "operator" || actorType === "human") {
    return "user";
  }

  return "system";
}

function mapAuditLevel(result?: string): AuditEvent["level"] {
  if (result === "success" || result === "accepted") {
    return "info";
  }

  if (result === "failed") {
    return "error";
  }

  return "warning";
}

function mapAuditMessage(event: AuditEventResponse): string {
  const summary = [event.action, event.result].filter(Boolean).join(" ");
  return event.reason ? `${summary}: ${event.reason}` : summary;
}

function mapAuditEvent(event: AuditEventResponse): AuditEvent {
  return {
    id: event.event_id ?? "",
    deploymentId: event.deployment_id ?? "",
    strategyId: event.strategy_id,
    actor: mapAuditActor(event.actor_type),
    actorType: event.actor_type,
    actorId: event.actor_id,
    action: event.action,
    entityType: event.entity_type,
    entityId: event.entity_id,
    before: event.before,
    after: event.after,
    level: mapAuditLevel(event.result),
    message: mapAuditMessage(event),
    result: event.result,
    reason: event.reason,
    requestId: event.request_id,
    createdAt: event.created_at ?? "",
    source: "api"
  };
}

function mapProposalSide(side?: string): TradeProposal["side"] {
  return side === "sell" ? "sell" : "buy";
}

function mapProposalStatus(status?: string): TradeProposal["status"] {
  if (
    status === "proposed" ||
    status === "approved" ||
    status === "rejected" ||
    status === "expired" ||
    status === "cancelled" ||
    status === "filled" ||
    status === "failed"
  ) {
    return status;
  }

  return "proposed";
}

function mapProposalOutcome(outcome?: string): TradeProposal["outcome"] {
  return outcome === "no" ? "no" : "yes";
}

function mapTradeProposal(proposal: TradeProposalResponse): TradeProposal {
  return {
    id: proposal.proposal_id ?? "",
    deploymentId: proposal.deployment_id ?? "",
    strategyId: proposal.strategy_id,
    conditionId: proposal.condition_id,
    assetId: proposal.asset_id,
    marketId: proposal.market_id ?? proposal.condition_id ?? proposal.proposal_id ?? "",
    side: mapProposalSide(proposal.side),
    outcome: mapProposalOutcome(proposal.outcome),
    price: proposal.price ?? 0,
    sizeUsd: proposal.size ?? 0,
    rationale: proposal.reason ?? "",
    status: mapProposalStatus(proposal.status),
    apiStatus: proposal.status,
    createdAt: proposal.created_at ?? "",
    source: "api"
  };
}

function mapCandidate(candidate: CandidateResponse): MarketCandidate {
  return {
    id: candidate.market_id ?? "",
    question: candidate.market_id ?? "Polymarket candidate",
    category: candidate.outcome ?? "Market",
    probability: Math.round((candidate.price ?? 0) * 100),
    volumeUsd: candidate.volume ?? 0,
    liquidityUsd: candidate.liquidity ?? 0,
    spreadBps: 0,
    closesAt: candidate.created_at ?? "",
    source: "api"
  };
}

function mapSignalFeatures(features?: Record<string, unknown>): Record<string, number> | undefined {
  if (!features) {
    return undefined;
  }

  const numericFeatures = Object.entries(features).filter(
    (entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1])
  );
  return numericFeatures.length > 0 ? Object.fromEntries(numericFeatures) : undefined;
}

function mapSignal(signal: SignalResponse): SignalRow {
  return {
    id: `signal-${signal.id ?? signal.asset_id ?? ""}`,
    marketId: signal.asset_id ?? "",
    label: signal.asset_id ?? "Signal",
    direction: signal.action === "sell" || signal.action === "no" ? "no" : "yes",
    confidence: Math.round((signal.confidence ?? 0) * 100),
    edgeBps: Math.round((signal.edge ?? 0) * 10000),
    updatedAt: signal.created_at ?? "",
    reason: signal.reason,
    features: mapSignalFeatures(signal.features),
    evidence: signal.reason ? [signal.reason] : [],
    freshnessLabel: signal.created_at ? "api" : "",
    source: "api"
  };
}

function mapSkip(skip: SkipResponse): SkipRow {
  return {
    id: `skip-${skip.id ?? skip.market_id ?? ""}`,
    marketId: skip.market_id ?? "",
    assetId: skip.asset_id,
    reason: skip.reason ?? "",
    detail: skip.detail ?? "",
    createdAt: skip.created_at ?? "",
    source: "api"
  };
}

function mapPaperTrade(trade: PaperTradeResponse): PaperTrade {
  return {
    id: `trade-${trade.id ?? trade.asset_id ?? ""}`,
    deploymentId: trade.deployment_id ?? "",
    assetId: trade.asset_id ?? "",
    side: trade.side ?? "",
    size: trade.size ?? 0,
    price: trade.price ?? 0,
    realizedPnl: trade.realized_pnl ?? 0,
    reason: trade.reason ?? "",
    createdAt: trade.created_at ?? "",
    source: "api"
  };
}

function mapPaperPosition(position: PaperPositionResponse): PaperPosition {
  const size = position.size ?? 0;
  const avgPrice = position.avg_price ?? 0;
  const assetId = position.asset_id ?? "";

  return {
    id: `position-${assetId}`,
    deploymentId: position.deployment_id ?? "",
    assetId,
    size,
    avgPrice,
    exposureUsd: size * avgPrice,
    realizedPnl: position.realized_pnl ?? 0,
    updatedAt: position.updated_at ?? "",
    source: "api"
  };
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function arrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function probabilityValue(value: unknown): number {
  const probability = numberValue(value);
  return probability > 0 && probability <= 1 ? Math.round(probability * 100) : probability;
}

function mapPolyAlphaOpportunity(item: PolyAlphaItemResponse): PolyAlphaOpportunity {
  return {
    id: stringValue(item.opportunity_id ?? item.id),
    marketId: stringValue(item.market_id),
    eventId: stringValue(item.event_id) || undefined,
    title: stringValue(item.title),
    thesis: stringValue(item.thesis),
    score: numberValue(item.score),
    probability: probabilityValue(item.probability),
    volumeUsd: numberValue(item.volume_usd ?? item.volume),
    liquidityUsd: numberValue(item.liquidity_usd ?? item.liquidity),
    edgeBps: numberValue(item.edge_bps),
    status: stringValue(item.status),
    tags: arrayValue(item.tags),
    createdAt: stringValue(item.created_at),
    updatedAt: stringValue(item.updated_at),
    source: "api"
  };
}

function mapPolyAlphaScanRun(item: PolyAlphaItemResponse): PolyAlphaScanRun {
  return {
    id: stringValue(item.scan_run_id ?? item.id),
    status: stringValue(item.status),
    query: stringValue(item.query),
    totalMarkets: numberValue(item.total_markets),
    matchedMarkets: numberValue(item.matched_markets),
    startedAt: stringValue(item.started_at),
    completedAt: stringValue(item.completed_at),
    error: stringValue(item.error),
    source: "api"
  };
}

function mapPolyAlphaScanResult(item: PolyAlphaItemResponse): PolyAlphaScanResult {
  return {
    id: stringValue(item.scan_result_id ?? item.result_id ?? item.id),
    scanRunId: stringValue(item.scan_run_id),
    marketId: stringValue(item.market_id),
    title: stringValue(item.title),
    rank: numberValue(item.rank),
    score: numberValue(item.score),
    reason: stringValue(item.reason),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaDocument(item: PolyAlphaItemResponse): PolyAlphaDocument {
  return {
    id: stringValue(item.document_id ?? item.id),
    title: stringValue(item.title),
    url: stringValue(item.url),
    sourceName: stringValue(item.source_name),
    author: stringValue(item.author),
    publishedAt: stringValue(item.published_at),
    summary: stringValue(item.summary),
    metadata: recordValue(item.metadata),
    source: "api"
  };
}

function mapPolyAlphaEvent(item: PolyAlphaItemResponse): PolyAlphaEvent {
  return {
    id: stringValue(item.event_id ?? item.id),
    title: stringValue(item.title),
    category: stringValue(item.category),
    startsAt: stringValue(item.starts_at),
    endsAt: stringValue(item.ends_at),
    importance: numberValue(item.importance),
    summary: stringValue(item.summary),
    documentIds: arrayValue(item.document_ids),
    source: "api"
  };
}

function mapPolyAlphaLink(item: PolyAlphaItemResponse): PolyAlphaEventMarketLink {
  return {
    id: stringValue(item.link_id ?? item.id),
    eventId: stringValue(item.event_id),
    marketId: stringValue(item.market_id),
    marketTitle: stringValue(item.market_title),
    relevanceScore: numberValue(item.relevance_score),
    rationale: stringValue(item.rationale),
    source: "api"
  };
}

function mapPolyAlphaResearchRun(item: PolyAlphaItemResponse): PolyAlphaResearchRun {
  return {
    id: stringValue(item.research_run_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    status: stringValue(item.status),
    agent: stringValue(item.agent),
    startedAt: stringValue(item.started_at),
    completedAt: stringValue(item.completed_at),
    findingCount: numberValue(item.finding_count),
    error: stringValue(item.error),
    source: "api"
  };
}

function mapPolyAlphaFinding(item: PolyAlphaItemResponse): PolyAlphaAgentFinding {
  return {
    id: stringValue(item.finding_id ?? item.id),
    researchRunId: stringValue(item.research_run_id),
    opportunityId: stringValue(item.opportunity_id),
    agent: stringValue(item.agent),
    summary: stringValue(item.summary),
    confidence: probabilityValue(item.confidence),
    evidenceIds: arrayValue(item.evidence_ids),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaEvidencePack(item: PolyAlphaItemResponse): PolyAlphaEvidencePack {
  return {
    id: stringValue(item.evidence_pack_id ?? item.pack_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    title: stringValue(item.title),
    summary: stringValue(item.summary),
    documentIds: arrayValue(item.document_ids),
    findingIds: arrayValue(item.finding_ids),
    createdAt: stringValue(item.created_at),
    updatedAt: stringValue(item.updated_at),
    source: "api"
  };
}

function mapPolyAlphaMarketSnapshot(item: PolyAlphaItemResponse): PolyAlphaMarketSnapshot {
  return {
    id: stringValue(item.snapshot_id ?? item.id),
    marketId: stringValue(item.market_id),
    question: stringValue(item.question),
    probability: probabilityValue(item.probability),
    volumeUsd: numberValue(item.volume_usd ?? item.volume),
    liquidityUsd: numberValue(item.liquidity_usd ?? item.liquidity),
    spreadBps: numberValue(item.spread_bps),
    timestamp: stringValue(item.timestamp ?? item.created_at),
    source: "api"
  };
}

function isPolyAlphaShadowSignalStatus(value: string): value is PolyAlphaShadowSignalStatus {
  return value === "active" || value === "validated" || value === "rejected" || value === "expired";
}

function mapPolyAlphaShadowSignalStatus(value: unknown): PolyAlphaShadowSignalStatus {
  const status = stringValue(value);
  return isPolyAlphaShadowSignalStatus(status) ? status : "active";
}

function mapPolyAlphaDirection(value: unknown): PolyAlphaShadowSignal["direction"] {
  return value === "no" || value === "sell" ? "no" : "yes";
}

function mapPolyAlphaShadowSignal(item: PolyAlphaItemResponse): PolyAlphaShadowSignal {
  return {
    id: stringValue(item.shadow_signal_id ?? item.signal_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    marketId: stringValue(item.market_id),
    status: mapPolyAlphaShadowSignalStatus(item.status),
    direction: mapPolyAlphaDirection(item.direction ?? item.outcome),
    confidence: probabilityValue(item.confidence),
    edgeBps: numberValue(item.edge_bps),
    rationale: stringValue(item.rationale ?? item.reason),
    createdAt: stringValue(item.created_at),
    updatedAt: stringValue(item.updated_at),
    source: "api"
  };
}

function mapPolyAlphaValidation(item: PolyAlphaItemResponse): PolyAlphaValidationResult {
  return {
    id: stringValue(item.validation_id ?? item.id),
    shadowSignalId: stringValue(item.shadow_signal_id ?? item.signal_id),
    marketId: stringValue(item.market_id),
    status: stringValue(item.status),
    score: numberValue(item.score),
    notes: stringValue(item.notes),
    rules: recordValue(item.rules),
    validatedAt: stringValue(item.validated_at ?? item.created_at),
    source: "api"
  };
}

function isPolyAlphaPromotionDecision(value: string): value is PolyAlphaPromotionDecisionValue {
  return value === "watch" || value === "promote" || value === "reject" || value === "defer";
}

function mapPolyAlphaPromotionDecisionValue(value: unknown): PolyAlphaPromotionDecisionValue {
  const decision = stringValue(value);
  return isPolyAlphaPromotionDecision(decision) ? decision : "defer";
}

function mapPolyAlphaPromotion(item: PolyAlphaItemResponse): PolyAlphaPromotionDecision {
  return {
    id: stringValue(item.promotion_id ?? item.id),
    shadowSignalId: stringValue(item.shadow_signal_id ?? item.signal_id),
    marketId: stringValue(item.market_id),
    decision: mapPolyAlphaPromotionDecisionValue(item.decision),
    reason: stringValue(item.reason),
    sizeUsd: numberValue(item.size_usd ?? item.size),
    decidedAt: stringValue(item.decided_at),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

async function fetchPolyAlphaResource<T>(
  path: string,
  mapper: (item: PolyAlphaItemResponse) => T,
  fallback: T[]
): Promise<T[]> {
  try {
    const body = await fetchJson<PolyAlphaListResponse>(path);
    return (body.items ?? []).map(mapper);
  } catch {
    return fallback;
  }
}

export async function getBotStatus(): Promise<BotStatus> {
  try {
    return mapBotStatus(await fetchJson<BotStatusResponse>("/api/bot/status"));
  } catch {
    return mockBotStatus;
  }
}

export async function getAuditEvents(deploymentId?: string): Promise<AuditEvent[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<AuditEventsResponse>(`/api/audit${query}`);
    return body.events.map(mapAuditEvent);
  } catch {
    return deploymentId
      ? mockAuditEvents.filter((event) => event.deploymentId === deploymentId)
      : mockAuditEvents;
  }
}

export async function getTradeProposals(deploymentId?: string): Promise<TradeProposal[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<TradeProposalsResponse>(`/api/proposals${query}`);
    return body.proposals.map(mapTradeProposal);
  } catch {
    return deploymentId
      ? mockTradeProposals.filter((proposal) => proposal.deploymentId === deploymentId)
      : mockTradeProposals;
  }
}

export async function getCandidates(deploymentId?: string): Promise<MarketCandidate[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<CandidateListResponse>(`/api/candidates${query}`);
    return body.candidates.map(mapCandidate);
  } catch {
    return mockMarketCandidates;
  }
}

export async function getSignals(deploymentId?: string): Promise<SignalRow[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<SignalListResponse>(`/api/signals${query}`);
    return body.signals.map(mapSignal);
  } catch {
    return mockSignals;
  }
}

export async function getSkips(deploymentId?: string): Promise<SkipRow[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<SkipListResponse>(`/api/skips${query}`);
    return body.skips.map(mapSkip);
  } catch {
    return mockSkips;
  }
}

export async function getPaperTrades(deploymentId?: string): Promise<PaperTrade[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<PaperTradeListResponse>(`/api/trades${query}`);
    return body.trades.map(mapPaperTrade);
  } catch {
    return deploymentId
      ? mockPaperTrades.filter((trade) => trade.deploymentId === deploymentId)
      : mockPaperTrades;
  }
}

export async function getPaperPositions(deploymentId?: string): Promise<PaperPosition[]> {
  const query = deploymentId ? `?deployment_id=${encodeURIComponent(deploymentId)}` : "";

  try {
    const body = await fetchJson<PaperPositionListResponse>(`/api/positions${query}`);
    return body.positions.map(mapPaperPosition);
  } catch {
    return deploymentId
      ? mockPaperPositions.filter((position) => position.deploymentId === deploymentId)
      : mockPaperPositions;
  }
}

export async function getRiskLimits(): Promise<RiskLimit[]> {
  return mockRiskLimits;
}

export function buildPolyAlphaSignalFilters(input: {
  shadowStatuses?: string[];
  promotionDecisions?: string[];
}): PolyAlphaSignalFilters {
  return {
    shadowStatuses: (input.shadowStatuses ?? []).filter(isPolyAlphaShadowSignalStatus),
    promotionDecisions: (input.promotionDecisions ?? []).filter(isPolyAlphaPromotionDecision)
  };
}

export async function fetchPolyAlphaOpportunities(): Promise<PolyAlphaOpportunity[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/opportunities",
    mapPolyAlphaOpportunity,
    mockPolyAlphaOpportunities
  );
}

export async function fetchPolyAlphaScanRuns(): Promise<PolyAlphaScanRun[]> {
  return fetchPolyAlphaResource("/api/poly-alpha/scan-runs", mapPolyAlphaScanRun, mockPolyAlphaScanRuns);
}

export async function fetchPolyAlphaScanResults(): Promise<PolyAlphaScanResult[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/scan-results",
    mapPolyAlphaScanResult,
    mockPolyAlphaScanResults
  );
}

export async function fetchPolyAlphaMarketSnapshots(): Promise<PolyAlphaMarketSnapshot[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/market-snapshots",
    mapPolyAlphaMarketSnapshot,
    mockPolyAlphaMarketSnapshots
  );
}

export async function fetchPolyAlphaDocuments(): Promise<PolyAlphaDocument[]> {
  return fetchPolyAlphaResource("/api/poly-alpha/documents", mapPolyAlphaDocument, mockPolyAlphaDocuments);
}

export async function fetchPolyAlphaEvents(): Promise<PolyAlphaEvent[]> {
  return fetchPolyAlphaResource("/api/poly-alpha/events", mapPolyAlphaEvent, mockPolyAlphaEvents);
}

export async function fetchPolyAlphaLinks(): Promise<PolyAlphaEventMarketLink[]> {
  return fetchPolyAlphaResource("/api/poly-alpha/links", mapPolyAlphaLink, mockPolyAlphaLinks);
}

export async function fetchPolyAlphaResearchRuns(): Promise<PolyAlphaResearchRun[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/research-runs",
    mapPolyAlphaResearchRun,
    mockPolyAlphaResearchRuns
  );
}

export async function fetchPolyAlphaFindings(): Promise<PolyAlphaAgentFinding[]> {
  return fetchPolyAlphaResource("/api/poly-alpha/findings", mapPolyAlphaFinding, mockPolyAlphaFindings);
}

export async function fetchPolyAlphaEvidencePacks(): Promise<PolyAlphaEvidencePack[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/evidence-packs",
    mapPolyAlphaEvidencePack,
    mockPolyAlphaEvidencePacks
  );
}

export async function fetchPolyAlphaShadowSignals(): Promise<PolyAlphaShadowSignal[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/shadow-signals",
    mapPolyAlphaShadowSignal,
    mockPolyAlphaShadowSignals
  );
}

export async function fetchPolyAlphaValidations(): Promise<PolyAlphaValidationResult[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/validations",
    mapPolyAlphaValidation,
    mockPolyAlphaValidationResults
  );
}

export async function fetchPolyAlphaPromotions(): Promise<PolyAlphaPromotionDecision[]> {
  return fetchPolyAlphaResource(
    "/api/poly-alpha/promotions",
    mapPolyAlphaPromotion,
    mockPolyAlphaPromotionDecisions
  );
}

export async function fetchPolyAlphaCockpit(): Promise<PolyAlphaCockpit> {
  const [opportunities, scanRuns, shadowSignals, validations, promotions] = await Promise.all([
    fetchPolyAlphaOpportunities(),
    fetchPolyAlphaScanRuns(),
    fetchPolyAlphaShadowSignals(),
    fetchPolyAlphaValidations(),
    fetchPolyAlphaPromotions()
  ]);

  return {
    opportunities,
    scanRuns,
    shadowSignals,
    validations,
    promotions
  };
}

export async function approveTradeProposal(
  proposalId: string,
  payload: ControlActionPayload
): Promise<void> {
  await postJson(`/api/proposals/${encodeURIComponent(proposalId)}/approve`, payload);
}

export async function rejectTradeProposal(
  proposalId: string,
  payload: ControlActionPayload
): Promise<void> {
  await postJson(`/api/proposals/${encodeURIComponent(proposalId)}/reject`, payload);
}

export async function triggerKillSwitch(payload: ControlActionPayload): Promise<void> {
  await postJson("/api/control/kill-switch", payload);
}

export async function getTerminalSnapshot(deploymentId = "default"): Promise<TerminalStatus> {
  const [status, proposals, trades, positions, auditEvents, markets, signals, riskLimits] = await Promise.all([
    getBotStatus(),
    getTradeProposals(deploymentId),
    getPaperTrades(deploymentId),
    getPaperPositions(deploymentId),
    getAuditEvents(deploymentId),
    getCandidates(deploymentId),
    getSignals(deploymentId),
    getRiskLimits()
  ]);
  const exposureUsd = positions.reduce((total, position) => total + position.exposureUsd, 0);

  return {
    ...mockTerminalSnapshot,
    status: {
      ...status,
      activeMarkets: positions.length,
      exposureUsd
    },
    markets,
    signals,
    proposals,
    trades,
    positions,
    auditEvents,
    riskLimits
  };
}
