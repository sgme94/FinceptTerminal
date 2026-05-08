import sqlite3
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_runner import run_polymarket_cycle
from polymarket_models import SignalDecision
from poly_alpha_promotion import (
    create_paper_proposal_from_promotion,
    evaluate_promotion,
    record_proposal_decision,
)
from poly_alpha_store import (
    ensure_poly_alpha_schema,
    list_opportunities,
    list_poly_alpha_audit_events,
    record_opportunity,
    record_research_run,
    record_shadow_signal,
    record_validation_result,
)
from polymarket_store import (
    ensure_polymarket_schema,
    list_trade_proposals,
    record_trade_proposal,
    update_trade_proposal_status,
)


NOW = "2026-05-06T00:00:00Z"


def passing_promotion_config():
    return {
        "min_promotion_samples": 30,
        "min_promotion_history_days": 90,
        "sample_count": 30,
        "history_days": 90,
        "cost_adjusted_net_return": 0.08,
        "median_clv_after_costs": 0.03,
        "max_drawdown": -0.12,
        "max_drawdown_threshold": -0.20,
        "hit_rate": 0.56,
        "min_hit_rate": 0.52,
        "payoff_ratio": 1.25,
        "min_payoff_ratio": 1.10,
        "capacity": 50.0,
        "paper_order_size": 25.0,
        "lookahead_check_passed": True,
        "survivorship_check_passed": True,
        "risk_reviewer_approved": True,
        "risk_reviewer": "risk-reviewer",
        "approval_latency_impact": {"median_seconds": 12, "edge_decay": 0.002},
        "unresolved_metrics": {"edge_decay": 0.01},
    }


def seed_poly_alpha_approved_proposal(conn, deployment_id="dep-1"):
    ensure_poly_alpha_schema(conn)
    opportunity_id = record_opportunity(
        conn,
        opportunity_id="opp-runner",
        strategy_version_id="strat-1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="cond-1",
        outcome_id="yes",
        title="Runner fill candidate",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        created_at=NOW,
        updated_at=NOW,
    )
    run_id = record_research_run(
        conn,
        run_id="run-runner",
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-runner",
        strategy_version_id="strat-1",
        event_id="event-runner",
        venue="polymarket",
        venue_market_id="market-1",
        requested_by="user",
        started_at=NOW,
        status="running",
        model_config={},
        created_at=NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        shadow_signal_id="shadow-runner",
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="cond-1",
        outcome_id="yes",
        adapter_metadata={"asset_id": "asset-1"},
        side="buy",
        observed_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        status="shadow",
        created_at=NOW,
        expires_at="2026-05-06T00:02:00Z",
    )
    record_validation_result(
        conn,
        opportunity_id=opportunity_id,
        shadow_signal_id=shadow_signal_id,
        strategy_version_id="strat-1",
        entry_snapshot_id="snap-entry",
        exit_snapshot_id="snap-exit",
        validation_type="fixed_horizon",
        entry_price=0.42,
        exit_price=0.48,
        holding_period="1h",
        gross_return=0.14,
        cost_adjusted_return=0.12,
        closing_line_value=0.05,
        brier_score=0.21,
        calibration_error=0.02,
        edge_decay=0.01,
        information_lag_sec=30,
        fetch_lag_sec=5,
        market_move_before_signal=0.01,
        market_move_after_signal=0.06,
        max_adverse_excursion=-0.02,
        max_favorable_excursion=0.08,
        liquidity_assumption="top_of_book",
        slippage_assumption="one_tick",
        pass_fail="pass",
        failure_reason="",
        created_at=NOW,
    )
    promotion_id = evaluate_promotion(conn, shadow_signal_id, passing_promotion_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, deployment_id, NOW)
    assert record_proposal_decision(
        conn,
        proposal_id,
        "approved",
        "reviewer",
        "2026-05-06T00:00:10Z",
        "manual approve",
    )
    return proposal_id


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


def test_expired_proposed_proposal_does_not_block_new_proposal(tmp_path):
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
    expired_signal = SignalDecision(asset_id="asset-1", action="buy", entry_price=0.40, reason="old")
    record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-old",
        condition_id="cond-old",
        signal=expired_signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:00:05Z",
    )
    conn.commit()
    conn.close()

    market_payload = {
        "fetched_at": "2026-05-06T00:00:20Z",
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
            "fetched_at": "2026-05-06T00:00:20Z",
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
            "reason": "fresh proposal",
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
        now="2026-05-06T00:00:20Z",
    )

    conn = sqlite3.connect(db_path)
    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    statuses = [proposal["status"] for proposal in proposals]
    audit_actions = [
        row[0]
        for row in conn.execute("SELECT action FROM algo_polymarket_audit_events ORDER BY id").fetchall()
    ]
    conn.close()

    assert result["proposals"] == 1
    assert statuses == ["expired", "proposed"]
    assert audit_actions == ["proposal_expired", "proposal_created"]


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


def test_poly_alpha_paper_approved_proposal_records_fill_through_bridge(tmp_path):
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
    seed_poly_alpha_approved_proposal(conn)
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
    opportunity = list_opportunities(conn)[0]
    poly_alpha_actions = [event["action"] for event in list_poly_alpha_audit_events(conn)]
    conn.close()

    assert result["fills"] == 1
    assert proposal["status"] == "filled"
    assert proposal["fill_trade_id"]
    assert opportunity["status"] == "filled"
    assert trade_count == 1
    assert "paper_fill_recorded" in poly_alpha_actions


def test_cancelled_proposal_snapshot_cannot_be_filled(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    signal = SignalDecision(asset_id="asset-1", action="buy", entry_price=0.40, reason="stale snapshot")
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
    stale_snapshot = list_trade_proposals(conn, deployment_id="dep-1")[0]
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="cancelled",
        decided_by="reviewer",
        decided_at="2026-05-06T00:00:03Z",
        decision_reason="kill switch",
    )

    from polymarket_runner import _transition_proposal

    updated = _transition_proposal(
        conn,
        "dep-1",
        stale_snapshot,
        "filled",
        "2026-05-06T00:00:20Z",
        action="fill_simulated",
        result="success",
        reason="stale runner snapshot",
        fill_trade_id="999",
    )
    conn.commit()

    proposal = list_trade_proposals(conn, deployment_id="dep-1")[0]
    audit_count = conn.execute("SELECT COUNT(*) FROM algo_polymarket_audit_events").fetchone()[0]
    conn.close()

    assert updated is False
    assert proposal["status"] == "cancelled"
    assert proposal["fill_trade_id"] == ""
    assert audit_count == 0


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
