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
    record_config_version,
    record_document,
    record_event,
    record_event_market_link,
    record_market_snapshot,
    record_opportunity,
    record_research_run,
    record_shadow_signal,
    record_source_set,
    record_strategy_version,
    record_validation_result,
)
from polymarket_store import ensure_polymarket_schema, record_audit_event

POLY_NOW = "2026-05-07T00:00:00Z"

POLY_ALPHA_LIST_ROUTES = [
    "/api/poly-alpha/config-versions",
    "/api/poly-alpha/source-sets",
    "/api/poly-alpha/strategy-versions",
    "/api/poly-alpha/documents",
    "/api/poly-alpha/events",
    "/api/poly-alpha/links",
    "/api/poly-alpha/research-runs",
    "/api/poly-alpha/findings",
    "/api/poly-alpha/scan-runs",
    "/api/poly-alpha/scan-results",
    "/api/poly-alpha/opportunities",
    "/api/poly-alpha/evidence-packs",
    "/api/poly-alpha/exploration-decisions",
    "/api/poly-alpha/market-snapshots",
    "/api/poly-alpha/shadow-signals",
    "/api/poly-alpha/validations",
    "/api/poly-alpha/promotions",
]


def seed_poly_alpha_versions(conn):
    record_config_version(
        conn,
        config_version_id="cfg-v1",
        name="phase-1",
        validation_freshness_window_sec=300,
        min_exploration_samples=10,
        min_promotion_samples=30,
        min_promotion_history_days=90,
        max_drawdown_threshold=-0.2,
        min_hit_rate=0.52,
        min_payoff_ratio=1.1,
        min_capacity_multiple=2.0,
        promotion_defaults={},
        created_at=POLY_NOW,
    )
    record_source_set(
        conn,
        source_set_version="sources-v1",
        name="phase-1-sources",
        enabled_sources=["official_rss"],
        trust_policy={"official": "required"},
        created_at=POLY_NOW,
    )
    record_strategy_version(
        conn,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        strategy_name="probability-lag",
        version="1",
        config_version_id="cfg-v1",
        prompt_version="prompt-v1",
        source_set_version="sources-v1",
        description="phase 1",
        created_at=POLY_NOW,
    )


def poly_alpha_document(document_id="doc-1", market_id="market-1"):
    return {
        "document_id": document_id,
        "source_type": "rss",
        "source_name": "Official feed",
        "url": "https://example.invalid/feed",
        "api_endpoint": "",
        "market_id": "",
        "venue": "polymarket",
        "venue_market_id": market_id,
        "venue_contract_id": f"contract-{market_id}",
        "outcome_id": "yes",
        "asset_symbol": "BTC",
        "topic": "crypto",
        "published_at": "2026-05-07T11:30:00Z",
        "fetched_at": "2026-05-07T11:45:00Z",
        "observed_at": "2026-05-07T11:46:00Z",
        "payload_hash": f"hash-{document_id}",
        "title": f"Document {document_id}",
        "normalized_text": "normalized evidence",
        "raw_payload": {"id": document_id},
        "trust_level": "official",
    }


def poly_alpha_snapshot(snapshot_id="snap-1", market_id="market-1", observed_at="2026-05-07T11:59:30Z"):
    return {
        "snapshot_id": snapshot_id,
        "venue": "polymarket",
        "venue_market_id": market_id,
        "venue_contract_id": f"contract-{market_id}",
        "outcome_id": "yes",
        "adapter_metadata": {"asset_id": "asset-1"},
        "source_api": "public_market_data",
        "observed_at": observed_at,
        "fetched_at": "2026-05-07T11:59:35Z",
        "payload_hash": f"hash-{snapshot_id}",
        "best_bid": 0.41,
        "best_ask": 0.43,
        "spread": 0.02,
        "top_bid_depth": 250.0,
        "top_ask_depth": 220.0,
        "mid_price": 0.42,
        "last_trade_price": 0.421,
        "liquidity": 1200.0,
        "volume": 5000.0,
        "raw_payload": {"id": snapshot_id},
        "title": f"Market {market_id}",
        "alpha_family": "cross_market_probability",
        "market_probability": 0.42,
        "estimated_probability": 0.57,
        "confidence": 0.72,
    }


