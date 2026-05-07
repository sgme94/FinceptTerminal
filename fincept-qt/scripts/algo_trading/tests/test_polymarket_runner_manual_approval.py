import sqlite3
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_runner import run_polymarket_cycle
from polymarket_models import SignalDecision
from polymarket_store import (
    ensure_polymarket_schema,
    list_trade_proposals,
    record_trade_proposal,
    update_trade_proposal_status,
)


def test_manual_approval_creates_proposal_without_fill(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.execute("CREATE TABLE algo_strategies (id TEXT PRIMARY KEY, bot_config TEXT)")
    conn.execute(
        "INSERT INTO algo_strategies (id, bot_config) VALUES (?, ?)",
        (
            "strat-1",
            '{"approval_mode":"manual_approval","paper_order_size":10,"min_edge":0.01}',
        ),
    )
    conn.commit()
    conn.close()

    market_payload = {
        "fetched_at": "2026-05-06T00:00:00Z",
        "data": [
            {
                "id": "market-1",
                "conditionId": "cond-1",
                "question": "Will event happen?",
                "active": True,
                "closed": False,
                "volume": 10000,
                "liquidity": 5000,
                "endDate": "2026-06-06T00:00:00Z",
                "outcomes": '["Yes"]',
                "outcomePrices": '["0.4"]',
                "clobTokenIds": '["asset-1"]',
            }
        ],
    }
    order_books = {
        "asset-1": {
            "source_api": "fixture",
            "fetched_at": "2026-05-06T00:00:00Z",
            "data": {
                "asset_id": "asset-1",
                "bids": [{"price": "0.39", "size": "100"}],
                "asks": [{"price": "0.40", "size": "100"}],
            },
        }
    }
    edge_overrides = {
        "asset-1": {
            "action": "buy",
            "reason": "test_override",
            "estimated_probability": 0.55,
            "edge": 0.15,
            "confidence": 0.8,
        }
    }

    result = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=market_payload,
        order_books=order_books,
        edge_overrides=edge_overrides,
        now="2026-05-06T00:00:00Z",
    )

    conn = sqlite3.connect(db_path)
    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    trades = conn.execute("SELECT COUNT(*) FROM algo_polymarket_paper_trades").fetchone()[0]
    audit_actions = [
        row[0]
        for row in conn.execute("SELECT action FROM algo_polymarket_audit_events ORDER BY id").fetchall()
    ]
    conn.close()

    assert result["proposals"] == 1
    assert result["fills"] == 0
    assert len(proposals) == 1
    assert proposals[0]["status"] == "proposed"
    assert trades == 0
    assert audit_actions == ["proposal_created"]


def test_manual_approval_cycle_does_not_duplicate_open_proposal(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.execute("CREATE TABLE algo_strategies (id TEXT PRIMARY KEY, bot_config TEXT)")
    conn.execute(
        "INSERT INTO algo_strategies (id, bot_config) VALUES (?, ?)",
        (
            "strat-1",
            '{"approval_mode":"manual_approval","paper_order_size":10,"min_edge":0.01}',
        ),
    )
    conn.commit()
    conn.close()

    market_payload = {
        "fetched_at": "2026-05-06T00:00:00Z",
        "data": [
            {
                "id": "market-1",
                "conditionId": "cond-1",
                "question": "Will event happen?",
                "active": True,
                "closed": False,
                "volume": 10000,
                "liquidity": 5000,
                "endDate": "2026-06-06T00:00:00Z",
                "outcomes": '["Yes"]',
                "outcomePrices": '["0.4"]',
                "clobTokenIds": '["asset-1"]',
            }
        ],
    }
    order_books = {
        "asset-1": {
            "source_api": "fixture",
            "fetched_at": "2026-05-06T00:00:00Z",
            "data": {
                "asset_id": "asset-1",
                "bids": [{"price": "0.39", "size": "100"}],
                "asks": [{"price": "0.40", "size": "100"}],
            },
        }
    }
    edge_overrides = {
        "asset-1": {
            "action": "buy",
            "reason": "test_override",
            "estimated_probability": 0.55,
            "edge": 0.15,
            "confidence": 0.8,
        }
    }

    first = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=market_payload,
        order_books=order_books,
        edge_overrides=edge_overrides,
        now="2026-05-06T00:00:00Z",
    )
    second = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=market_payload,
        order_books=order_books,
        edge_overrides=edge_overrides,
        now="2026-05-06T00:00:20Z",
    )

    conn = sqlite3.connect(db_path)
    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    latest_skip = conn.execute("SELECT reason FROM algo_polymarket_skips ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()

    assert first["proposals"] == 1
    assert second["proposals"] == 0
    assert len(proposals) == 1
    assert latest_skip == "open_proposal_exists"


def test_approved_proposal_rechecks_book_and_risk_before_paper_fill(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.execute("CREATE TABLE algo_strategies (id TEXT PRIMARY KEY, bot_config TEXT)")
    conn.execute(
        "INSERT INTO algo_strategies (id, bot_config) VALUES (?, ?)",
        (
            "strat-1",
            '{"approval_mode":"manual_approval","paper_order_size":10,"min_edge":0.01}',
        ),
    )
    signal = SignalDecision(
        asset_id="asset-1",
        action="buy",
        entry_price=0.40,
        estimated_probability=0.55,
        edge=0.15,
        confidence=0.8,
        reason="manual approval fill",
    )
    proposal_id = record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-1",
        condition_id="cond-1",
        signal=signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:02:00Z",
    )
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="approved",
        decided_by="reviewer",
        decided_at="2026-05-06T00:00:10Z",
        decision_reason="manual approve",
    )
    conn.commit()
    conn.close()

    result = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload={"fetched_at": "2026-05-06T00:00:20Z", "data": []},
        order_books={
            "asset-1": {
                "source_api": "fixture",
                "fetched_at": "2026-05-06T00:00:20Z",
                "data": {
                    "asset_id": "asset-1",
                    "bids": [{"price": "0.39", "size": "100"}],
                    "asks": [{"price": "0.40", "size": "100"}],
                },
            }
        },
        now="2026-05-06T00:00:20Z",
    )

    conn = sqlite3.connect(db_path)
    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    trade_count = conn.execute("SELECT COUNT(*) FROM algo_polymarket_paper_trades").fetchone()[0]
    position_count = conn.execute("SELECT COUNT(*) FROM algo_polymarket_paper_positions").fetchone()[0]
    audit_actions = [
        row[0]
        for row in conn.execute("SELECT action FROM algo_polymarket_audit_events ORDER BY id").fetchall()
    ]
    conn.close()

    assert result["fills"] == 1
    assert proposals[0]["status"] == "filled"
    assert proposals[0]["fill_trade_id"]
    assert trade_count == 1
    assert position_count == 1
    assert audit_actions == ["fill_simulated"]


