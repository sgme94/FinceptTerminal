from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALGO_ROOT = Path(__file__).resolve().parents[1] / "algo_trading"
if str(ALGO_ROOT) not in sys.path:
    sys.path.insert(0, str(ALGO_ROOT))

from polymarket_store import (  # noqa: E402
    ensure_polymarket_schema,
    list_audit_events,
    list_paper_positions,
    list_paper_trades,
    list_trade_proposals,
    record_audit_event,
    update_trade_proposal_status,
)
from poly_alpha_promotion import (  # noqa: E402
    create_paper_proposal_from_promotion,
    evaluate_promotion,
)
from poly_alpha_promotion import record_proposal_decision as record_poly_alpha_proposal_decision  # noqa: E402
from poly_alpha_scanner import (  # noqa: E402
    build_evidence_pack,
    decide_exploration,
    run_deterministic_scan,
)
from poly_alpha_store import (  # noqa: E402
    ensure_poly_alpha_schema,
    list_agent_findings,
    list_config_versions,
    list_documents,
    list_event_market_links,
    list_events,
    list_evidence_packs,
    list_exploration_decisions,
    list_market_snapshots,
    list_opportunities,
    list_poly_alpha_audit_events,
    list_promotion_decisions,
    list_research_runs,
    list_scan_results,
    list_scan_runs,
    list_shadow_signals,
    list_source_sets,
    list_strategy_versions,
    list_validation_results,
    record_research_run,
)
from poly_alpha_validation import run_signal_validation  # noqa: E402


POLY_ALPHA_LISTERS = {
    "config-versions": list_config_versions,
    "source-sets": list_source_sets,
    "strategy-versions": list_strategy_versions,
    "documents": list_documents,
    "events": list_events,
    "links": list_event_market_links,
    "research-runs": list_research_runs,
    "findings": list_agent_findings,
    "scan-runs": list_scan_runs,
    "scan-results": list_scan_results,
    "opportunities": list_opportunities,
    "evidence-packs": list_evidence_packs,
    "exploration-decisions": list_exploration_decisions,
    "market-snapshots": list_market_snapshots,
    "shadow-signals": list_shadow_signals,
    "validations": list_validation_results,
    "promotions": list_promotion_decisions,
    "audit": list_poly_alpha_audit_events,
}


class ProposalNotFoundError(Exception):
    pass


class InvalidProposalStateError(Exception):
    pass


class ProposalExpiredError(Exception):
    pass


