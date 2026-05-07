import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_store import (
    audit_action_for_lifecycle_event,
    ensure_poly_alpha_schema,
    list_agent_findings,
    list_documents,
    list_event_market_links,
    list_events,
    list_evidence_packs,
    list_exploration_decisions,
    list_market_snapshots,
    list_opportunities,
    list_poly_alpha_audit_events,
    list_promotion_decisions,
    list_research_runs,
    list_scan_results,
    list_scan_runs,
    list_shadow_signals,
    list_validation_results,
    record_agent_finding,
    record_config_version,
    record_document,
    record_event,
    record_event_market_link,
    record_evidence_pack,
    record_exploration_decision,
    record_market_snapshot,
    record_opportunity,
    record_promotion_decision,
    record_research_run,
    record_scan_result,
    record_scan_run,
    record_shadow_signal,
    record_source_set,
    record_strategy_version,
    record_validation_result,
    update_opportunity_status,
)


NOW = "2026-05-07T00:00:00Z"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ensure_poly_alpha_schema(conn)
    return conn


def test_ensure_poly_alpha_schema_creates_phase_1_tables(tmp_path):
    conn = sqlite3.connect(tmp_path / "poly.db")
    ensure_poly_alpha_schema(conn)

    names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "poly_alpha_config_versions" in names
    assert "poly_alpha_source_sets" in names
    assert "poly_alpha_strategy_versions" in names
    assert "poly_alpha_documents" in names
    assert "poly_alpha_events" in names
    assert "poly_alpha_event_market_links" in names
    assert "poly_alpha_research_runs" in names
    assert "poly_alpha_scan_runs" in names
    assert "poly_alpha_scan_results" in names
    assert "poly_alpha_opportunities" in names
    assert "poly_alpha_evidence_packs" in names
    assert "poly_alpha_exploration_decisions" in names
    assert "poly_alpha_market_snapshots" in names
    assert "poly_alpha_agent_findings" in names
    assert "poly_alpha_shadow_signals" in names
    assert "poly_alpha_validation_results" in names
    assert "poly_alpha_promotion_decisions" in names


def test_scan_runs_persist_no_trade_attribution_and_creation_audit():
    conn = _conn()

    scan_run_id = record_scan_run(
        conn,
        trigger_type="manual_scan",
        strategy_version_id="strat-v1",
        config_version_id="cfg-v1",
        source_set_version="sources-v1",
        status="running",
        started_at=NOW,
        created_at=NOW,
    )
    assert scan_run_id

    ignored_result_id = record_scan_result(
        conn,
        scan_run_id=scan_run_id,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        decision="ignore",
        reason="wide_spread",
        source_snapshot_ids=["snap-1"],
        source_document_ids=["doc-1"],
        observed_at=NOW,
        created_at=NOW,
    )
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-2",
        venue_contract_id="contract-2",
        outcome_id="yes",
        title="Will BTC close above 100k?",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.56,
        edge=0.14,
        confidence=0.71,
        created_at=NOW,
        updated_at=NOW,
        write_audit=True,
    )
    record_scan_result(
        conn,
        scan_run_id=scan_run_id,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-2",
        venue_contract_id="contract-2",
        outcome_id="yes",
        decision="create_opportunity",
        reason="edge_detected",
        source_snapshot_ids=[],
        source_document_ids=[],
        created_opportunity_id=opportunity_id,
        observed_at=NOW,
        created_at=NOW,
    )
    document_id = record_document(
        conn,
        source_type="rss",
        source_name="Official feed",
        url="https://example.invalid/feed",
        api_endpoint="",
        venue="polymarket",
        venue_market_id="market-2",
        venue_contract_id="contract-2",
        outcome_id="yes",
        asset_symbol="BTC",
        topic="crypto",
        published_at=NOW,
        fetched_at=NOW,
        observed_at=NOW,
        payload_hash="doc-hash-1",
        title="BTC official update",
        normalized_text="normalized",
        raw_payload={"title": "BTC official update"},
        trust_level="official",
        created_at=NOW,
        write_audit=True,
    )
    evidence_pack_id = record_evidence_pack(
        conn,
        opportunity_id=opportunity_id,
        strategy_version_id="strat-v1",
        document_ids=[document_id],
        snapshot_ids=[],
        event_ids=[],
        source_set_version="sources-v1",
        latest_published_at=NOW,
        latest_fetched_at=NOW,
        latest_observed_at=NOW,
        created_at=NOW,
        payload_hash="pack-hash-1",
        write_audit=True,
    )

    scan_results = list_scan_results(conn, scan_run_id=scan_run_id)
    assert scan_results[0]["scan_result_id"] == ignored_result_id
    assert scan_results[0]["decision"] == "ignore"
    assert scan_results[0]["reason"] == "wide_spread"
    assert scan_results[0]["source_snapshot_ids"] == ["snap-1"]
    assert scan_results[0]["source_document_ids"] == ["doc-1"]

    scan_runs = list_scan_runs(conn)
    assert scan_runs == [
        {
            "scan_run_id": scan_run_id,
            "trigger_type": "manual_scan",
            "strategy_version_id": "strat-v1",
            "config_version_id": "cfg-v1",
            "source_set_version": "sources-v1",
            "status": "running",
            "started_at": NOW,
            "completed_at": "",
            "scanned_count": 2,
            "ignored_count": 1,
            "watch_count": 0,
            "created_opportunity_count": 1,
            "error_message": "",
            "created_at": NOW,
        }
    ]

    audit_actions = [row["action"] for row in list_poly_alpha_audit_events(conn)]
    assert "opportunity_discovered" in audit_actions
    assert "document_ingested" in audit_actions
    assert "evidence_pack_created" in audit_actions
    assert evidence_pack_id


