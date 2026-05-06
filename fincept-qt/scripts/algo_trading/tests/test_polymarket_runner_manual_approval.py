import sqlite3
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_runner import run_polymarket_cycle
from polymarket_store import ensure_polymarket_schema, list_trade_proposals


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
