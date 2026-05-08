import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
ALGO_ROOT = SCRIPT_ROOT / "algo_trading"
for path in (SCRIPT_ROOT, ALGO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from polymarket_web_api.app import create_app
from polymarket_web_api.repository import InvalidProposalStateError, PolymarketRepository
from poly_alpha_promotion import create_paper_proposal_from_promotion, evaluate_promotion
from poly_alpha_store import (
    ensure_poly_alpha_schema,
    list_opportunities,
    list_poly_alpha_audit_events,
    record_opportunity,
    record_research_run,
    record_shadow_signal,
    record_validation_result,
)
from polymarket_store import ensure_polymarket_schema, record_audit_event

POLY_NOW = "2026-05-07T00:00:00Z"


def insert_proposal(
    conn,
    proposal_id="proposal-1",
    deployment_id="dep-1",
    status="proposed",
    expires_at="2099-05-07T00:00:00Z",
):
    conn.execute(
        """
        INSERT INTO algo_polymarket_trade_proposals
            (proposal_id, deployment_id, strategy_id, market_id, condition_id, asset_id,
             side, price, estimated_probability, edge, confidence, reason, features_json,
             size, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal_id,
            deployment_id,
            "strat-1",
            "market-1",
            "condition-1",
            "asset-1",
            "buy",
            0.42,
            0.55,
            0.13,
            0.8,
            "edge detected",
            "{}",
            10.0,
            status,
            "2026-05-06T00:00:00Z",
            expires_at,
        ),
    )


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


def seed_poly_alpha_proposal(conn, proposal_suffix: str) -> str:
    ensure_poly_alpha_schema(conn)
    opportunity_id = record_opportunity(
        conn,
        opportunity_id=f"opp-{proposal_suffix}",
        strategy_version_id="strat-1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="condition-1",
        outcome_id="yes",
        title="Promotion candidate",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        created_at=POLY_NOW,
        updated_at=POLY_NOW,
    )
    run_id = record_research_run(
        conn,
        run_id=f"run-{proposal_suffix}",
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-1",
        event_id="event-1",
        venue="polymarket",
        venue_market_id="market-1",
        requested_by="user",
        started_at=POLY_NOW,
        status="running",
        model_config={},
        created_at=POLY_NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        shadow_signal_id=f"shadow-{proposal_suffix}",
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="condition-1",
        outcome_id="yes",
        adapter_metadata={"asset_id": "asset-1"},
        side="buy",
        observed_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        status="shadow",
        created_at=POLY_NOW,
        expires_at="2099-05-07T00:00:00Z",
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
        edge_decay=None,
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
        created_at=POLY_NOW,
    )
    promotion_id = evaluate_promotion(conn, shadow_signal_id, passing_promotion_config(), POLY_NOW)
    return create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", POLY_NOW)


def insert_trade(conn, deployment_id="dep-1"):
    conn.execute(
        """
        INSERT INTO algo_polymarket_paper_trades
            (deployment_id, asset_id, side, size, price, realized_pnl, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            "asset-1",
            "BUY",
            10.0,
            0.42,
            0.0,
            "manual approval fill",
            "2026-05-06T00:01:00Z",
        ),
    )


def insert_position(conn, deployment_id="dep-1"):
    conn.execute(
        """
        INSERT INTO algo_polymarket_paper_positions
            (deployment_id, asset_id, size, avg_price, realized_pnl, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            "asset-1",
            10.0,
            0.42,
            0.0,
            "2026-05-06T00:01:00Z",
        ),
    )


def insert_candidate(conn, deployment_id="dep-1"):
    conn.execute(
        """
        INSERT INTO algo_polymarket_candidates
            (deployment_id, strategy_id, market_id, condition_id, asset_id, outcome,
             price, volume, liquidity, fetched_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            "strat-1",
            "market-1",
            "condition-1",
            "asset-1",
            "yes",
            0.57,
            1000.0,
            250.0,
            "2026-05-06T00:00:00Z",
            "2026-05-06T00:00:01Z",
        ),
    )


def insert_signal(conn, deployment_id="dep-1", features_json='{"macro repricing": 0.42}'):
    conn.execute(
        """
        INSERT INTO algo_polymarket_signals
            (deployment_id, asset_id, action, entry_price, estimated_probability,
             edge, confidence, reason, features_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            "asset-1",
            "buy",
            0.42,
            0.55,
            0.13,
            0.8,
            "edge detected",
            features_json,
            "2026-05-06T00:00:00Z",
        ),
    )


def insert_skip(conn, deployment_id="dep-1"):
    conn.execute(
        """
        INSERT INTO algo_polymarket_skips
            (deployment_id, market_id, asset_id, reason, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            deployment_id,
            "market-thin",
            "asset-thin",
            "liquidity_below_threshold",
            "liquidity 8 < 100",
            "2026-05-06T00:00:00Z",
        ),
    )


def test_status_route_returns_terminal_status(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/bot/status")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "paper"
    assert body["live_enabled"] is False


def test_api_allows_local_web_terminal_cors(tmp_path):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    response = client.options(
        "/api/proposals",
        headers={
            "Origin": "http://127.0.0.1:4177",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4177"


def test_audit_route_returns_events(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    record_audit_event(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        actor_type="user",
        actor_id="local-user",
        action="start",
        entity_type="deployment",
        entity_id="dep-1",
        before={},
        after={"status": "running"},
        result="success",
        reason="start paper bot",
        request_id="req-1",
        now="2026-05-06T00:00:00Z",
    )
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/audit?deployment_id=dep-1")

    assert response.status_code == 200
    assert response.json()["events"][0]["action"] == "start"


def test_proposals_route_returns_deployment_proposals(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn)
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/proposals?deployment_id=dep-1")

    assert response.status_code == 200
    proposal = response.json()["proposals"][0]
    assert proposal["proposal_id"] == "proposal-1"
    assert proposal["status"] == "proposed"


def test_candidates_signals_and_skips_routes_return_deployment_rows(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_candidate(conn)
    insert_candidate(conn, deployment_id="other-dep")
    insert_signal(conn)
    insert_signal(conn, deployment_id="other-dep")
    insert_skip(conn)
    insert_skip(conn, deployment_id="other-dep")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    candidates = client.get("/api/candidates?deployment_id=dep-1")
    signals = client.get("/api/signals?deployment_id=dep-1")
    skips = client.get("/api/skips?deployment_id=dep-1")

    assert candidates.status_code == 200
    assert signals.status_code == 200
    assert skips.status_code == 200
    assert [row["market_id"] for row in candidates.json()["candidates"]] == ["market-1"]
    assert [row["asset_id"] for row in signals.json()["signals"]] == ["asset-1"]
    assert [row["reason"] for row in skips.json()["skips"]] == ["liquidity_below_threshold"]


def test_trades_and_positions_routes_return_paper_rows(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_trade(conn)
    insert_trade(conn, deployment_id="other-dep")
    insert_position(conn)
    insert_position(conn, deployment_id="other-dep")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    trades = client.get("/api/trades?deployment_id=dep-1")
    positions = client.get("/api/positions?deployment_id=dep-1")

    assert trades.status_code == 200
    assert positions.status_code == 200
    assert [row["asset_id"] for row in trades.json()["trades"]] == ["asset-1"]
    assert [row["asset_id"] for row in positions.json()["positions"]] == ["asset-1"]


def test_signals_route_degrades_malformed_features_to_empty_object(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_signal(conn, features_json="{bad json")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/signals?deployment_id=dep-1")

    assert response.status_code == 200
    assert response.json()["signals"][0]["features"] == {}


def test_kill_switch_records_paper_only_audit_event_and_cancels_open_proposals(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="open-1", status="proposed")
    insert_proposal(conn, proposal_id="open-2", status="approved")
    insert_proposal(conn, proposal_id="closed-1", status="filled")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    response = client.post(
        "/api/control/kill-switch",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "manual",
            "actor_id": "reviewer",
            "reason": "paper kill switch",
            "request_id": "req-kill",
        },
    )

    assert response.status_code == 202
    assert response.json()["action"] == "kill_switch"

    events = client.get("/api/audit?deployment_id=dep-1").json()["events"]
    proposals = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"]
    statuses = {proposal["proposal_id"]: proposal["status"] for proposal in proposals}

    assert statuses == {"open-1": "cancelled", "open-2": "cancelled", "closed-1": "filled"}
    assert [event["action"] for event in events] == ["kill_switch", "proposal_cancelled", "proposal_cancelled"]
    assert events[0]["entity_type"] == "deployment"
    assert events[0]["result"] == "accepted"


def test_control_start_records_audit_event(tmp_path):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    response = client.post(
        "/api/control/start",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "local-user",
            "reason": "start paper bot",
            "request_id": "req-1",
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    audit_response = client.get("/api/audit?deployment_id=dep-1")
    event = audit_response.json()["events"][0]
    assert event["action"] == "start"
    assert event["result"] == "accepted"


def test_approve_and_reject_update_proposal_state_and_audit(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="approve-1")
    insert_proposal(conn, proposal_id="reject-1")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    approve_response = client.post(
        "/api/proposals/approve-1/approve",
        json={"deployment_id": "dep-1", "strategy_id": "strat-1", "actor_id": "reviewer"},
    )
    reject_response = client.post(
        "/api/proposals/reject-1/reject",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "reviewer",
            "reason": "too risky",
        },
    )

    assert approve_response.status_code == 202
    assert reject_response.status_code == 202
    assert approve_response.json()["action"] == "approve"
    assert reject_response.json()["action"] == "reject"

    proposals = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"]
    statuses = {proposal["proposal_id"]: proposal["status"] for proposal in proposals}
    assert statuses == {"approve-1": "approved", "reject-1": "rejected"}

    actions = [event["action"] for event in client.get("/api/audit?deployment_id=dep-1").json()["events"]]
    assert actions == ["approve", "reject"]


@pytest.mark.parametrize(
    ("route_action", "expected_status", "expected_opportunity_status", "expected_audit_action"),
    [
        ("approve", "approved", "approved", "proposal_approved"),
        ("reject", "rejected", "rejected", "proposal_rejected"),
    ],
)
def test_poly_alpha_proposal_decision_route_updates_lineage_and_poly_audit(
    tmp_path,
    route_action,
    expected_status,
    expected_opportunity_status,
    expected_audit_action,
):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    proposal_id = seed_poly_alpha_proposal(conn, proposal_suffix=route_action)
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.post(
        f"/api/proposals/{proposal_id}/{route_action}",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "reviewer",
            "reason": f"manual {route_action}",
            "request_id": f"req-poly-{route_action}",
        },
    )

    assert response.status_code == 202
    assert response.json()["action"] == route_action
    proposal = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"][0]
    assert proposal["status"] == expected_status
    assert proposal["decided_by"] == "reviewer"
    assert proposal["decision_reason"] == f"manual {route_action}"

    conn = sqlite3.connect(db_path)
    opportunity = list_opportunities(conn)[0]
    poly_actions = [row["action"] for row in list_poly_alpha_audit_events(conn)]
    conn.close()
    assert opportunity["status"] == expected_opportunity_status
    assert expected_audit_action in poly_actions

    audit = client.get("/api/audit?deployment_id=dep-1").json()["events"][-1]
    assert audit["action"] == expected_audit_action
    assert audit["request_id"] == f"req-poly-{route_action}"
    assert response.json()["event_id"] == audit["event_id"]


def test_repository_approve_does_not_overwrite_state_changed_after_read(tmp_path, monkeypatch):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="race-approve")
    conn.commit()
    conn.close()

    from polymarket_web_api import repository as repository_module

    original_update = repository_module.update_trade_proposal_status
    raced = {"done": False}

    def racing_update(conn, proposal_id, status, *args, **kwargs):
        if proposal_id == "race-approve" and status == "approved" and not raced["done"]:
            raced["done"] = True
            original_update(
                conn,
                proposal_id,
                "cancelled",
                "kill-switch",
                "2026-05-06T00:00:01Z",
                "paper kill switch",
            )
        return original_update(conn, proposal_id, status, *args, **kwargs)

    monkeypatch.setattr(repository_module, "update_trade_proposal_status", racing_update)
    repo = PolymarketRepository(str(db_path))

    with pytest.raises(InvalidProposalStateError):
        repo.decide_proposal(
            proposal_id="race-approve",
            deployment_id="dep-1",
            strategy_id="strat-1",
            status="approved",
            actor_id="reviewer",
            reason="manual approve",
            request_id="req-race",
            now="2026-05-06T00:00:02Z",
        )

    client = TestClient(create_app(db_path=str(db_path)))
    proposal = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"][0]
    event = client.get("/api/audit?deployment_id=dep-1").json()["events"][0]

    assert proposal["status"] == "cancelled"
    assert event["action"] == "approve"
    assert event["result"] == "failed"
    assert event["reason"] == "proposal_not_proposed"


def test_repository_kill_switch_does_not_cancel_state_changed_after_read(tmp_path, monkeypatch):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="race-kill", status="approved")
    conn.commit()
    conn.close()

    from polymarket_web_api import repository as repository_module

    original_update = repository_module.update_trade_proposal_status
    raced = {"done": False}

    def racing_update(conn, proposal_id, status, *args, **kwargs):
        if proposal_id == "race-kill" and status == "cancelled" and not raced["done"]:
            raced["done"] = True
            original_update(
                conn,
                proposal_id,
                "filled",
                "runner",
                "2026-05-06T00:00:01Z",
                "paper fill",
            )
        return original_update(conn, proposal_id, status, *args, **kwargs)

    monkeypatch.setattr(repository_module, "update_trade_proposal_status", racing_update)
    repo = PolymarketRepository(str(db_path))

    repo.kill_switch(
        deployment_id="dep-1",
        strategy_id="strat-1",
        actor_id="reviewer",
        reason="paper kill switch",
        request_id="req-race-kill",
        now="2026-05-06T00:00:02Z",
    )

    client = TestClient(create_app(db_path=str(db_path)))
    proposal = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"][0]
    events = client.get("/api/audit?deployment_id=dep-1").json()["events"]

    assert proposal["status"] == "filled"
    assert [event["action"] for event in events] == ["kill_switch", "proposal_cancelled"]
    assert events[1]["result"] == "failed"


def test_missing_proposal_approve_returns_404_and_failed_audit(tmp_path):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    response = client.post(
        "/api/proposals/missing-1/approve",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "reviewer",
            "reason": "manual approve",
            "request_id": "req-missing",
        },
    )

    assert response.status_code == 404

    events = client.get("/api/audit?deployment_id=dep-1").json()["events"]
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "approve"
    assert event["entity_type"] == "proposal"
    assert event["entity_id"] == "missing-1"
    assert event["before"] == {}
    assert event["after"] == {}
    assert event["result"] == "failed"
    assert event["reason"] == "manual approve"


def test_approve_expired_proposal_returns_409_failed_audit_and_preserves_status(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="expired-1", status="expired")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.post(
        "/api/proposals/expired-1/approve",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "reviewer",
            "reason": "manual approve",
            "request_id": "req-expired",
        },
    )

    assert response.status_code == 409

    proposals = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"]
    assert proposals[0]["status"] == "expired"

    events = client.get("/api/audit?deployment_id=dep-1").json()["events"]
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "approve"
    assert event["entity_type"] == "proposal"
    assert event["entity_id"] == "expired-1"
    assert event["before"]["status"] == "expired"
    assert event["after"]["status"] == "expired"
    assert event["result"] == "failed"
    assert event["reason"] == "proposal_not_proposed"


def test_approve_past_ttl_proposed_proposal_marks_expired_and_returns_409(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="past-ttl-1", expires_at="2020-01-01T00:00:00Z")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.post(
        "/api/proposals/past-ttl-1/approve",
        json={
            "deployment_id": "dep-1",
            "strategy_id": "strat-1",
            "actor_id": "reviewer",
            "reason": "manual approve",
            "request_id": "req-past-ttl",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "proposal_expired"

    proposal = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"][0]
    assert proposal["status"] == "expired"

    event = client.get("/api/audit?deployment_id=dep-1").json()["events"][0]
    assert event["action"] == "approve"
    assert event["result"] == "failed"
    assert event["reason"] == "proposal_expired"


def test_proposals_route_marks_past_ttl_proposed_proposal_expired(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="read-expired-1", expires_at="2020-01-01T00:00:00Z")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/proposals?deployment_id=dep-1")

    assert response.status_code == 200
    assert response.json()["proposals"][0]["status"] == "expired"

    events = client.get("/api/audit?deployment_id=dep-1").json()["events"]
    assert len(events) == 1
    assert events[0]["action"] == "proposal_expired"
    assert events[0]["entity_id"] == "read-expired-1"
    assert events[0]["before"]["status"] == "proposed"
    assert events[0]["after"]["status"] == "expired"
    assert events[0]["result"] == "failed"
    assert events[0]["reason"] == "proposal_expired"


def test_cross_deployment_approve_and_reject_return_404_without_changing_original(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    insert_proposal(conn, proposal_id="shared-approve", deployment_id="dep-original")
    insert_proposal(conn, proposal_id="shared-reject", deployment_id="dep-original")
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    approve_response = client.post(
        "/api/proposals/shared-approve/approve",
        json={"deployment_id": "dep-requested", "strategy_id": "strat-1", "actor_id": "reviewer"},
    )
    reject_response = client.post(
        "/api/proposals/shared-reject/reject",
        json={"deployment_id": "dep-requested", "strategy_id": "strat-1", "actor_id": "reviewer"},
    )

    assert approve_response.status_code == 404
    assert reject_response.status_code == 404

    original_proposals = client.get("/api/proposals?deployment_id=dep-original").json()["proposals"]
    statuses = {proposal["proposal_id"]: proposal["status"] for proposal in original_proposals}
    assert statuses == {"shared-approve": "proposed", "shared-reject": "proposed"}

    requested_events = client.get("/api/audit?deployment_id=dep-requested").json()["events"]
    assert [event["action"] for event in requested_events] == ["approve", "reject"]
    assert [event["result"] for event in requested_events] == ["failed", "failed"]
