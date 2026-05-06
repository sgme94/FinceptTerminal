from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ALGO_ROOT = Path(__file__).resolve().parents[1] / "algo_trading"
if str(ALGO_ROOT) not in sys.path:
    sys.path.insert(0, str(ALGO_ROOT))

from polymarket_store import (  # noqa: E402
    ensure_polymarket_schema,
    list_audit_events,
    list_trade_proposals,
    record_audit_event,
    update_trade_proposal_status,
)


class ProposalNotFoundError(Exception):
    pass


class InvalidProposalStateError(Exception):
    pass


def parse_features_json(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


class PolymarketRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        ensure_polymarket_schema(conn)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def list_audit(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return list_audit_events(conn, deployment_id)

    def list_proposals(self, deployment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
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
            update_trade_proposal_status(conn, proposal_id, status, actor_id, now, reason)
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
