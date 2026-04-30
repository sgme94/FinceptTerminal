import json
import sqlite3
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_runner import run_polymarket_cycle
from polymarket_sources import load_fixture
from polymarket_store import ensure_polymarket_schema


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def gamma_fixture():
    return load_fixture(FIXTURE_DIR / "polymarket_gamma_markets.json")


def book_fixture():
    return load_fixture(FIXTURE_DIR / "polymarket_clob_book_yes.json")


def stale_book_fixture():
    return load_fixture(FIXTURE_DIR / "polymarket_clob_book_stale.json")


def seed_strategy(db, market_type="polymarket", bot_config=None):
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_strategies (
            id TEXT PRIMARY KEY,
            market_type TEXT DEFAULT 'equity',
            bot_config TEXT DEFAULT '{}'
        )
        """
    )
    conn.execute(
        "INSERT INTO algo_strategies (id, market_type, bot_config) VALUES (?, ?, ?)",
        ("strat-1", market_type, json.dumps(bot_config or {})),
    )
    conn.commit()
    conn.close()


def seed_position(db, deployment_id, asset_id, size, avg_price):
    conn = sqlite3.connect(db)
    ensure_polymarket_schema(conn)
    conn.execute(
        """
        INSERT INTO algo_polymarket_paper_positions
            (deployment_id, asset_id, size, avg_price, realized_pnl, updated_at)
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (deployment_id, asset_id, size, avg_price, "2026-04-30T00:00:00Z"),
    )
    conn.commit()
    conn.close()


def count_rows(db, table):
    conn = sqlite3.connect(db)
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return count


def latest_skip_reason(db):
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT reason FROM algo_polymarket_skips ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else None


def latest_trade_side(db):
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT side FROM algo_polymarket_paper_trades ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else None


def test_runner_one_cycle_writes_signal_and_paper_fill(tmp_path):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"max_candidates": 2, "min_edge": 0.01})

    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture(),
        order_books={"yes-token-1": book_fixture()},
        now="2026-04-30T00:00:00Z",
    )

    assert result["success"] is True
    assert count_rows(db, "algo_polymarket_signals") >= 1
    assert count_rows(db, "algo_polymarket_paper_trades") >= 1


def test_runner_skips_stale_orderbook(tmp_path):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"freshness_ttl_sec": 30, "max_candidates": 1})

    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture(),
        order_books={"yes-token-1": stale_book_fixture()},
        now="2026-04-30T00:10:00Z",
    )

    assert result["fills"] == 0
    assert latest_skip_reason(db) == "stale_orderbook"


def test_runner_exits_existing_position_on_edge_reversal(tmp_path):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"min_edge": 0.04})
    seed_position(db, deployment_id="dep-1", asset_id="yes-token-1", size=10, avg_price=0.60)

    result = run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture(),
        order_books={"yes-token-1": book_fixture()},
        edge_overrides={"yes-token-1": {"action": "exit", "reason": "edge_reversal"}},
        now="2026-04-30T00:00:00Z",
    )

    assert result["exits"] == 1
    assert latest_trade_side(db) == "SELL"
