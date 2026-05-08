from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .control import accept_control_action, decide_proposal
from .repository import POLY_ALPHA_LISTERS, PolymarketRepository, utc_now
from .schemas import (
    AuditEventList,
    BotStatus,
    CandidateList,
    ControlActionRequest,
    ControlActionResponse,
    PaperPositionList,
    PaperTradeList,
    PolyAlphaControlResponse,
    PolyAlphaDeterministicScanRequest,
    PolyAlphaEvidencePackRequest,
    PolyAlphaExplorationDecisionRequest,
    PolyAlphaListResponse,
    PolyAlphaManualResearchRequest,
    PolyAlphaPaperProposalRequest,
    PolyAlphaPromotionRequest,
    PolyAlphaValidationRequest,
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

    def poly_alpha_response(action: str, ids: dict) -> PolyAlphaControlResponse:
        return PolyAlphaControlResponse(accepted=True, action=action, ids=ids, status="accepted")

    def poly_alpha_bad_request(exc: ValueError) -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    def poly_alpha_list(resource: str) -> PolyAlphaListResponse:
        return PolyAlphaListResponse(items=repo.list_poly_alpha(resource))

    def add_poly_alpha_list_route(resource: str) -> None:
        @app.get(f"/api/poly-alpha/{resource}", response_model=PolyAlphaListResponse)
        def get_poly_alpha_resource() -> PolyAlphaListResponse:
            return poly_alpha_list(resource)

    for poly_alpha_resource in POLY_ALPHA_LISTERS:
        if poly_alpha_resource == "audit":
            continue
        add_poly_alpha_list_route(poly_alpha_resource)

    @app.get("/api/poly-alpha/audit", response_model=PolyAlphaListResponse)
    def get_poly_alpha_audit() -> PolyAlphaListResponse:
        return poly_alpha_list("audit")

    @app.post(
        "/api/poly-alpha/research-runs/manual",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def start_poly_alpha_manual_research(request: PolyAlphaManualResearchRequest) -> PolyAlphaControlResponse:
        try:
            run_id = repo.start_manual_research_run(
                opportunity_id=request.opportunity_id,
                evidence_pack_id=request.evidence_pack_id,
                strategy_version_id=request.strategy_version_id,
                event_id=request.event_id,
                venue=request.venue,
                venue_market_id=request.venue_market_id,
                requested_by=request.requested_by,
                config=request.config,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("research_started", {"run_id": run_id})

    @app.post(
        "/api/poly-alpha/scan-runs/deterministic",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def run_poly_alpha_scan(request: PolyAlphaDeterministicScanRequest) -> PolyAlphaControlResponse:
        try:
            result = repo.run_poly_alpha_deterministic_scan(
                strategy_version_id=request.strategy_version_id,
                config=request.config,
                source_documents=request.source_documents,
                market_snapshots=request.market_snapshots,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("deterministic_scan_completed", result)

    @app.post(
        "/api/poly-alpha/evidence-packs/build",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def build_poly_alpha_pack(request: PolyAlphaEvidencePackRequest) -> PolyAlphaControlResponse:
        try:
            evidence_pack_id = repo.build_poly_alpha_evidence_pack(
                opportunity_id=request.opportunity_id,
                document_ids=request.document_ids,
                snapshot_ids=request.snapshot_ids,
                event_ids=request.event_ids,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("evidence_pack_created", {"evidence_pack_id": evidence_pack_id})

    @app.post(
        "/api/poly-alpha/exploration-decisions/decide",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def decide_poly_alpha_exploration(request: PolyAlphaExplorationDecisionRequest) -> PolyAlphaControlResponse:
        try:
            exploration_id = repo.decide_poly_alpha_exploration(
                opportunity_id=request.opportunity_id,
                evidence_pack_id=request.evidence_pack_id,
                config=request.config,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("exploration_decided", {"exploration_id": exploration_id})

    @app.post(
        "/api/poly-alpha/validations/run",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def run_poly_alpha_signal_validation(request: PolyAlphaValidationRequest) -> PolyAlphaControlResponse:
        try:
            result = repo.run_poly_alpha_validation(
                shadow_signal_id=request.shadow_signal_id,
                config=request.config,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("validation_completed", result)

    @app.post(
        "/api/poly-alpha/promotions/evaluate",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def evaluate_poly_alpha_signal_promotion(request: PolyAlphaPromotionRequest) -> PolyAlphaControlResponse:
        try:
            promotion_id = repo.evaluate_poly_alpha_promotion(
                shadow_signal_id=request.shadow_signal_id,
                config=request.config,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("promotion_evaluated", {"promotion_id": promotion_id})

    @app.post(
        "/api/poly-alpha/paper-proposals/create",
        response_model=PolyAlphaControlResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_poly_alpha_paper_proposal(request: PolyAlphaPaperProposalRequest) -> PolyAlphaControlResponse:
        try:
            proposal_id = repo.create_poly_alpha_paper_proposal(
                promotion_id=request.promotion_id,
                deployment_id=request.deployment_id,
                now=utc_now(),
            )
        except ValueError as exc:
            raise poly_alpha_bad_request(exc) from exc
        return poly_alpha_response("paper_proposal_created", {"proposal_id": proposal_id})

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