def test_evidence_chain_persists_citations_and_lifecycle_records():
    conn = _conn()

    record_config_version(
        conn,
        config_version_id="cfg-v1",
        name="phase-1-defaults",
        validation_freshness_window_sec=300,
        min_exploration_samples=10,
        min_promotion_samples=30,
        min_promotion_history_days=90,
        max_drawdown_threshold=-0.20,
        min_hit_rate=0.52,
        min_payoff_ratio=1.10,
        min_capacity_multiple=2.0,
        promotion_defaults={"risk": "paper_only"},
        created_at=NOW,
        write_audit=True,
    )
    record_source_set(
        conn,
        source_set_version="sources-v1",
        name="phase-1-sources",
        enabled_sources=["polymarket_gamma", "official_rss"],
        trust_policy={"official": "required"},
        created_at=NOW,
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
        created_at=NOW,
        write_audit=True,
    )
    opportunity_id = record_opportunity(
        conn,
        opportunity_id="opp-1",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        title="BTC above 100k",
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
    document_id = record_document(
        conn,
        document_id="doc-1",
        source_type="rss",
        source_name="Official feed",
        url="https://example.invalid/feed",
        api_endpoint="",
        market_id="legacy-market-id",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        asset_symbol="BTC",
        topic="crypto",
        published_at=NOW,
        fetched_at=NOW,
        observed_at=NOW,
        payload_hash="duplicate-hash",
        title="BTC official update",
        normalized_text="normalized",
        raw_payload={"headline": "BTC official update"},
        trust_level="official",
        created_at=NOW,
    )
    duplicate_document_id = record_document(
        conn,
        document_id="doc-duplicate",
        source_type="rss",
        source_name="Official feed",
        url="https://example.invalid/feed",
        api_endpoint="",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        asset_symbol="BTC",
        topic="crypto",
        published_at=NOW,
        fetched_at=NOW,
        observed_at=NOW,
        payload_hash="duplicate-hash",
        title="Different title",
        normalized_text="different",
        raw_payload={"headline": "Different title"},
        trust_level="official",
        created_at=NOW,
    )
    event_id = record_event(
        conn,
        event_id="event-1",
        event_type="crypto_price",
        title="BTC breaks level",
        summary="BTC moved quickly",
        primary_assets=["BTC", "ETH"],
        event_time=NOW,
        status="open",
        created_at=NOW,
        updated_at=NOW,
    )
    link_id = record_event_market_link(
        conn,
        event_id=event_id,
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        adapter_metadata={"condition_id": "cond-1", "asset_id": "asset-1"},
        outcome="yes",
        link_reason="same underlying event",
        link_confidence=0.82,
        created_at=NOW,
        write_audit=True,
    )
    snapshot_id = record_market_snapshot(
        conn,
        snapshot_id="snap-1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        adapter_metadata={"condition_id": "cond-1", "asset_id": "asset-1"},
        source_api="clob",
        observed_at=NOW,
        fetched_at=NOW,
        payload_hash="snap-hash-1",
        best_bid=0.41,
        best_ask=0.43,
        spread=0.02,
        top_bid_depth=200.0,
        top_ask_depth=180.0,
        mid_price=0.42,
        last_trade_price=0.421,
        liquidity=1000.0,
        volume=5000.0,
        raw_payload={"book": "snapshot"},
        created_at=NOW,
    )
    evidence_pack_id = record_evidence_pack(
        conn,
        evidence_pack_id="pack-1",
        opportunity_id=opportunity_id,
        strategy_version_id="strat-v1",
        document_ids=[document_id],
        snapshot_ids=[snapshot_id],
        event_ids=[event_id],
        source_set_version="sources-v1",
        latest_published_at=NOW,
        latest_fetched_at=NOW,
        latest_observed_at=NOW,
        created_at=NOW,
        payload_hash="pack-hash-1",
    )
    research_run_id = record_research_run(
        conn,
        run_id="run-1",
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id=evidence_pack_id,
        strategy_version_id="strat-v1",
        event_id=event_id,
        venue="polymarket",
        venue_market_id="market-1",
        requested_by="user",
        started_at=NOW,
        completed_at=NOW,
        status="completed",
        model_config={"model": "paper-researcher"},
        created_at=NOW,
        write_audit=True,
    )
    finding_id = record_agent_finding(
        conn,
        run_id=research_run_id,
        opportunity_id=opportunity_id,
        evidence_pack_id=evidence_pack_id,
        strategy_version_id="strat-v1",
        agent_role="researcher",
        estimated_probability=0.55,
        market_probability=0.42,
        edge=0.13,
        confidence=0.7,
        recommendation="shadow_signal",
        thesis="Market lagged official evidence",
        evidence_ids=[document_id],
        counter_evidence_ids=[],
        resolution_risks=[],
        blockers=[],
        created_at=NOW,
    )

    assert duplicate_document_id == document_id
    assert len(list_documents(conn)) == 1
    assert list_events(conn)[0]["primary_assets"] == ["BTC", "ETH"]
    assert list_events(conn)[0]["event_type"] == "crypto_price"
    assert list_events(conn)[0]["status"] == "open"
    assert list_event_market_links(conn, event_id=event_id)[0]["link_id"] == link_id
    assert list_event_market_links(conn, event_id=event_id)[0]["venue"] == "polymarket"
    assert list_event_market_links(conn, event_id=event_id)[0]["adapter_metadata"] == {
        "condition_id": "cond-1",
        "asset_id": "asset-1",
    }
    assert list_market_snapshots(conn)[0]["adapter_metadata"]["asset_id"] == "asset-1"
    assert list_evidence_packs(conn)[0]["document_ids"] == [document_id]
    assert list_evidence_packs(conn)[0]["snapshot_ids"] == [snapshot_id]
    assert list_evidence_packs(conn)[0]["event_ids"] == [event_id]
    assert list_research_runs(conn)[0]["opportunity_id"] == opportunity_id
    assert list_research_runs(conn)[0]["evidence_pack_id"] == evidence_pack_id
    assert list_research_runs(conn)[0]["strategy_version_id"] == "strat-v1"
    assert list_research_runs(conn)[0]["model_config"] == {"model": "paper-researcher"}
    assert list_research_runs(conn)[0]["status"] == "completed"
    assert list_agent_findings(conn)[0]["finding_id"] == finding_id
    assert list_agent_findings(conn)[0]["evidence_ids"] == [document_id]
    assert "event_linked" in [row["action"] for row in list_poly_alpha_audit_events(conn)]
    assert "research_completed" in [row["action"] for row in list_poly_alpha_audit_events(conn)]


@pytest.mark.parametrize(
    ("decision", "expected_status", "expected_action"),
    [
        ("pass", "watch", "exploration_passed"),
        ("watch", "watch", "exploration_watch"),
        ("reject", "rejected", "exploration_rejected"),
    ],
)
def test_exploration_decisions_update_status_and_map_to_audit_actions(
    decision,
    expected_status,
    expected_action,
):
    conn = _conn()
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id=f"market-{decision}",
        venue_contract_id=f"contract-{decision}",
        outcome_id="yes",
        title=f"Opportunity {decision}",
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
    exploration_id = record_exploration_decision(
        conn,
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-v1",
        decision=decision,
        reason="gate_result",
        metrics={"evidence_count": 2},
        created_at=NOW,
        expected_status="watch",
        write_audit=True,
    )

    assert list_exploration_decisions(conn)[0]["exploration_id"] == exploration_id
    assert list_exploration_decisions(conn)[0]["metrics"] == {"evidence_count": 2}
    assert list_opportunities(conn)[0]["status"] == expected_status
    assert list_poly_alpha_audit_events(conn)[0]["action"] == expected_action


def test_lifecycle_audit_mapping_and_shadow_validation_promotion_helpers():
    conn = _conn()
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        title="BTC above 100k",
        alpha_family="cross_market_probability",
        status="approved",
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
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-v1",
        event_id="event-1",
        venue="polymarket",
        venue_market_id="market-1",
        requested_by="user",
        started_at=NOW,
        status="running",
        model_config={"model": "paper-researcher"},
        created_at=NOW,
        write_audit=True,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id="market-1",
        venue_contract_id="contract-1",
        outcome_id="yes",
        adapter_metadata={"asset_id": "asset-1"},
        side="buy",
        observed_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        status="shadow",
        created_at=NOW,
        expires_at="2026-05-08T00:00:00Z",
        write_audit=True,
    )
    assert list_opportunities(conn)[0]["status"] == "shadow"
    assert list_shadow_signals(conn)[0]["status"] == "shadow"

    validation_id = record_validation_result(
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
        created_at=NOW,
        write_audit=True,
    )
    assert list_opportunities(conn)[0]["status"] == "validated"
    assert list_shadow_signals(conn)[0]["status"] == "validated"

    promotion_id = record_promotion_decision(
        conn,
        opportunity_id=opportunity_id,
        shadow_signal_id=shadow_signal_id,
        strategy_version_id="strat-v1",
        decision="promote",
        reason="gate_passed",
        prediction_metrics={"hit_rate": 0.6},
        trading_metrics={"payoff_ratio": 1.2},
        metrics={"sample_count": 30},
        critic_blockers=[],
        risk_checks={"paper_only": True},
        proposal_id="",
        decided_at=NOW,
        write_audit=True,
    )
    assert list_opportunities(conn)[0]["status"] == "promoted"
    assert list_shadow_signals(conn)[0]["status"] == "promoted"

    skipped = update_opportunity_status(
        conn,
        opportunity_id=opportunity_id,
        lifecycle_event="paper_fill_skipped",
        primary_reason="approval_latency_risk",
        updated_at=NOW,
        expected_status="promoted",
        write_audit=True,
    )

    assert audit_action_for_lifecycle_event("exploration_pass") == "exploration_passed"
    assert audit_action_for_lifecycle_event("validation_pass") == "validation_completed"
    assert audit_action_for_lifecycle_event("promotion_promote") == "promotion_approved"
    assert audit_action_for_lifecycle_event("promotion_reject") == "promotion_rejected"
    assert audit_action_for_lifecycle_event("promotion_watch") == "promotion_watch"
    assert audit_action_for_lifecycle_event("signal_ttl_expired") == "expired"
    assert audit_action_for_lifecycle_event("proposal_ttl_expired") == "expired"
    assert audit_action_for_lifecycle_event("opportunity_ttl_expired") == "expired"
    assert audit_action_for_lifecycle_event("proposal_created") == "proposal_created"
    assert audit_action_for_lifecycle_event("proposal_approved") == "proposal_approved"
    assert audit_action_for_lifecycle_event("proposal_rejected") == "proposal_rejected"
    assert audit_action_for_lifecycle_event("paper_fill_skipped") == "paper_fill_skipped"

    assert skipped is True
    assert list_shadow_signals(conn)[0]["shadow_signal_id"] == shadow_signal_id
    assert list_shadow_signals(conn)[0]["status"] == "promoted"
    assert list_shadow_signals(conn)[0]["adapter_metadata"] == {"asset_id": "asset-1"}
    assert list_validation_results(conn)[0]["validation_id"] == validation_id
    assert list_validation_results(conn)[0]["pass_fail"] == "pass"
    assert list_promotion_decisions(conn)[0]["promotion_id"] == promotion_id
    assert list_promotion_decisions(conn)[0]["decision"] == "promote"
    assert list_opportunities(conn)[0]["status"] == "skipped"
    assert list_opportunities(conn)[0]["primary_reason"] == "approval_latency_risk"

    audit_actions = [row["action"] for row in list_poly_alpha_audit_events(conn)]
    assert "research_started" in audit_actions
    assert "shadow_signal_created" in audit_actions
    assert "validation_completed" in audit_actions
    assert "promotion_approved" in audit_actions
    assert "paper_fill_skipped" in audit_actions

    with pytest.raises(ValueError, match="Unknown lifecycle event"):
        audit_action_for_lifecycle_event("not_a_lifecycle_event")
    with pytest.raises(ValueError, match="Unsupported shadow signal status"):
        record_shadow_signal(
            conn,
            opportunity_id=opportunity_id,
            run_id=run_id,
            strategy_version_id="strat-v1",
            strategy_family="cross_market_probability",
            venue="polymarket",
            venue_market_id="market-1",
            venue_contract_id="contract-1",
            outcome_id="yes",
            adapter_metadata={},
            side="buy",
            observed_price=0.42,
            estimated_probability=0.55,
            edge=0.13,
            confidence=0.7,
            status="watch",
            created_at=NOW,
            expires_at="2026-05-08T00:00:00Z",
        )


