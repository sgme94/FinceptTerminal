from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BotStatus(BaseModel):
    mode: str = "paper"
    live_enabled: bool = False
    approval_mode: str = "manual_approval"
    status: str = "idle"
    healthy: bool = True
    db_path: str


class AuditEvent(BaseModel):
    event_id: str
    deployment_id: str
    strategy_id: str
    actor_type: str
    actor_id: str = ""
    action: str
    entity_type: str
    entity_id: str = ""
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    result: str
    reason: str = ""
    request_id: str = ""
    created_at: str


class AuditEventList(BaseModel):
    events: list[AuditEvent]


class Proposal(BaseModel):
    id: int
    proposal_id: str
    deployment_id: str
    strategy_id: str
    market_id: str | None = None
    condition_id: str | None = None
    asset_id: str | None = None
    side: str | None = None
    price: float | None = None
    fill_trade_id: str = ""
    estimated_probability: float | None = None
    edge: float | None = None
    confidence: float | None = None
    reason: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    size: float
    status: str
    created_at: str
    expires_at: str | None = None
    decided_by: str = ""
    decided_at: str = ""
    decision_reason: str = ""


class ProposalList(BaseModel):
    proposals: list[Proposal]


class ControlActionRequest(BaseModel):
    deployment_id: str = "default"
    strategy_id: str = "manual"
    actor_id: str = "local-user"
    reason: str = ""
    request_id: str = ""


class ControlActionResponse(BaseModel):
    accepted: bool
    action: str
    deployment_id: str
    event_id: str
    status: str