def parse_features_json(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def is_past_timestamp(value: str | None, now: str) -> bool:
    if not value:
        return False
    expires_at = _parse_utc(value)
    now_dt = _parse_utc(now)
    return expires_at is not None and now_dt is not None and expires_at <= now_dt


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_proposal(conn: sqlite3.Connection, deployment_id: str, proposal_id: str) -> dict[str, Any] | None:
    return next((item for item in list_trade_proposals(conn, deployment_id) if item["proposal_id"] == proposal_id), None)


def is_poly_alpha_paper_proposal(proposal: dict[str, Any]) -> bool:
    features = proposal.get("features") or {}
    return features.get("source") == "poly_alpha" and features.get("paper_only") is True


def require_poly_alpha_manual_research_lineage(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    evidence_pack_id: str,
    strategy_version_id: str,
    event_id: str,
    venue: str,
    venue_market_id: str,
) -> None:
    strategies = {row["strategy_version_id"] for row in list_strategy_versions(conn)}
    if strategy_version_id not in strategies:
        raise ValueError(f"Unknown strategy_version_id: {strategy_version_id}")

    opportunity = next(
        (row for row in list_opportunities(conn) if row["opportunity_id"] == opportunity_id),
        None,
    )
    if opportunity is None:
        raise ValueError(f"Unknown opportunity_id: {opportunity_id}")
    if opportunity["strategy_version_id"] != strategy_version_id:
        raise ValueError("Manual research opportunity strategy_version_id mismatch")
    if venue and opportunity["venue"] != venue:
        raise ValueError("Manual research opportunity venue mismatch")
    if venue_market_id and opportunity["venue_market_id"] != venue_market_id:
        raise ValueError("Manual research opportunity venue_market_id mismatch")

    evidence_pack = next(
        (row for row in list_evidence_packs(conn) if row["evidence_pack_id"] == evidence_pack_id),
        None,
    )
    if evidence_pack is None:
        raise ValueError(f"Unknown evidence_pack_id: {evidence_pack_id}")
    if evidence_pack["opportunity_id"] != opportunity_id:
        raise ValueError("Manual research evidence pack opportunity_id mismatch")
    if evidence_pack["strategy_version_id"] != strategy_version_id:
        raise ValueError("Manual research evidence pack strategy_version_id mismatch")
    if event_id and event_id not in evidence_pack["event_ids"]:
        raise ValueError("Manual research event_id is not in evidence pack")


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class PolymarketRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        ensure_polymarket_schema(conn)
        ensure_poly_alpha_schema(conn)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def list_poly_alpha(self, resource: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return POLY_ALPHA_LISTERS[resource](conn)

    def start_manual_research_run(
        self,
        *,
        opportunity_id: str,
        evidence_pack_id: str,
        strategy_version_id: str,
        event_id: str,
        venue: str,
        venue_market_id: str,
        requested_by: str,
        config: dict[str, Any],
        now: str,
    ) -> str:
        with self.connect() as conn:
            require_poly_alpha_manual_research_lineage(
                conn,
                opportunity_id=opportunity_id,
                evidence_pack_id=evidence_pack_id,
                strategy_version_id=strategy_version_id,
                event_id=event_id,
                venue=venue,
                venue_market_id=venue_market_id,
            )
            return record_research_run(
                conn,
                trigger_type="manual_task",
                opportunity_id=opportunity_id,
                evidence_pack_id=evidence_pack_id,
                strategy_version_id=strategy_version_id,
                event_id=event_id,
                venue=venue,
                venue_market_id=venue_market_id,
                requested_by=requested_by,
                started_at=now,
                status="running",
                model_config=config,
                created_at=now,
                write_audit=True,
            )

    def run_poly_alpha_deterministic_scan(
        self,
        *,
        strategy_version_id: str,
        config: dict[str, Any],
        source_documents: list[dict[str, Any]],
        market_snapshots: list[dict[str, Any]],
        now: str,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            return run_deterministic_scan(
                conn,
                strategy_version_id,
                config,
                source_documents,
                market_snapshots,
                now,
            )

    def build_poly_alpha_evidence_pack(
        self,
        *,
        opportunity_id: str,
        document_ids: list[str],
        snapshot_ids: list[str],
        event_ids: list[str],
        now: str,
    ) -> str:
        with self.connect() as conn:
            return build_evidence_pack(conn, opportunity_id, document_ids, snapshot_ids, event_ids, now)

    def decide_poly_alpha_exploration(
        self,
        *,
        opportunity_id: str,
        evidence_pack_id: str,
        config: dict[str, Any],
        now: str,
    ) -> str:
        with self.connect() as conn:
            return decide_exploration(conn, opportunity_id, evidence_pack_id, config, now)

    def run_poly_alpha_validation(
        self,
        *,
        shadow_signal_id: str,
        config: dict[str, Any],
        now: str,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            return run_signal_validation(conn, shadow_signal_id, config, now)

    def evaluate_poly_alpha_promotion(
        self,
        *,
        shadow_signal_id: str,
        config: dict[str, Any],
        now: str,
    ) -> str:
        with self.connect() as conn:
            return evaluate_promotion(conn, shadow_signal_id, config, now)

    def create_poly_alpha_paper_proposal(
        self,
        *,
        promotion_id: str,
        deployment_id: str,
        now: str,
    ) -> str:
        with self.connect() as conn:
            return create_paper_proposal_from_promotion(conn, promotion_id, deployment_id, now)

    def list_audit(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return list_audit_events(conn, deployment_id)

    def list_proposals(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            expire_past_ttl_proposals(conn, deployment_id, utc_now())
            return list_trade_proposals(conn, deployment_id)

    def list_candidates(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT market_id, condition_id, asset_id, outcome, price, volume, liquidity,
                       fetched_at, created_at
                FROM algo_polymarket_candidates
                WHERE deployment_id = ?
                ORDER BY created_at, market_id
                """,
                (deployment_id,),
            ).fetchall()
            return [
                {
                    "market_id": row[0],
                    "condition_id": row[1],
                    "asset_id": row[2],
                    "outcome": row[3],
                    "price": row[4],
                    "volume": row[5],
                    "liquidity": row[6],
                    "fetched_at": row[7],
                    "created_at": row[8],
                }
                for row in rows
            ]

    def list_signals(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, asset_id, action, entry_price, estimated_probability, edge, confidence,
                       reason, features_json, created_at
                FROM algo_polymarket_signals
                WHERE deployment_id = ?
                ORDER BY created_at, id
                """,
                (deployment_id,),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "asset_id": row[1],
                    "action": row[2],
                    "entry_price": row[3],
                    "estimated_probability": row[4],
                    "edge": row[5],
                    "confidence": row[6],
                    "reason": row[7],
                    "features": parse_features_json(row[8]),
                    "created_at": row[9],
                }
                for row in rows
            ]

    def list_skips(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, market_id, asset_id, reason, detail, created_at
                FROM algo_polymarket_skips
                WHERE deployment_id = ?
                ORDER BY created_at, id
                """,
                (deployment_id,),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "market_id": row[1],
                    "asset_id": row[2],
                    "reason": row[3],
                    "detail": row[4],
                    "created_at": row[5],
                }
                for row in rows
            ]

    def list_trades(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return list_paper_trades(conn, deployment_id)

    def list_positions(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return list_paper_positions(conn, deployment_id)

    def record_audit(
        self,
        *,
        deployment_id: str,
        strategy_id: str,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before: dict[str, Any],
        after: dict[str, Any],
        result: str,
        reason: str,
        request_id: str,
        now: str,
    ) -> str:
        with self.connect() as conn:
            return record_audit_event(
                conn,
                deployment_id=deployment_id,
                strategy_id=strategy_id,
                actor_type="user",
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before=before,
                after=after,
                result=result,
                reason=reason,
                request_id=request_id,
                now=now,
            )

    def decide_proposal(
        self,
        *,
        proposal_id: str,
        deployment_id: str,
        strategy_id: str,
        status: str,
        actor_id: str,
        reason: str,
        request_id: str,
        now: str,
    ) -> str:
        with self.connect() as conn:
            proposals = list_trade_proposals(conn, deployment_id)
            before = next((item for item in proposals if item["proposal_id"] == proposal_id), None)
            action = {"approved": "approve", "rejected": "reject"}[status]
            if before is None:
                record_audit_event(
                    conn,
                    deployment_id=deployment_id,
                    strategy_id=strategy_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action=action,
                    entity_type="proposal",
                    entity_id=proposal_id,
                    before={},
                    after={},
                    result="failed",
                    reason=reason or "proposal_not_found",
                    request_id=request_id,
                    now=now,
                )
                conn.commit()
                raise ProposalNotFoundError(proposal_id)
            if before["status"] != "proposed":
                record_audit_event(
                    conn,
                    deployment_id=deployment_id,
                    strategy_id=strategy_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action=action,
                    entity_type="proposal",
                    entity_id=proposal_id,
                    before=before,
                    after=dict(before),
                    result="failed",
                    reason="proposal_not_proposed",
                    request_id=request_id,
                    now=now,
                )
                conn.commit()
                raise InvalidProposalStateError(proposal_id)
            if is_past_timestamp(before.get("expires_at"), now):
                after = dict(before)
                after["status"] = "expired"
                updated = update_trade_proposal_status(
                    conn,
                    proposal_id,
                    "expired",
                    before.get("decided_by", ""),
                    before.get("decided_at", ""),
                    before.get("decision_reason", ""),
                    deployment_id=deployment_id,
                    expected_status="proposed",
                )
                if not updated:
                    current = find_proposal(conn, deployment_id, proposal_id) or dict(before)
                    record_audit_event(
                        conn,
                        deployment_id=deployment_id,
                        strategy_id=strategy_id,
                        actor_type="user",
                        actor_id=actor_id,
                        action=action,
                        entity_type="proposal",
                        entity_id=proposal_id,
                        before=before,
                        after=current,
                        result="failed",
                        reason="proposal_not_proposed",
                        request_id=request_id,
                        now=now,
                    )
                    conn.commit()
                    raise InvalidProposalStateError(proposal_id)
                record_audit_event(
                    conn,
                    deployment_id=deployment_id,
                    strategy_id=strategy_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action=action,
                    entity_type="proposal",
                    entity_id=proposal_id,
                    before=before,
                    after=after,
                    result="failed",
                    reason="proposal_expired",
                    request_id=request_id,
                    now=now,
                )
                conn.commit()
                raise ProposalExpiredError(proposal_id)
            if is_poly_alpha_paper_proposal(before):
                try:
                    event_id = record_poly_alpha_proposal_decision(
                        conn,
                        proposal_id,
                        status,
                        actor_id,
                        now,
                        reason,
                        request_id=request_id,
                    )
                except ValueError as exc:
                    current = find_proposal(conn, deployment_id, proposal_id) or dict(before)
                    record_audit_event(
                        conn,
                        deployment_id=deployment_id,
                        strategy_id=strategy_id,
                        actor_type="user",
                        actor_id=actor_id,
                        action=action,
                        entity_type="proposal",
                        entity_id=proposal_id,
                        before=before,
                        after=current,
                        result="failed",
                        reason="invalid_poly_alpha_lineage",
                        request_id=request_id,
                        now=now,
                    )
                    conn.commit()
                    raise InvalidProposalStateError(proposal_id) from exc
                if not event_id:
                    current = find_proposal(conn, deployment_id, proposal_id) or dict(before)
                    record_audit_event(
                        conn,
                        deployment_id=deployment_id,
                        strategy_id=strategy_id,
                        actor_type="user",
                        actor_id=actor_id,
                        action=action,
                        entity_type="proposal",
                        entity_id=proposal_id,
                        before=before,
                        after=current,
                        result="failed",
                        reason="proposal_not_proposed",
                        request_id=request_id,
                        now=now,
                    )
                    conn.commit()
                    raise InvalidProposalStateError(proposal_id)
                return event_id
            updated = update_trade_proposal_status(
                conn,
                proposal_id,
                status,
                actor_id,
                now,
                reason,
                deployment_id=deployment_id,
                expected_status="proposed",
            )
            if not updated:
                current = find_proposal(conn, deployment_id, proposal_id) or dict(before)
                record_audit_event(
                    conn,
                    deployment_id=deployment_id,
                    strategy_id=strategy_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action=action,
                    entity_type="proposal",
                    entity_id=proposal_id,
                    before=before,
                    after=current,
                    result="failed",
                    reason="proposal_not_proposed",
                    request_id=request_id,
                    now=now,
                )
                conn.commit()
                raise InvalidProposalStateError(proposal_id)
            after = dict(before)
            after.update(
                {
                    "status": status,
                    "decided_by": actor_id,
                    "decided_at": now,
                    "decision_reason": reason,
                }
            )
            return record_audit_event(
                conn,
                deployment_id=deployment_id,
                strategy_id=strategy_id,
                actor_type="user",
                actor_id=actor_id,
                action=action,
                entity_type="proposal",
                entity_id=proposal_id,
                before=before,
                after=after,
                result="accepted",
                reason=reason,
                request_id=request_id,
                now=now,
            )

    def kill_switch(
        self,
        *,
        deployment_id: str,
        strategy_id: str,
        actor_id: str,
        reason: str,
        request_id: str,
        now: str,
    ) -> str:
        with self.connect() as conn:
            event_id = record_audit_event(
                conn,
                deployment_id=deployment_id,
                strategy_id=strategy_id,
                actor_type="user",
                actor_id=actor_id,
                action="kill_switch",
                entity_type="deployment",
                entity_id=deployment_id,
                before={},
                after={"status": "kill_switch"},
                result="accepted",
                reason=reason,
                request_id=request_id,
                now=now,
            )
            open_proposals = [
                proposal
                for proposal in list_trade_proposals(conn, deployment_id)
                if proposal["status"] in {"proposed", "approved"}
            ]
            for proposal in open_proposals:
                after = dict(proposal)
                after["status"] = "cancelled"
                updated = update_trade_proposal_status(
                    conn,
                    proposal["proposal_id"],
                    "cancelled",
                    actor_id,
                    now,
                    reason or "kill_switch",
                    deployment_id=deployment_id,
                    expected_status=proposal["status"],
                )
                if not updated:
                    after = find_proposal(conn, deployment_id, proposal["proposal_id"]) or after
                record_audit_event(
                    conn,
                    deployment_id=deployment_id,
                    strategy_id=proposal.get("strategy_id") or strategy_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action="proposal_cancelled",
                    entity_type="proposal",
                    entity_id=proposal["proposal_id"],
                    before=proposal,
                    after=after,
                    result="success" if updated else "failed",
                    reason=(reason or "kill_switch") if updated else "proposal_not_open",
                    request_id=request_id,
                    now=now,
                )
            return event_id


def expire_past_ttl_proposals(conn: sqlite3.Connection, deployment_id: str, now: str) -> None:
    for proposal in list_trade_proposals(conn, deployment_id):
        if proposal["status"] != "proposed" or not is_past_timestamp(proposal.get("expires_at"), now):
            continue
        after = dict(proposal)
        after["status"] = "expired"
        updated = update_trade_proposal_status(
            conn,
            proposal["proposal_id"],
            "expired",
            proposal.get("decided_by") or "",
            proposal.get("decided_at") or "",
            proposal.get("decision_reason") or "",
            deployment_id=deployment_id,
            expected_status="proposed",
        )
        if updated:
            record_audit_event(
                conn,
                deployment_id=deployment_id,
                strategy_id=proposal.get("strategy_id") or "",
                actor_type="system",
                actor_id="polymarket_web_api",
                action="proposal_expired",
                entity_type="proposal",
                entity_id=proposal["proposal_id"],
                before=proposal,
                after=after,
                result="failed",
                reason="proposal_expired",
                request_id="",
                now=now,
            )