@pytest.mark.parametrize(
    ("pass_fail", "expected_opportunity_status", "expected_signal_status"),
    [
        ("pass", "validated", "validated"),
        ("fail", "rejected", "rejected"),
    ],
)
def test_validation_results_update_opportunity_and_shadow_signal_status(
    pass_fail,
    expected_opportunity_status,
    expected_signal_status,
):
    conn = _conn()
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id=f"market-validation-{pass_fail}",
        venue_contract_id=f"contract-validation-{pass_fail}",
        outcome_id="yes",
        title=f"Validation {pass_fail}",
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
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-v1",
        event_id="event-1",
        venue="polymarket",
        venue_market_id=f"market-validation-{pass_fail}",
        requested_by="user",
        started_at=NOW,
        status="running",
        model_config={},
        created_at=NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id=f"market-validation-{pass_fail}",
        venue_contract_id=f"contract-validation-{pass_fail}",
        outcome_id="yes",
        adapter_metadata={},
        side="buy",
        observed_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        status="shadow",
        created_at=NOW,
        expires_at="2026-05-08T00:00:00Z",
    )

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
        pass_fail=pass_fail,
        failure_reason="" if pass_fail == "pass" else "failed_validation",
        created_at=NOW,
    )

    assert list_opportunities(conn)[0]["status"] == expected_opportunity_status
    assert list_shadow_signals(conn)[0]["status"] == expected_signal_status


