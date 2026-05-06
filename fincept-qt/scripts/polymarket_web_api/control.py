from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status as http_status

from .repository import PolymarketRepository, ProposalNotFoundError
from .schemas import ControlActionRequest, ControlActionResponse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def proposal_action(status: str) -> str:
    return {"approved": "approve", "rejected": "reject"}[status]


def accept_control_action(
    repo: PolymarketRepository,
    action: str,
    request: ControlActionRequest,
) -> ControlActionResponse:
    event_id = repo.record_audit(
        deployment_id=request.deployment_id,
        strategy_id=request.strategy_id,
        actor_id=request.actor_id,
        action=action,
        entity_type="deployment",
        entity_id=request.deployment_id,
        before={},
        after={"status": action},
        result="accepted",
        reason=request.reason,
        request_id=request.request_id,
        now=utc_now(),
    )
    return ControlActionResponse(
        accepted=True,
        action=action,
        deployment_id=request.deployment_id,
        event_id=event_id,
        status="accepted",
    )


def decide_proposal(
    repo: PolymarketRepository,
    proposal_id: str,
    status: str,
    request: ControlActionRequest,
) -> ControlActionResponse:
    try:
        event_id = repo.decide_proposal(
            proposal_id=proposal_id,
            deployment_id=request.deployment_id,
            strategy_id=request.strategy_id,
            status=status,
            actor_id=request.actor_id,
            reason=request.reason,
            request_id=request.request_id,
            now=utc_now(),
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="proposal_not_found") from exc
    return ControlActionResponse(
        accepted=True,
        action=proposal_action(status),
        deployment_id=request.deployment_id,
        event_id=event_id,
        status="accepted",
    )