def record_poly_alpha_document(conn, document_id="doc-1", market_id="market-1", write_audit=False):
    return record_document(conn, created_at=POLY_NOW, write_audit=write_audit, **poly_alpha_document(document_id, market_id))


def record_poly_alpha_snapshot(conn, snapshot_id="snap-1", market_id="market-1", observed_at="2026-05-07T11:59:30Z"):
    snapshot = {
        key: value
        for key, value in poly_alpha_snapshot(snapshot_id, market_id, observed_at).items()
        if key
        in {
            "snapshot_id",
            "venue",
            "venue_market_id",
            "venue_contract_id",
            "outcome_id",
            "adapter_metadata",
            "source_api",
            "observed_at",
            "fetched_at",
            "payload_hash",
            "best_bid",
            "best_ask",
            "spread",
            "top_bid_depth",
            "top_ask_depth",
            "mid_price",
            "last_trade_price",
            "liquidity",
            "volume",
            "raw_payload",
        }
    }
    return record_market_snapshot(conn, created_at=POLY_NOW, **snapshot)


def seed_poly_alpha_opportunity(conn, suffix="control", market_id="market-1", status="watch"):
    return record_opportunity(
        conn,
        opportunity_id=f"opp-{suffix}",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        title=f"Opportunity {suffix}",
        alpha_family="cross_market_probability",
        status=status,
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.57,
        edge=0.15,
        confidence=0.72,
        created_at=POLY_NOW,
        updated_at=POLY_NOW,
    )


def seed_poly_alpha_evidence(conn, suffix="control", market_id="market-1"):
    opportunity_id = seed_poly_alpha_opportunity(conn, suffix=suffix, market_id=market_id)
    document_id = record_poly_alpha_document(conn, document_id=f"doc-{suffix}", market_id=market_id)
    snapshot_id = record_poly_alpha_snapshot(conn, snapshot_id=f"snap-{suffix}", market_id=market_id)
    event_id = record_event(
        conn,
        event_id=f"event-{suffix}",
        event_type="crypto_price",
        title="BTC breaks level",
        summary="BTC moved quickly",
        primary_assets=["BTC"],
        event_time="2026-05-07T11:40:00Z",
        status="open",
        created_at=POLY_NOW,
        updated_at=POLY_NOW,
    )
    record_event_market_link(
        conn,
        event_id=event_id,
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        adapter_metadata={},
        outcome="yes",
        link_reason="same underlying event",
        link_confidence=0.82,
        created_at=POLY_NOW,
    )
    return opportunity_id, document_id, snapshot_id, event_id


def seed_poly_alpha_shadow(conn, suffix="control", with_validation=False):
    opportunity_id = seed_poly_alpha_opportunity(conn, suffix=suffix, market_id=f"market-{suffix}", status="watch")
    run_id = record_research_run(
        conn,
        run_id=f"run-{suffix}",
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="",
        strategy_version_id="strat-v1",
        event_id="",
        venue="polymarket",
        venue_market_id=f"market-{suffix}",
        requested_by="user",
        started_at=POLY_NOW,
        completed_at=POLY_NOW,
        status="completed",
        model_config={},
        created_at=POLY_NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        shadow_signal_id=f"shadow-{suffix}",
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id=f"market-{suffix}",
        venue_contract_id=f"contract-market-{suffix}",
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
    if with_validation:
        record_validation_result(
            conn,
            opportunity_id=opportunity_id,
            shadow_signal_id=shadow_signal_id,
            strategy_version_id="strat-v1",
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
            created_at=POLY_NOW,
        )
    return opportunity_id, shadow_signal_id


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


@pytest.mark.parametrize("route", POLY_ALPHA_LIST_ROUTES)
def test_poly_alpha_list_routes_return_items_and_ensure_schema(tmp_path, route):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    response = client.get(route)

    assert response.status_code == 200
    assert response.json() == {"items": []}

    conn = sqlite3.connect(db_path)
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'poly_alpha_config_versions'"
    ).fetchone()
    conn.close()
    assert table_exists is not None