@pytest.mark.parametrize(
    ("decision", "expected_opportunity_status", "expected_signal_status"),
    [
        ("promote", "promoted", "promoted"),
        ("reject", "rejected", "rejected"),
        ("watch", "validated", "validated"),
    ],
)
def test_promotion_decisions_update_opportunity_and_shadow_signal_status(
    decision,
    expected_opportunity_status,
    expected_signal_status,
):
    conn = _conn()
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id=f"market-promotion-{decision}",
        venue_contract_id=f"contract-promotion-{decision}",
        outcome_id="yes",
        title=f"Promotion {decision}",
        alpha_family="cross_market_probability",
        status="validated",
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
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-v1",
        event_id="event-1",
        venue="polymarket",
        venue_market_id=f"market-promotion-{decision}",
        requested_by="user",
        started_at=NOW,
        status="running",
        model_config={},
        created_at=NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id=f"market-promotion-{decision}",
        venue_contract_id=f"contract-promotion-{decision}",
        outcome_id="yes",
        adapter_metadata={},
        side="buy",
        observed_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        status="validated",
        created_at=NOW,
        expires_at="2026-05-08T00:00:00Z",
    )

    record_promotion_decision(
        conn,
        opportunity_id=opportunity_id,
        shadow_signal_id=shadow_signal_id,
        strategy_version_id="strat-v1",
        decision=decision,
        reason="gate_result",
        prediction_metrics={},
        trading_metrics={},
        metrics={},
        critic_blockers=[],
        risk_checks={"paper_only": True},
        proposal_id="",
        decided_at=NOW,
    )

    assert list_opportunities(conn)[0]["status"] == expected_opportunity_status
    assert list_shadow_signals(conn)[0]["status"] == expected_signal_status


def test_proposal_lifecycle_event_updates_opportunity_and_writes_audit():
    conn = _conn()
    opportunity_id = record_opportunity(
        conn,
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-proposal",
        venue_contract_id="contract-proposal",
        outcome_id="yes",
        title="Proposal candidate",
        alpha_family="cross_market_probability",
        status="promoted",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        created_at=NOW,
        updated_at=NOW,
    )

    updated = update_opportunity_status(
        conn,
        opportunity_id=opportunity_id,
        lifecycle_event="proposal_created",
        updated_at=NOW,
        expected_status="promoted",
        write_audit=True,
    )

    assert updated is True
    assert list_opportunities(conn)[0]["status"] == "proposed"
    audit = list_poly_alpha_audit_events(conn)
    assert len(audit) == 1
    assert audit[0]["action"] == "proposal_created"
    assert audit[0]["entity_id"] == opportunity_id
