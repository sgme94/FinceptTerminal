from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


SENSITIVE_KEY_TOKENS = (
    "private_key",
    "api_secret",
    "api_key",
    "api_token",
    "secret",
    "clob",
    "live_trading",
    "live_order",
    "order_endpoint",
    "order_client",
)
SENSITIVE_VALUE_TOKENS = (
    "private_key",
    "api_secret",
    "api_key",
    "api_token",
    "secret",
    "live_trading",
    "live_order",
    "order_endpoint",
    "order_client",
    "clob_order",
)


def _contains_token(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in tokens)


def reject_sensitive_tree(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and _contains_token(key, SENSITIVE_KEY_TOKENS):
                raise ValueError("MVP paper-only API rejects live trading fields")
            reject_sensitive_tree(nested)
        return
    if isinstance(value, list):
        for nested in value:
            reject_sensitive_tree(nested)
        return
    if isinstance(value, str) and _contains_token(value, SENSITIVE_VALUE_TOKENS):
        raise ValueError("MVP paper-only API rejects live trading fields")


class StrictPolyAlphaControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_live_trading_payload(cls, data: Any) -> Any:
        reject_sensitive_tree(data)
        return data


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


class Candidate(BaseModel):
    market_id: str | None = None
    condition_id: str | None = None
    asset_id: str | None = None
    outcome: str | None = None
    price: float | None = None
    volume: float | None = None
    liquidity: float | None = None
    fetched_at: str | None = None
    created_at: str


class CandidateList(BaseModel):
    candidates: list[Candidate]


class Signal(BaseModel):
    id: int
    asset_id: str | None = None
    action: str | None = None
    entry_price: float | None = None
    estimated_probability: float | None = None
    edge: float | None = None
    confidence: float | None = None
    reason: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class SignalList(BaseModel):
    signals: list[Signal]


class Skip(BaseModel):
    id: int
    market_id: str | None = None
    asset_id: str | None = None
    reason: str
    detail: str = ""
    created_at: str


class SkipList(BaseModel):
    skips: list[Skip]


class PaperTrade(BaseModel):
    id: int
    deployment_id: str
    asset_id: str | None = None
    side: str | None = None
    size: float | None = None
    price: float | None = None
    realized_pnl: float | None = None
    reason: str = ""
    created_at: str


class PaperTradeList(BaseModel):
    trades: list[PaperTrade]


class PaperPosition(BaseModel):
    deployment_id: str
    asset_id: str
    size: float
    avg_price: float
    realized_pnl: float | None = None
    updated_at: str


class PaperPositionList(BaseModel):
    positions: list[PaperPosition]


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


class PolyAlphaListResponse(BaseModel):
    items: list[dict[str, Any]]


class PolyAlphaControlResponse(BaseModel):
    accepted: bool
    action: str
    ids: dict[str, Any] = Field(default_factory=dict)
    status: str


class PolyAlphaManualResearchRequest(StrictPolyAlphaControlRequest):
    opportunity_id: str
    evidence_pack_id: str = ""
    strategy_version_id: str
    event_id: str = ""
    venue: str = "polymarket"
    venue_market_id: str = ""
    requested_by: str = "local-user"
    config: dict[str, Any] = Field(default_factory=dict)


class PolyAlphaDeterministicScanRequest(StrictPolyAlphaControlRequest):
    strategy_version_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    market_snapshots: list[dict[str, Any]] = Field(default_factory=list)


class PolyAlphaEvidencePackRequest(StrictPolyAlphaControlRequest):
    opportunity_id: str
    document_ids: list[str] = Field(default_factory=list)
    snapshot_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)


class PolyAlphaExplorationDecisionRequest(StrictPolyAlphaControlRequest):
    opportunity_id: str
    evidence_pack_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class PolyAlphaValidationRequest(StrictPolyAlphaControlRequest):
    shadow_signal_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class PolyAlphaPromotionRequest(StrictPolyAlphaControlRequest):
    shadow_signal_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class PolyAlphaPaperProposalRequest(StrictPolyAlphaControlRequest):
    promotion_id: str
    deployment_id: str
