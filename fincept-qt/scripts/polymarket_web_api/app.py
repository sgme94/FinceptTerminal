from __future__ import annotations

import os

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .control import accept_control_action, decide_proposal
from .repository import PolymarketRepository
from .schemas import (
    AuditEventList,
    BotStatus,
    CandidateList,
    ControlActionRequest,
    ControlActionResponse,
    PaperPositionList,
    PaperTradeList,
    ProposalList,
    SignalList,
    SkipList,
)


def create_app(*, db_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("POLYMARKET_WEB_DB", ".polymarket-web.sqlite")
    repo = PolymarketRepository(db_path)
    app = FastAPI(title="Polymarket Web Terminal API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:4177", "http://localhost:4177"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/bot/status", response_model=BotStatus)
    def get_bot_status() -> BotStatus:
        return BotStatus(db_path=db_path)

    @app.get("/api/audit", response_model=AuditEventList)
    def get_audit(deployment_id: str = "default") -> AuditEventList:
        return AuditEventList(events=repo.list_audit(deployment_id))

    @app.get("/api/proposals", response_model=ProposalList)
    def get_proposals(deployment_id: str = "default") -> ProposalList:
        return ProposalList(proposals=repo.list_proposals(deployment_id))

    @app.get("/api/candidates", response_model=CandidateList)
    def get_candidates(deployment_id: str = "default") -> CandidateList:
        return CandidateList(candidates=repo.list_candidates(deployment_id))

    @app.get("/api/signals", response_model=SignalList)
    def get_signals(deployment_id: str = "default") -> SignalList:
        return SignalList(signals=repo.list_signals(deployment_id))

    @app.get("/api/skips", response_model=SkipList)
    def get_skips(deployment_id: str = "default") -> SkipList:
        return SkipList(skips=repo.list_skips(deployment_id))

    @app.get("/api/trades", response_model=PaperTradeList)
    def get_trades(deployment_id: str = "default") -> PaperTradeList:
        return PaperTradeList(trades=repo.list_trades(deployment_id))

    @app.get("/api/positions", response_model=PaperPositionList)
    def get_positions(deployment_id: str = "default") -> PaperPositionList:
        return PaperPositionList(positions=repo.list_positions(deployment_id))

    @app.post("/api/control/start", response_model=ControlActionResponse, status_code=status.HTTP_202_ACCEPTED)
    def start_bot(request: ControlActionRequest) -> ControlActionResponse:
        return accept_control_action(repo, "start", request)

    @app.post("/api/control/stop", response_model=ControlActionResponse, status_code=status.HTTP_202_ACCEPTED)
    def stop_bot(request: ControlActionRequest) -> ControlActionResponse:
        return accept_control_action(repo, "stop", request)

    @app.post("/api/control/kill-switch", response_model=ControlActionResponse, status_code=status.HTTP_202_ACCEPTED)
    def kill_switch(request: ControlActionRequest) -> ControlActionResponse:
        return accept_control_action(repo, "kill_switch", request)

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