def test_approved_proposal_expires_before_paper_fill(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    signal = SignalDecision(asset_id="asset-1", action="buy", entry_price=0.40, reason="expired")
    proposal_id = record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-1",
        condition_id="cond-1",
        signal=signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:00:05Z",
    )
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="approved",
        decided_by="reviewer",
        decided_at="2026-05-06T00:00:02Z",
        decision_reason="manual approve",
    )
    conn.commit()
    conn.close()

    result = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload={"fetched_at": "2026-05-06T00:00:20Z", "data": []},
        order_books={},
        now="2026-05-06T00:00:20Z",
    )

    conn = sqlite3.connect(db_path)
    proposal = list_trade_proposals(conn, deployment_id="dep-1")[0]
    audit = conn.execute("SELECT action, result, reason FROM algo_polymarket_audit_events").fetchone()
    conn.close()

    assert result["fills"] == 0
    assert proposal["status"] == "expired"
    assert audit == ("proposal_expired", "failed", "proposal_expired")


def test_approved_proposal_failed_risk_check_does_not_fill(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.execute("CREATE TABLE algo_strategies (id TEXT PRIMARY KEY, bot_config TEXT)")
    conn.execute(
        "INSERT INTO algo_strategies (id, bot_config) VALUES (?, ?)",
        ("strat-1", '{"approval_mode":"manual_approval","max_order_usdc":1}'),
    )
    signal = SignalDecision(asset_id="asset-1", action="buy", entry_price=0.40, reason="risk check")
    proposal_id = record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-1",
        condition_id="cond-1",
        signal=signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:02:00Z",
    )
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="approved",
        decided_by="reviewer",
        decided_at="2026-05-06T00:00:02Z",
        decision_reason="manual approve",
    )
    conn.commit()
    conn.close()

    result = run_polymarket_cycle(
        db_path=str(db_path),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload={"fetched_at": "2026-05-06T00:00:20Z", "data": []},
        order_books={
            "asset-1": {
                "source_api": "fixture",
                "fetched_at": "2026-05-06T00:00:20Z",
                "data": {
                    "asset_id": "asset-1",
                    "bids": [{"price": "0.39", "size": "100"}],
                    "asks": [{"price": "0.40", "size": "100"}],
                },
            }
        },
        now="2026-05-06T00:00:20Z",
    )

    conn = sqlite3.connect(db_path)
    proposal = list_trade_proposals(conn, deployment_id="dep-1")[0]
    trade_count = conn.execute("SELECT COUNT(*) FROM algo_polymarket_paper_trades").fetchone()[0]
    audit = conn.execute("SELECT action, result, reason FROM algo_polymarket_audit_events").fetchone()
    conn.close()

    assert result["fills"] == 0
    assert proposal["status"] == "failed"
    assert trade_count == 0
    assert audit == ("error", "failed", "max_order_usdc")
