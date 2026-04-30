from __future__ import annotations

import json
import sqlite3

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
