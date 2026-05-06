from __future__ import annotations

import json
import sqlite3
import uuid

from polymarket_models import MarketCandidate, PaperFill, PaperPosition, SignalDecision
from polymarket_scanner import SkippedMarket


def ensure_polymarket_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            market_id TEXT,
            condition_id TEXT,
            asset_id TEXT,
            outcome TEXT,
            price REAL,
            volume REAL,
            liquidity REAL,
            fetched_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            asset_id TEXT,
            action TEXT,
            entry_price REAL,
            estimated_probability REAL,
            edge REAL,
            confidence REAL,
            reason TEXT,
            features_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_skips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            market_id TEXT,
            asset_id TEXT,
            reason TEXT NOT NULL,
            detail TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT NOT NULL,
            asset_id TEXT,
            side TEXT,
            size REAL,
            price REAL,
            realized_pnl REAL DEFAULT 0,
            reason TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_paper_positions (
            deployment_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            size REAL NOT NULL,
            avg_price REAL NOT NULL,
            realized_pnl REAL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (deployment_id, asset_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_trade_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            deployment_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            market_id TEXT,
            condition_id TEXT,
            asset_id TEXT,
            side TEXT,
            price REAL,
            fill_trade_id TEXT DEFAULT '',
            estimated_probability REAL,
            edge REAL,
            confidence REAL,
            reason TEXT,
            features_json TEXT DEFAULT '{}',
            size REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            decided_by TEXT DEFAULT '',
            decided_at TEXT DEFAULT '',
            decision_reason TEXT DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_polymarket_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            deployment_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT DEFAULT '',
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT DEFAULT '',
            before_json TEXT DEFAULT '{}',
            after_json TEXT DEFAULT '{}',
            result TEXT NOT NULL,
            reason TEXT DEFAULT '',
            request_id TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )


def record_trade_proposal(
    conn: sqlite3.Connection,
    deployment_id: str,
    strategy_id: str,
    market_id: str,
    condition_id: str,
    signal: SignalDecision,
    size: float,
    now: str,
    expires_at: str,
) -> str:
    proposal_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO algo_polymarket_trade_proposals
            (proposal_id, deployment_id, strategy_id, market_id, condition_id, asset_id,
             side, price, fill_trade_id, estimated_probability, edge, confidence, reason,
             features_json, size, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal_id,
            deployment_id,
            strategy_id,
            market_id,
            condition_id,
            signal.asset_id,
            signal.action,
            signal.entry_price,
            "",
            signal.estimated_probability,
            signal.edge,
            signal.confidence,
            signal.reason,
            json.dumps(signal.features),
            size,
            "proposed",
            now,
            expires_at,
        ),
    )
    return proposal_id


def update_trade_proposal_status(
    conn: sqlite3.Connection,
    proposal_id: str,
    status: str,
    decided_by: str,
    decided_at: str,
    decision_reason: str,
) -> None:
    conn.execute(
        """
        UPDATE algo_polymarket_trade_proposals
        SET status = ?,
            decided_by = ?,
            decided_at = ?,
            decision_reason = ?
        WHERE proposal_id = ?
        """,
        (status, decided_by, decided_at, decision_reason, proposal_id),
    )


def list_trade_proposals(conn: sqlite3.Connection, deployment_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, proposal_id, deployment_id, strategy_id, market_id, condition_id, asset_id,
               side, price, fill_trade_id, estimated_probability, edge, confidence, reason,
               features_json, size, status, created_at, expires_at, decided_by, decided_at,
               decision_reason
        FROM algo_polymarket_trade_proposals
        WHERE deployment_id = ?
        ORDER BY created_at, proposal_id
        """,
        (deployment_id,),
    ).fetchall()
    return [
        {
            "id": row[0],
            "proposal_id": row[1],
            "deployment_id": row[2],
            "strategy_id": row[3],
            "market_id": row[4],
            "condition_id": row[5],
            "asset_id": row[6],
            "side": row[7],
            "price": row[8],
            "fill_trade_id": row[9],
            "estimated_probability": row[10],
            "edge": row[11],
            "confidence": row[12],
            "reason": row[13],
            "features": json.loads(row[14] or "{}"),
            "size": row[15],
            "status": row[16],
            "created_at": row[17],
            "expires_at": row[18],
            "decided_by": row[19],
            "decided_at": row[20],
            "decision_reason": row[21],
        }
        for row in rows
    ]


def record_audit_event(
    conn: sqlite3.Connection,
    deployment_id: str,
    strategy_id: str,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict,
    after: dict,
    result: str,
    reason: str,
    request_id: str,
    now: str,
) -> str:
    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO algo_polymarket_audit_events
            (event_id, deployment_id, strategy_id, actor_type, actor_id, action,
             entity_type, entity_id, before_json, after_json, result, reason,
             request_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            deployment_id,
            strategy_id,
            actor_type,
            actor_id,
            action,
            entity_type,
            entity_id,
            json.dumps(before),
            json.dumps(after),
            result,
            reason,
            request_id,
            now,
        ),
    )
    return event_id


def list_audit_events(conn: sqlite3.Connection, deployment_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT event_id, deployment_id, strategy_id, actor_type, actor_id, action,
               entity_type, entity_id, before_json, after_json, result, reason,
               request_id, created_at
        FROM algo_polymarket_audit_events
        WHERE deployment_id = ?
        ORDER BY created_at, event_id
        """,
        (deployment_id,),
    ).fetchall()
    return [
        {
            "event_id": row[0],
            "deployment_id": row[1],
            "strategy_id": row[2],
            "actor_type": row[3],
            "actor_id": row[4],
            "action": row[5],
            "entity_type": row[6],
            "entity_id": row[7],
            "before": json.loads(row[8] or "{}"),
            "after": json.loads(row[9] or "{}"),
            "result": row[10],
            "reason": row[11],
            "request_id": row[12],
            "created_at": row[13],
        }
        for row in rows
    ]


