from __future__ import annotations

import os

from fastapi import FastAPI, status

from .control import accept_control_action, decide_proposal
from .repository import PolymarketRepository
from .schemas import (
    AuditEventList,
    BotStatus,
    ControlActionRequest,
    ControlActionResponse,
    ProposalList,
)


def create_app(*, db_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("POLYMARKET_WEB_DB", ".polymarket-web.sqlite")
    repo = PolymarketRepository(db_path)
    app = FastAPI(title="Polymarket Web Terminal API")

    @app.get("/api/bot/status", response_model=BotStatus)
    def get_bot_status() -> BotStatus:
        return BotStatus(db_path=db_path)

    @app.get("/api/audit", response_model=AuditEventList)
    def get_audit(deployment_id: str = "default") -> AuditEventList:
        return AuditEventList(events=repo.list_audit(deployment_id))

    @app.get("/api/proposals", response_model=ProposalList)
    def get_proposals(deployment_id: str = "default") -> ProposalList:
        return ProposalList(proposals=repo.list_proposals(deployment_id))

    @app.post("/api/control/start", response_model=ControlActionResponse, status_code=status.HTTP_202_ACCEPTED)
    def start_bot(request: ControlActionRequest) -> ControlActionResponse:
        return accept_control_action(repo, "start", request)

    @app.post("/api/control/stop", response_model=ControlActionResponse, status_code=status.HTTP_202_ACCEPTED)
    def stop_bot(request: ControlActionRequest) -> ControlActionResponse:
        return accept_control_action(repo, "stop", request)

    @app.post(
        "/api/proposals/{proposal_id}/approve",
        response_model=ControlActionResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def approve_proposal(proposal_id: str, request: ControlActionRequest) -> ControlActionResponse:
        return decide_proposal(repo, proposal_id, "approved", request)

    @app.post(
        "/api/proposals/{proposal_id}/reject",
        response_model=ControlActionResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def reject_proposal(proposal_id: str, request: ControlActionRequest) -> ControlActionResponse:
        return decide_proposal(repo, proposal_id, "rejected", request)

    return app
