/// <reference types="vite/client" />

import {
  mockAuditEvents,
  mockBotStatus,
  mockTerminalSnapshot,
  mockTradeProposals
} from "../data/mockTerminalData";
import type { AuditEvent, BotStatus, TerminalStatus, TradeProposal } from "./types";

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

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);

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

export async function getTerminalSnapshot(deploymentId = "default"): Promise<TerminalStatus> {
  const [status, proposals, auditEvents] = await Promise.all([
    getBotStatus(),
    getTradeProposals(deploymentId),
    getAuditEvents(deploymentId)
  ]);

  return {
    ...mockTerminalSnapshot,
    status,
    proposals,
    auditEvents
  };
}