def record_candidate(conn: sqlite3.Connection, deployment_id: str, strategy_id: str, candidate: MarketCandidate, now: str) -> None:
    conn.execute(
        """
        INSERT INTO algo_polymarket_candidates
            (deployment_id, strategy_id, market_id, condition_id, asset_id, outcome,
             price, volume, liquidity, fetched_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            strategy_id,
            candidate.market_id,
            candidate.condition_id,
            candidate.asset_id,
            candidate.outcome,
            candidate.price,
            candidate.volume,
            candidate.liquidity,
            candidate.fetched_at,
            now,
        ),
    )


def record_skip(
    conn: sqlite3.Connection,
    deployment_id: str,
    reason: str,
    now: str,
    market_id: str = "",
    asset_id: str = "",
    detail: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO algo_polymarket_skips
            (deployment_id, market_id, asset_id, reason, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (deployment_id, market_id, asset_id, reason, detail, now),
    )


def record_scan_skip(conn: sqlite3.Connection, deployment_id: str, skipped: SkippedMarket, now: str) -> None:
    record_skip(conn, deployment_id, skipped.reason, now, market_id=skipped.market_id, detail=skipped.detail)


def record_signal(conn: sqlite3.Connection, deployment_id: str, signal: SignalDecision, now: str) -> None:
    conn.execute(
        """
        INSERT INTO algo_polymarket_signals
            (deployment_id, asset_id, action, entry_price, estimated_probability,
             edge, confidence, reason, features_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            signal.asset_id,
            signal.action,
            signal.entry_price,
            signal.estimated_probability,
            signal.edge,
            signal.confidence,
            signal.reason,
            json.dumps(signal.features),
            now,
        ),
    )


def record_trade(conn: sqlite3.Connection, deployment_id: str, fill: PaperFill, now: str) -> None:
    conn.execute(
        """
        INSERT INTO algo_polymarket_paper_trades
            (deployment_id, asset_id, side, size, price, realized_pnl, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (deployment_id, fill.asset_id, fill.side, fill.size, fill.price, fill.realized_pnl, fill.reason, now),
    )


def load_positions(conn: sqlite3.Connection, deployment_id: str) -> dict[str, PaperPosition]:
    rows = conn.execute(
        """
        SELECT asset_id, size, avg_price, realized_pnl
        FROM algo_polymarket_paper_positions
        WHERE deployment_id = ?
        """,
        (deployment_id,),
    ).fetchall()
    return {
        row[0]: PaperPosition(asset_id=row[0], size=float(row[1]), avg_price=float(row[2]), realized_pnl=float(row[3] or 0.0))
        for row in rows
    }


def upsert_position(conn: sqlite3.Connection, deployment_id: str, position: PaperPosition, now: str) -> None:
    conn.execute(
        """
        INSERT INTO algo_polymarket_paper_positions
            (deployment_id, asset_id, size, avg_price, realized_pnl, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(deployment_id, asset_id) DO UPDATE SET
            size = excluded.size,
            avg_price = excluded.avg_price,
            realized_pnl = excluded.realized_pnl,
            updated_at = excluded.updated_at
        """,
        (deployment_id, position.asset_id, position.size, position.avg_price, position.realized_pnl, now),
    )


def delete_position(conn: sqlite3.Connection, deployment_id: str, asset_id: str) -> None:
    conn.execute(
        "DELETE FROM algo_polymarket_paper_positions WHERE deployment_id = ? AND asset_id = ?",
        (deployment_id, asset_id),
    )
