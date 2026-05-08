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
    strategyVersionId: stringValue(item.strategy_version_id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    title: stringValue(item.title),
    alphaFamily: stringValue(item.alpha_family),
    status: stringValue(item.status),
    primaryReason: stringValue(item.primary_reason),
    marketProbability: probabilityValue(item.market_probability),
    estimatedProbability: probabilityValue(item.estimated_probability),
    edge: numberValue(item.edge),
    confidence: probabilityValue(item.confidence),
    createdAt: stringValue(item.created_at),
    updatedAt: stringValue(item.updated_at),
    source: "api"
  };
}

function mapPolyAlphaScanRun(item: PolyAlphaItemResponse): PolyAlphaScanRun {
  return {
    id: stringValue(item.scan_run_id ?? item.id),
    triggerType: stringValue(item.trigger_type),
    strategyVersionId: stringValue(item.strategy_version_id),
    configVersionId: stringValue(item.config_version_id),
    sourceSetVersion: stringValue(item.source_set_version),
    status: stringValue(item.status),
    startedAt: stringValue(item.started_at),
    completedAt: stringValue(item.completed_at),
    scannedCount: numberValue(item.scanned_count),
    ignoredCount: numberValue(item.ignored_count),
    watchCount: numberValue(item.watch_count),
    createdOpportunityCount: numberValue(item.created_opportunity_count),
    errorMessage: stringValue(item.error_message),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaScanResult(item: PolyAlphaItemResponse): PolyAlphaScanResult {
  return {
    id: stringValue(item.scan_result_id ?? item.result_id ?? item.id),
    scanRunId: stringValue(item.scan_run_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    decision: stringValue(item.decision),
    reason: stringValue(item.reason),
    sourceSnapshotIds: arrayValue(item.source_snapshot_ids),
    sourceDocumentIds: arrayValue(item.source_document_ids),
    createdOpportunityId: stringValue(item.created_opportunity_id),
    observedAt: stringValue(item.observed_at),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaDocument(item: PolyAlphaItemResponse): PolyAlphaDocument {
  return {
    id: stringValue(item.document_id ?? item.id),
    sourceType: stringValue(item.source_type),
    sourceName: stringValue(item.source_name),
    url: stringValue(item.url),
    apiEndpoint: stringValue(item.api_endpoint),
    marketId: stringValue(item.market_id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    assetSymbol: stringValue(item.asset_symbol),
    topic: stringValue(item.topic),
    publishedAt: stringValue(item.published_at),
    fetchedAt: stringValue(item.fetched_at),
    observedAt: stringValue(item.observed_at),
    payloadHash: stringValue(item.payload_hash),
    title: stringValue(item.title),
    normalizedText: stringValue(item.normalized_text),
    rawPayload: recordValue(item.raw_payload),
    trustLevel: stringValue(item.trust_level),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaEvent(item: PolyAlphaItemResponse): PolyAlphaEvent {
  return {
    id: stringValue(item.event_id ?? item.id),
    eventType: stringValue(item.event_type),
    title: stringValue(item.title),
    summary: stringValue(item.summary),
    primaryAssets: arrayValue(item.primary_assets),
    eventTime: stringValue(item.event_time),
    status: stringValue(item.status),
    createdAt: stringValue(item.created_at),
    updatedAt: stringValue(item.updated_at),
    source: "api"
  };
}

function mapPolyAlphaLink(item: PolyAlphaItemResponse): PolyAlphaEventMarketLink {
  return {
    id: stringValue(item.link_id ?? item.id),
    eventId: stringValue(item.event_id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    adapterMetadata: recordValue(item.adapter_metadata),
    outcome: stringValue(item.outcome),
    linkReason: stringValue(item.link_reason),
    linkConfidence: numberValue(item.link_confidence),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaResearchRun(item: PolyAlphaItemResponse): PolyAlphaResearchRun {
  return {
    id: stringValue(item.run_id ?? item.id),
    triggerType: stringValue(item.trigger_type),
    opportunityId: stringValue(item.opportunity_id),
    evidencePackId: stringValue(item.evidence_pack_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    eventId: stringValue(item.event_id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    requestedBy: stringValue(item.requested_by),
    startedAt: stringValue(item.started_at),
    completedAt: stringValue(item.completed_at),
    status: stringValue(item.status),
    modelConfig: recordValue(item.model_config),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaFinding(item: PolyAlphaItemResponse): PolyAlphaAgentFinding {
  return {
    id: stringValue(item.finding_id ?? item.id),
    runId: stringValue(item.run_id),
    opportunityId: stringValue(item.opportunity_id),
    evidencePackId: stringValue(item.evidence_pack_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    agentRole: stringValue(item.agent_role),
    estimatedProbability: probabilityValue(item.estimated_probability),
    marketProbability: probabilityValue(item.market_probability),
    edge: numberValue(item.edge),
    confidence: probabilityValue(item.confidence),
    recommendation: stringValue(item.recommendation),
    thesis: stringValue(item.thesis),
    evidenceIds: arrayValue(item.evidence_ids),
    counterEvidenceIds: arrayValue(item.counter_evidence_ids),
    resolutionRisks: arrayValue(item.resolution_risks),
    blockers: arrayValue(item.blockers),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function mapPolyAlphaEvidencePack(item: PolyAlphaItemResponse): PolyAlphaEvidencePack {
  return {
    id: stringValue(item.evidence_pack_id ?? item.pack_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    documentIds: arrayValue(item.document_ids),
    snapshotIds: arrayValue(item.snapshot_ids),
    eventIds: arrayValue(item.event_ids),
    sourceSetVersion: stringValue(item.source_set_version),
    latestPublishedAt: stringValue(item.latest_published_at),
    latestFetchedAt: stringValue(item.latest_fetched_at),
    latestObservedAt: stringValue(item.latest_observed_at),
    createdAt: stringValue(item.created_at),
    payloadHash: stringValue(item.payload_hash),
    source: "api"
  };
}

function mapPolyAlphaMarketSnapshot(item: PolyAlphaItemResponse): PolyAlphaMarketSnapshot {
  return {
    id: stringValue(item.snapshot_id ?? item.id),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    adapterMetadata: recordValue(item.adapter_metadata),
    sourceApi: stringValue(item.source_api),
    observedAt: stringValue(item.observed_at),
    fetchedAt: stringValue(item.fetched_at),
    payloadHash: stringValue(item.payload_hash),
    bestBid: numberValue(item.best_bid),
    bestAsk: numberValue(item.best_ask),
    spread: numberValue(item.spread),
    topBidDepth: numberValue(item.top_bid_depth),
    topAskDepth: numberValue(item.top_ask_depth),
    midPrice: numberValue(item.mid_price),
    lastTradePrice: numberValue(item.last_trade_price),
    liquidity: numberValue(item.liquidity),
    volume: numberValue(item.volume),
    rawPayload: recordValue(item.raw_payload),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function isPolyAlphaFilterableShadowSignalStatus(
  value: string
): value is Exclude<PolyAlphaShadowSignalStatus, "unknown"> {
  return (
    value === "shadow" ||
    value === "validated" ||
    value === "rejected" ||
    value === "promoted" ||
    value === "expired"
  );
}

function mapPolyAlphaShadowSignalStatus(value: unknown): PolyAlphaShadowSignalStatus {
  const status = stringValue(value);
  return isPolyAlphaFilterableShadowSignalStatus(status) ? status : "unknown";
}

function mapPolyAlphaShadowSignal(item: PolyAlphaItemResponse): PolyAlphaShadowSignal {
  const rawStatus = stringValue(item.status);

  return {
    id: stringValue(item.shadow_signal_id ?? item.signal_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    runId: stringValue(item.run_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    strategyFamily: stringValue(item.strategy_family),
    venue: stringValue(item.venue),
    venueMarketId: stringValue(item.venue_market_id),
    venueContractId: stringValue(item.venue_contract_id),
    outcomeId: stringValue(item.outcome_id),
    adapterMetadata: recordValue(item.adapter_metadata),
    side: stringValue(item.side),
    observedPrice: numberValue(item.observed_price),
    estimatedProbability: probabilityValue(item.estimated_probability),
    edge: numberValue(item.edge),
    confidence: probabilityValue(item.confidence),
    status: mapPolyAlphaShadowSignalStatus(rawStatus),
    rawStatus,
    createdAt: stringValue(item.created_at),
    expiresAt: stringValue(item.expires_at),
    source: "api"
  };
}

function mapPolyAlphaValidation(item: PolyAlphaItemResponse): PolyAlphaValidationResult {
  return {
    id: stringValue(item.validation_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    shadowSignalId: stringValue(item.shadow_signal_id ?? item.signal_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    entrySnapshotId: stringValue(item.entry_snapshot_id),
    exitSnapshotId: stringValue(item.exit_snapshot_id),
    validationType: stringValue(item.validation_type),
    entryPrice: numberValue(item.entry_price),
    exitPrice: numberValue(item.exit_price),
    holdingPeriod: stringValue(item.holding_period),
    grossReturn: numberValue(item.gross_return),
    costAdjustedReturn: numberValue(item.cost_adjusted_return),
    closingLineValue: numberValue(item.closing_line_value),
    brierScore: numberValue(item.brier_score),
    calibrationError: numberValue(item.calibration_error),
    edgeDecay: numberValue(item.edge_decay),
    informationLagSec: numberValue(item.information_lag_sec),
    fetchLagSec: numberValue(item.fetch_lag_sec),
    marketMoveBeforeSignal: numberValue(item.market_move_before_signal),
    marketMoveAfterSignal: numberValue(item.market_move_after_signal),
    maxAdverseExcursion: numberValue(item.max_adverse_excursion),
    maxFavorableExcursion: numberValue(item.max_favorable_excursion),
    liquidityAssumption: stringValue(item.liquidity_assumption),
    slippageAssumption: stringValue(item.slippage_assumption),
    passFail: stringValue(item.pass_fail),
    failureReason: stringValue(item.failure_reason),
    createdAt: stringValue(item.created_at),
    source: "api"
  };
}

function isPolyAlphaFilterablePromotionDecision(
  value: string
): value is Exclude<PolyAlphaPromotionDecisionValue, "unknown"> {
  return value === "watch" || value === "promote" || value === "reject";
}

function mapPolyAlphaPromotionDecisionValue(value: unknown): PolyAlphaPromotionDecisionValue {
  const decision = stringValue(value);
  return isPolyAlphaFilterablePromotionDecision(decision) ? decision : "unknown";
}

function mapPolyAlphaPromotion(item: PolyAlphaItemResponse): PolyAlphaPromotionDecision {
  const rawDecision = stringValue(item.decision);

  return {
    id: stringValue(item.promotion_id ?? item.id),
    opportunityId: stringValue(item.opportunity_id),
    shadowSignalId: stringValue(item.shadow_signal_id ?? item.signal_id),
    strategyVersionId: stringValue(item.strategy_version_id),
    decision: mapPolyAlphaPromotionDecisionValue(rawDecision),
    rawDecision,
    reason: stringValue(item.reason),
    predictionMetrics: recordValue(item.prediction_metrics),
    tradingMetrics: recordValue(item.trading_metrics),
    metrics: recordValue(item.metrics),
    criticBlockers: arrayValue(item.critic_blockers),
    riskChecks: recordValue(item.risk_checks),
    proposalId: stringValue(item.proposal_id),
    decidedAt: stringValue(item.decided_at),
    source: "api"
  };
}

async function fetchPolyAlphaResource<T>(
  path: string,
  mapper: (item: PolyAlphaItemResponse) => T,
  fallback: T[]
): Promise<T[]> {
  let body: PolyAlphaListResponse;

  try {
    body = await fetchJson<PolyAlphaListResponse>(path);
  } catch {
    return fallback;
  }

  if (!Array.isArray(body.items)) {
    throw new Error(`Invalid poly alpha response for ${path}: items must be an array`);
  }

  return body.items.map(mapper);
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
    shadowStatuses: (input.shadowStatuses ?? []).filter(isPolyAlphaFilterableShadowSignalStatus),
    promotionDecisions: (input.promotionDecisions ?? []).filter(isPolyAlphaFilterablePromotionDecision)
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
