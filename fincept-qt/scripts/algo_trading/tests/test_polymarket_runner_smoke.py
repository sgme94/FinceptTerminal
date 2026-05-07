import json
import sqlite3
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import backtest_engine
from polymarket_runner import run_polymarket_cycle
from polymarket_sources import load_fixture
from polymarket_store import ensure_polymarket_schema
from backtest_engine import cmd_list_strategies, cmd_run_backtest, cmd_save_strategy
from algo_live_runner import load_strategy, open_db_connection
from algo_manager import cmd_list_deployments


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


def seed_deployment(db):
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_deployments (
            id TEXT PRIMARY KEY,
            strategy_id TEXT,
            symbol TEXT,
            mode TEXT,
            status TEXT,
            timeframe TEXT,
            quantity REAL,
            error_message TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_metrics (
            deployment_id TEXT PRIMARY KEY,
            total_pnl REAL,
            unrealized_pnl REAL,
            total_trades INTEGER,
            win_rate REAL,
            max_drawdown REAL,
            current_position_qty REAL,
            current_position_side TEXT,
            current_position_entry REAL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO algo_deployments
            (id, strategy_id, symbol, mode, status, timeframe, quantity, error_message, created_at, updated_at)
        VALUES ('dep-1', 'strat-1', 'polymarket:auto', 'paper', 'running', 'live', 10, '', ?, ?)
        """,
        ("2026-04-30T00:00:00Z", "2026-04-30T00:00:00Z"),
    )
    conn.commit()
    conn.close()


def save_strategy(db, bot_config=None):
    payload = {
        "id": "strat-1",
        "name": "Polymarket paper bot",
        "market_type": "polymarket",
        "market_id": "",
        "symbol": "",
        "timeframe": "live",
        "entry_conditions": [],
        "exit_conditions": [],
        "bot_config": bot_config or {},
    }
    out = StringIO()
    with redirect_stdout(out):
        cmd_save_strategy(payload, str(db))
    return json.loads(out.getvalue())


def list_strategies(db):
    out = StringIO()
    with redirect_stdout(out):
        cmd_list_strategies(str(db))
    return json.loads(out.getvalue())["strategies"]


def list_deployments(db):
    out = StringIO()
    with redirect_stdout(out):
        cmd_list_deployments(str(db))
    return json.loads(out.getvalue())["deployments"]


def test_strategy_save_and_list_preserves_bot_config(tmp_path):
    db = tmp_path / "fincept.db"

    result = save_strategy(db, bot_config={"max_candidates": 3, "min_edge": 0.02})
    strategies = list_strategies(db)

    assert result["success"] is True
    assert strategies[0]["market_type"] == "polymarket"
    assert strategies[0]["bot_config"]["max_candidates"] == 3
    assert strategies[0]["bot_config"]["min_edge"] == 0.02


def test_saved_polymarket_strategy_uses_token_id_for_backtest(tmp_path, monkeypatch):
    db = tmp_path / "fincept.db"
    token_id = "yes-token-1"
    captured = {}

    candles = pd.DataFrame(
        {
            "open": [0.51] * 65,
            "high": [0.53] * 65,
            "low": [0.50] * 65,
            "close": [0.52] * 65,
            "volume": [1000] * 65,
        },
        index=pd.date_range("2026-01-01", periods=65, freq="D"),
    )

    def fake_fetch(symbol, period, interval, **kwargs):
        captured.update(symbol=symbol, period=period, interval=interval, kwargs=kwargs)
        return candles, None

    monkeypatch.setattr(backtest_engine, "fetch_historical_data", fake_fetch)
    out = StringIO()
    with redirect_stdout(out):
        cmd_save_strategy(
            {
                "id": "strat-token",
                "name": "Polymarket token backtest",
                "market_type": "polymarket",
                "token_id": token_id,
                "timeframe": "1d",
                "entry_conditions": [],
                "exit_conditions": [],
            },
            str(db),
        )
    assert json.loads(out.getvalue())["success"] is True

    out = StringIO()
    with redirect_stdout(out):
        cmd_run_backtest(
            {
                "strategy_id": "strat-token",
                "start_date": "2026-01-01",
                "end_date": "2026-03-15",
                "initial_capital": 1000,
            },
            str(db),
        )
    result = json.loads(out.getvalue())

    assert result["success"] is True
    assert result["market_type"] == "polymarket"
    assert result["symbol"] == token_id
    assert captured["symbol"] == token_id
    assert captured["kwargs"]["provider"] == "polymarket"


def test_backtest_respects_explicit_empty_conditions_for_saved_strategy(tmp_path, monkeypatch):
    db = tmp_path / "fincept.db"
    captured = {}
    old_entry = [{"indicator": "CLOSE", "params": {}, "field": "value", "operator": ">", "value": 999}]
    old_exit = [{"indicator": "CLOSE", "params": {}, "field": "value", "operator": "<", "value": 1}]
    candles = pd.DataFrame(
        {
            "open": [10.0] * 65,
            "high": [11.0] * 65,
            "low": [9.0] * 65,
            "close": [10.0] * 65,
            "volume": [1000] * 65,
        }
    )

    monkeypatch.setattr(backtest_engine, "fetch_historical_data", lambda *args, **kwargs: (candles, None))

    def fake_run_backtest(**kwargs):
        captured.update(kwargs)
        return {
            "trades": [],
            "equity_curve": [],
            "metrics": {
                "total_return": 0,
                "total_return_pct": 0,
                "sharpe": 0,
                "max_drawdown": 0,
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
            },
        }

    monkeypatch.setattr(backtest_engine, "run_backtest", fake_run_backtest)

    out = StringIO()
    with redirect_stdout(out):
        cmd_save_strategy(
            {
                "id": "strat-clear",
                "name": "Clear conditions",
                "market_type": "equity",
                "symbol": "TEST",
                "timeframe": "1d",
                "entry_conditions": old_entry,
                "exit_conditions": old_exit,
            },
            str(db),
        )
    assert json.loads(out.getvalue())["success"] is True

    out = StringIO()
    with redirect_stdout(out):
        cmd_run_backtest(
            {
                "strategy_id": "strat-clear",
                "entry_conditions": [],
                "exit_conditions": [],
                "start_date": "2026-01-01",
                "end_date": "2026-03-15",
                "initial_capital": 1000,
            },
            str(db),
        )

    assert json.loads(out.getvalue())["success"] is True
    assert captured["entry_conditions"] == []
    assert captured["exit_conditions"] == []


def test_monthly_timeframe_uses_monthly_sharpe_annualization():
    close_prices = [100 + (i % 5) * 2 + i * 0.4 for i in range(75)]
    candles = pd.DataFrame(
        {
            "open": close_prices,
            "high": [price + 1 for price in close_prices],
            "low": [price - 1 for price in close_prices],
            "close": close_prices,
            "volume": [1000] * len(close_prices),
        }
    )
    entry_condition = [{"indicator": "CLOSE", "params": {}, "field": "value", "operator": ">", "value": 0}]

    legacy_monthly = backtest_engine.run_backtest(
        candles,
        entry_conditions=entry_condition,
        exit_conditions=[],
        initial_capital=1000,
        timeframe="1M",
    )
    new_monthly = backtest_engine.run_backtest(
        candles,
        entry_conditions=entry_condition,
        exit_conditions=[],
        initial_capital=1000,
        timeframe="1mth",
    )

    assert new_monthly["metrics"]["total_trades"] == 1
    assert new_monthly["metrics"]["sharpe"] == legacy_monthly["metrics"]["sharpe"]


def test_live_runner_load_strategy_returns_polymarket_config(tmp_path):
    db = tmp_path / "fincept.db"
    save_strategy(db, bot_config={"max_candidates": 3})
    conn = open_db_connection(str(db))

    strategy = load_strategy(conn, "strat-1")
    conn.close()

    assert strategy["market_type"] == "polymarket"
    assert strategy["bot_config"]["max_candidates"] == 3


def test_algo_manager_lists_polymarket_summary(tmp_path):
    db = tmp_path / "fincept.db"
    save_strategy(db, bot_config={"approval_mode": "auto_paper", "max_candidates": 2, "min_edge": 0.01})
    seed_deployment(db)
    run_polymarket_cycle(
        db_path=str(db),
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_payload=gamma_fixture(),
        order_books={"yes-token-1": book_fixture()},
        now="2026-04-30T00:00:00Z",
    )

    deployment = list_deployments(db)[0]

    assert deployment["poly_candidate_count"] >= 1
    assert deployment["poly_signal_count"] >= 1
    assert deployment["poly_position_count"] >= 1
    assert deployment["poly_latest_signal"] == "buy"
    assert deployment["poly_bot_state"] == "scanning"


def test_runner_one_cycle_writes_signal_and_paper_fill(tmp_path):
    db = tmp_path / "fincept.db"
    seed_strategy(db, market_type="polymarket", bot_config={"approval_mode": "auto_paper", "max_candidates": 2, "min_edge": 0.01})

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


def test_runner_smoke_command_uses_fixtures_without_network(tmp_path):
    db = tmp_path / "fincept.db"
    script = SCRIPT_DIR / "polymarket_runner.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "smoke",
            "--fixture-dir",
            str(FIXTURE_DIR),
            "--db",
            str(db),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["success"] is True
    assert payload["scanned"] == 1
    assert payload["signals"] == 1
    assert count_rows(db, "algo_polymarket_paper_trades") == 1
