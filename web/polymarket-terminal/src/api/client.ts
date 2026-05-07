/// <reference types="vite/client" />

import {
  mockAuditEvents,
  mockBotStatus,
  mockMarketCandidates,
  mockPaperPositions,
  mockPaperTrades,
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

  return {
    ...mockTerminalSnapshot,
    status,
    markets,
    signals,
    proposals,
    trades,
    positions,
    auditEvents,
    riskLimits
  };
}