def test_poly_alpha_list_route_ignores_resource_query_parameter(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_poly_alpha_schema(conn)
    seed_poly_alpha_versions(conn)
    conn.execute(
        """
        INSERT INTO poly_alpha_audit_events
            (audit_id, action, entity_type, entity_id, actor_type, before_json,
             after_json, result, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "audit-resource-query",
            "research_started",
            "research_run",
            "run-resource-query",
            "system",
            "{}",
            "{}",
            "success",
            POLY_NOW,
        ),
    )
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)), raise_server_exceptions=False)

    audit_override = client.get("/api/poly-alpha/config-versions?resource=audit")
    unknown_override = client.get("/api/poly-alpha/config-versions?resource=unknown")

    assert audit_override.status_code == 200
    assert unknown_override.status_code == 200
    assert audit_override.json()["items"][0]["config_version_id"] == "cfg-v1"
    assert unknown_override.json()["items"][0]["config_version_id"] == "cfg-v1"
    assert "action" not in audit_override.json()["items"][0]


def test_poly_alpha_manual_research_route_records_run_and_audit(tmp_path):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    response = client.post(
        "/api/poly-alpha/research-runs/manual",
        json={
            "opportunity_id": "opp-manual",
            "evidence_pack_id": "pack-manual",
            "strategy_version_id": "strat-v1",
            "event_id": "event-manual",
            "venue": "polymarket",
            "venue_market_id": "market-manual",
            "requested_by": "analyst",
            "config": {"model": "paper-research"},
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["action"] == "research_started"
    assert body["ids"]["run_id"]

    runs = client.get("/api/poly-alpha/research-runs").json()["items"]
    audit = client.get("/api/poly-alpha/audit").json()["items"]
    assert runs[0]["run_id"] == body["ids"]["run_id"]
    assert runs[0]["trigger_type"] == "manual_task"
    assert runs[0]["status"] == "running"
    assert [event["action"] for event in audit] == ["research_started"]


def test_poly_alpha_control_routes_run_paper_only_workflow(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_polymarket_schema(conn)
    ensure_poly_alpha_schema(conn)
    seed_poly_alpha_versions(conn)
    evidence_opportunity_id, document_id, snapshot_id, event_id = seed_poly_alpha_evidence(conn, suffix="evidence")
    _, validation_shadow_id = seed_poly_alpha_shadow(conn, suffix="validation")
    record_poly_alpha_snapshot(
        conn,
        snapshot_id="snap-validation-entry",
        market_id="market-validation",
        observed_at="2026-05-06T23:59:00Z",
    )
    _, promotion_shadow_id = seed_poly_alpha_shadow(conn, suffix="promotion", with_validation=True)
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))

    scan_response = client.post(
        "/api/poly-alpha/scan-runs/deterministic",
        json={
            "strategy_version_id": "strat-v1",
            "config": {"min_edge": 0.01},
            "source_documents": [poly_alpha_document("doc-scan", "market-scan")],
            "market_snapshots": [poly_alpha_snapshot("snap-scan", "market-scan")],
        },
    )
    evidence_response = client.post(
        "/api/poly-alpha/evidence-packs/build",
        json={
            "opportunity_id": evidence_opportunity_id,
            "document_ids": [document_id],
            "snapshot_ids": [snapshot_id],
            "event_ids": [event_id],
        },
    )
    exploration_response = client.post(
        "/api/poly-alpha/exploration-decisions/decide",
        json={
            "opportunity_id": evidence_opportunity_id,
            "evidence_pack_id": evidence_response.json()["ids"]["evidence_pack_id"],
            "config": {"historical_sample_count": 10, "exploration_snapshot_freshness_sec": 604800},
        },
    )
    validation_response = client.post(
        "/api/poly-alpha/validations/run",
        json={
            "shadow_signal_id": validation_shadow_id,
            "config": {"validation_freshness_window_sec": 300},
        },
    )
    promotion_response = client.post(
        "/api/poly-alpha/promotions/evaluate",
        json={"shadow_signal_id": promotion_shadow_id, "config": passing_promotion_config()},
    )
    proposal_response = client.post(
        "/api/poly-alpha/paper-proposals/create",
        json={
            "promotion_id": promotion_response.json()["ids"]["promotion_id"],
            "deployment_id": "dep-1",
        },
    )

    assert scan_response.status_code == 202
    assert evidence_response.status_code == 202
    assert exploration_response.status_code == 202
    assert validation_response.status_code == 202
    assert promotion_response.status_code == 202
    assert proposal_response.status_code == 202
    assert scan_response.json()["ids"]["scan_run_id"]
    assert evidence_response.json()["ids"]["evidence_pack_id"]
    assert exploration_response.json()["ids"]["exploration_id"]
    assert validation_response.json()["ids"]["validation_ids"]
    assert promotion_response.json()["ids"]["promotion_id"]
    assert proposal_response.json()["ids"]["proposal_id"]

    assert client.get("/api/poly-alpha/scan-runs").json()["items"][0]["status"] == "completed"
    assert client.get("/api/poly-alpha/evidence-packs").json()["items"][0]["opportunity_id"] == evidence_opportunity_id
    assert client.get("/api/poly-alpha/exploration-decisions").json()["items"][0]["decision"] == "pass"
    assert client.get("/api/poly-alpha/validations").json()["items"]
    assert client.get("/api/poly-alpha/promotions").json()["items"][0]["decision"] == "promote"
    proposal = client.get("/api/proposals?deployment_id=dep-1").json()["proposals"][0]
    assert proposal["proposal_id"] == proposal_response.json()["ids"]["proposal_id"]
    assert proposal["features"]["paper_only"] is True


def test_poly_alpha_control_routes_reject_live_order_fields(tmp_path):
    db_path = tmp_path / "bot.db"
    client = TestClient(create_app(db_path=str(db_path)))

    unknown_live_field = client.post(
        "/api/poly-alpha/research-runs/manual",
        json={
            "opportunity_id": "opp-manual",
            "evidence_pack_id": "pack-manual",
            "strategy_version_id": "strat-v1",
            "live_order": {"side": "buy"},
        },
    )
    nested_live_field = client.post(
        "/api/poly-alpha/scan-runs/deterministic",
        json={
            "strategy_version_id": "strat-v1",
            "config": {"nested": {"private_key": "not-accepted"}},
            "source_documents": [],
            "market_snapshots": [],
        },
    )
    nested_clob_value = client.post(
        "/api/poly-alpha/research-runs/manual",
        json={
            "opportunity_id": "opp-manual",
            "evidence_pack_id": "pack-manual",
            "strategy_version_id": "strat-v1",
            "config": {"routing": {"source": "clob"}},
        },
    )
    clob_order_shape = client.post(
        "/api/poly-alpha/promotions/evaluate",
        json={
            "shadow_signal_id": "shadow-unsafe",
            "config": {
                "order": {
                    "tokenId": "123",
                    "makerAmount": "100",
                    "takerAmount": "42",
                    "side": "BUY",
                    "signature": "0xsig",
                }
            },
        },
    )
    nested_order_fields_in_list = client.post(
        "/api/poly-alpha/scan-runs/deterministic",
        json={
            "strategy_version_id": "strat-v1",
            "config": {},
            "source_documents": [],
            "market_snapshots": [{"venue": "polymarket", "makerAmount": "100", "signature": "0xsig"}],
        },
    )

    assert unknown_live_field.status_code == 422
    assert nested_live_field.status_code == 422
    assert nested_clob_value.status_code == 422
    assert clob_order_shape.status_code == 422
    assert nested_order_fields_in_list.status_code == 422


def test_poly_alpha_audit_route_returns_unified_audit_actions(tmp_path):
    db_path = tmp_path / "bot.db"
    conn = sqlite3.connect(db_path)
    ensure_poly_alpha_schema(conn)
    actions = [
        "document_ingested",
        "evidence_pack_created",
        "research_started",
        "research_completed",
        "validation_completed",
        "promotion_approved",
        "promotion_rejected",
        "promotion_watch",
        "paper_fill_skipped",
    ]
    for index, action in enumerate(actions):
        conn.execute(
            """
            INSERT INTO poly_alpha_audit_events
                (audit_id, action, entity_type, entity_id, actor_type, before_json,
                 after_json, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit-{index}",
                action,
                "poly_alpha",
                f"entity-{index}",
                "system",
                "{}",
                "{}",
                "success",
                f"2026-05-07T00:00:{index:02d}Z",
            ),
        )
    conn.commit()
    conn.close()

    client = TestClient(create_app(db_path=str(db_path)))
    response = client.get("/api/poly-alpha/audit")

    assert response.status_code == 200
    assert [event["action"] for event in response.json()["items"]] == actions


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
