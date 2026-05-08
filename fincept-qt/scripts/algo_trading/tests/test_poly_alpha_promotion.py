import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_promotion import (
    create_paper_proposal_from_promotion,
    evaluate_promotion,
    record_paper_fill_recorded,
    record_post_approval_skip,
    record_proposal_decision,
)
from poly_alpha_store import (
    ensure_poly_alpha_schema,
    list_opportunities,
    list_poly_alpha_audit_events,
    list_promotion_decisions,
    list_shadow_signals,
    record_agent_finding,
    record_opportunity,
    record_research_run,
    record_shadow_signal,
    record_validation_result,
)
from polymarket_store import (
    ensure_polymarket_schema,
    list_audit_events,
    list_trade_proposals,
    record_trade_proposal,
)
from polymarket_models import SignalDecision


NOW = "2026-05-07T00:00:00Z"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ensure_poly_alpha_schema(conn)
    ensure_polymarket_schema(conn)
    return conn


def _seed_validated_shadow(conn: sqlite3.Connection) -> tuple[str, str]:
    opportunity_id = record_opportunity(
        conn,
        opportunity_id="opp-promo",
        strategy_version_id="strat-v1",
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
        created_at=NOW,
        updated_at=NOW,
    )
    run_id = record_research_run(
        conn,
        run_id="run-promo",
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
        model_config={},
        created_at=NOW,
    )
    shadow_signal_id = record_shadow_signal(
        conn,
        shadow_signal_id="shadow-promo",
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
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
        created_at=NOW,
    )
    return opportunity_id, shadow_signal_id


def _passing_config(**overrides):
    config = {
        "min_promotion_samples": 30,
        "min_promotion_history_days": 90,
        "sample_count": 30,
        "history_days": 10,
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
    config.update(overrides)
    return config


def _seed_wrong_opportunity(conn: sqlite3.Connection) -> None:
    record_opportunity(
        conn,
        opportunity_id="opp-wrong",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-2",
        venue_contract_id="condition-2",
        outcome_id="yes",
        title="Wrong candidate",
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


def test_promotion_gate_promotes_and_records_required_metrics():
    conn = _conn()
    opportunity_id, shadow_signal_id = _seed_validated_shadow(conn)

    promotion_id = evaluate_promotion(conn, shadow_signal_id, _passing_config(), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["promotion_id"] == promotion_id
    assert decision["decision"] == "promote"
    assert decision["prediction_metrics"]["brier_score"] == 0.21
    assert decision["prediction_metrics"]["calibration_error"] == 0.02
    assert decision["prediction_metrics"]["edge_decay"] == 0.01
    assert decision["trading_metrics"]["cost_adjusted_net_return"] == 0.08
    assert decision["trading_metrics"]["median_clv_after_costs"] == 0.03
    assert decision["trading_metrics"]["approval_latency_impact"]["median_seconds"] == 12
    assert decision["risk_checks"]["lookahead_check_passed"] is True
    assert decision["risk_checks"]["survivorship_check_passed"] is True
    assert decision["risk_checks"]["risk_reviewer_approved"] is True
    assert list_opportunities(conn)[0]["opportunity_id"] == opportunity_id
    assert list_opportunities(conn)[0]["status"] == "promoted"
    assert list_shadow_signals(conn)[0]["status"] == "promoted"


def test_promotion_gate_enforces_hard_coverage_floor_and_allows_90_days():
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(
        conn,
        "shadow-promo",
        _passing_config(min_promotion_samples=1, min_promotion_history_days=1, sample_count=1, history_days=10),
        NOW,
    )

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "watch"
    assert decision["reason"] == "insufficient_promotion_coverage"

    conn = _conn()
    _seed_validated_shadow(conn)
    evaluate_promotion(
        conn,
        "shadow-promo",
        _passing_config(min_promotion_samples=1, min_promotion_history_days=1, sample_count=1, history_days=90),
        NOW,
    )

    assert list_promotion_decisions(conn)[0]["decision"] == "promote"


@pytest.mark.parametrize("override", [{"approval_latency_impact": None}, {}])
def test_promotion_gate_rejects_missing_approval_latency_impact(override):
    conn = _conn()
    _seed_validated_shadow(conn)
    config = _passing_config()
    if override:
        config.update(override)
    else:
        config.pop("approval_latency_impact")

    evaluate_promotion(conn, "shadow-promo", config, NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "missing_approval_latency_impact"


@pytest.mark.parametrize(
    "approval_latency_impact",
    [
        {"median_seconds": float("nan")},
        {"distribution": {"p50_seconds": 12, "p95_seconds": float("inf")}},
        {"median_seconds": "bad"},
    ],
)
def test_promotion_gate_rejects_invalid_approval_latency_impact_without_writing_nan(
    approval_latency_impact,
):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(
        conn,
        "shadow-promo",
        _passing_config(approval_latency_impact=approval_latency_impact),
        NOW,
    )

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "invalid_approval_latency_impact"
    assert "NaN" not in conn.execute(
        """
        SELECT trading_metrics_json
        FROM poly_alpha_promotion_decisions
        """
    ).fetchone()[0]


def test_promotion_gate_requires_resolved_prediction_metrics_only_when_resolved_outcomes_exist():
    conn = _conn()
    _seed_validated_shadow(conn)
    conn.execute(
        """
        UPDATE poly_alpha_validation_results
        SET brier_score = NULL, calibration_error = NULL
        """
    )

    evaluate_promotion(conn, "shadow-promo", _passing_config(resolved_outcomes_exist=False), NOW)

    assert list_promotion_decisions(conn)[0]["decision"] == "promote"

    conn = _conn()
    _seed_validated_shadow(conn)
    conn.execute(
        """
        UPDATE poly_alpha_validation_results
        SET brier_score = NULL, calibration_error = NULL
        """
    )
    evaluate_promotion(conn, "shadow-promo", _passing_config(resolved_outcomes_exist=True), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "missing_resolved_prediction_metrics"


def test_promotion_gate_requires_edge_decay_only_when_unresolved_markets_exist():
    conn = _conn()
    _seed_validated_shadow(conn)
    config = _passing_config(unresolved_markets_exist=False)
    config.pop("unresolved_metrics")

    evaluate_promotion(conn, "shadow-promo", config, NOW)

    assert list_promotion_decisions(conn)[0]["decision"] == "promote"

    conn = _conn()
    _seed_validated_shadow(conn)
    config = _passing_config(unresolved_markets_exist=True)
    config.pop("unresolved_metrics")
    evaluate_promotion(conn, "shadow-promo", config, NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "missing_unresolved_edge_decay"


@pytest.mark.parametrize(
    ("override", "expected_decision", "reason"),
    [
        ({"sample_count": 29, "history_days": 89}, "watch", "insufficient_promotion_coverage"),
        ({"cost_adjusted_net_return": 0.0}, "reject", "non_positive_net_return"),
        ({"median_clv_after_costs": 0.0}, "reject", "non_positive_median_clv"),
        ({"max_drawdown": -0.25}, "reject", "drawdown_below_threshold"),
        ({"hit_rate": 0.51}, "reject", "hit_rate_below_threshold"),
        ({"payoff_ratio": 1.0}, "reject", "payoff_ratio_below_threshold"),
        ({"capacity": 49.0}, "reject", "capacity_too_small"),
        ({"lookahead_check_passed": False}, "reject", "lookahead_check_failed"),
        ({"survivorship_check_passed": False}, "reject", "survivorship_check_failed"),
        ({"risk_reviewer_approved": False}, "reject", "risk_reviewer_not_approved"),
    ],
)
def test_promotion_gate_rejects_or_watches_failed_requirements(
    override,
    expected_decision,
    reason,
):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(**override), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == expected_decision
    assert decision["reason"] == reason


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"lookahead_check_passed": "false"}, "lookahead_check_failed"),
        ({"survivorship_check_passed": "false"}, "survivorship_check_failed"),
        ({"risk_reviewer_approved": "false"}, "risk_reviewer_not_approved"),
        ({"lookahead_check_passed": "not-a-bool"}, "lookahead_check_failed"),
    ],
)
def test_promotion_gate_requires_literal_true_for_risk_checks(override, reason):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(**override), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == reason


@pytest.mark.parametrize(
    ("override", "expected_decision", "reason"),
    [
        ({"hit_rate": 0.50, "payoff_ratio": 1.50}, "promote", "gate_passed"),
        ({"hit_rate": 0.60, "payoff_ratio": 1.00}, "promote", "gate_passed"),
        ({"hit_rate": 0.50, "payoff_ratio": 1.00}, "reject", "hit_rate_below_threshold"),
    ],
)
def test_promotion_gate_allows_hit_rate_and_payoff_ratio_exceptions(
    override,
    expected_decision,
    reason,
):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(**override), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == expected_decision
    assert decision["reason"] == reason


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"paper_order_size": 0.0}, "invalid_paper_order_size"),
        ({"paper_order_size": -1.0}, "invalid_paper_order_size"),
        ({"capacity": float("nan")}, "invalid_capacity"),
        ({"cost_adjusted_net_return": float("nan")}, "invalid_cost_adjusted_net_return"),
        ({"median_clv_after_costs": float("nan")}, "invalid_median_clv_after_costs"),
        ({"max_drawdown": float("nan")}, "invalid_max_drawdown"),
        ({"hit_rate": float("nan")}, "invalid_hit_rate"),
        ({"payoff_ratio": float("nan")}, "invalid_payoff_ratio"),
        ({"max_drawdown_threshold": float("nan")}, "invalid_max_drawdown_threshold"),
        ({"min_hit_rate": float("nan")}, "invalid_min_hit_rate"),
        ({"min_payoff_ratio": float("nan")}, "invalid_min_payoff_ratio"),
    ],
)
def test_promotion_gate_rejects_invalid_numeric_metrics_without_promoting(override, reason):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(**override), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == reason
    assert list_opportunities(conn)[0]["status"] == "rejected"
    assert "NaN" not in conn.execute(
        """
        SELECT trading_metrics_json || metrics_json
        FROM poly_alpha_promotion_decisions
        """
    ).fetchone()[0]


@pytest.mark.parametrize(
    "override",
    [
        {"hit_rate": -0.01},
        {"hit_rate": 1.01},
        {"payoff_ratio": -0.01},
        {"payoff_ratio": 0.0},
        {"min_hit_rate": -0.01},
        {"min_hit_rate": 1.01},
        {"min_payoff_ratio": -0.01},
        {"min_payoff_ratio": 0.0},
    ],
)
def test_promotion_gate_rejects_invalid_promotion_metric_ranges(override):
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(**override), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "invalid_promotion_metrics"


def test_promotion_gate_rejects_invalid_sample_metrics_without_raw_exception():
    conn = _conn()
    _seed_validated_shadow(conn)

    evaluate_promotion(conn, "shadow-promo", _passing_config(sample_count="bad"), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "invalid_promotion_metrics"


def test_promotion_gate_rejects_blocking_validation_and_agent_findings():
    conn = _conn()
    opportunity_id, shadow_signal_id = _seed_validated_shadow(conn)
    record_validation_result(
        conn,
        opportunity_id=opportunity_id,
        shadow_signal_id=shadow_signal_id,
        strategy_version_id="strat-v1",
        entry_snapshot_id="snap-late-entry",
        exit_snapshot_id="snap-late-exit",
        validation_type="event_time",
        entry_price=0.42,
        exit_price=0.41,
        holding_period="1h",
        gross_return=-0.02,
        cost_adjusted_return=-0.03,
        closing_line_value=-0.01,
        brier_score=None,
        calibration_error=None,
        edge_decay=0.02,
        information_lag_sec=120,
        fetch_lag_sec=30,
        market_move_before_signal=0.08,
        market_move_after_signal=0.01,
        max_adverse_excursion=-0.04,
        max_favorable_excursion=0.02,
        liquidity_assumption="top_of_book",
        slippage_assumption="one_tick",
        pass_fail="fail",
        failure_reason="late_information",
        created_at=NOW,
    )
    record_agent_finding(
        conn,
        run_id="run-promo",
        opportunity_id=opportunity_id,
        evidence_pack_id="pack-1",
        strategy_version_id="strat-v1",
        agent_role="critic",
        estimated_probability=0.5,
        market_probability=0.42,
        edge=0.08,
        confidence=0.7,
        recommendation="block",
        thesis="late data",
        evidence_ids=[],
        counter_evidence_ids=[],
        resolution_risks=[],
        blockers=[{"reason": "data_leak", "resolved": False}],
        created_at=NOW,
    )

    evaluate_promotion(conn, shadow_signal_id, _passing_config(), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "late_information"
    assert decision["critic_blockers"] == [{"reason": "data_leak", "resolved": False}]


def test_promotion_gate_rejects_late_information_from_any_validation_type():
    conn = _conn()
    _seed_validated_shadow(conn)
    conn.execute(
        """
        UPDATE poly_alpha_validation_results
        SET failure_reason = 'late_information'
        WHERE shadow_signal_id = 'shadow-promo'
          AND validation_type = 'fixed_horizon'
        """
    )

    evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)

    decision = list_promotion_decisions(conn)[0]
    assert decision["decision"] == "reject"
    assert decision["reason"] == "late_information"


def test_promotion_lifecycle_watch_reject_promote_updates_opportunity_and_shadow():
    for decision, expected_status in [
        ("watch", "validated"),
        ("reject", "rejected"),
        ("promote", "promoted"),
    ]:
        conn = _conn()
        _seed_validated_shadow(conn)
        config = _passing_config()
        if decision == "watch":
            config.update({"sample_count": 29, "history_days": 89})
        elif decision == "reject":
            config.update({"capacity": 49.0})

        evaluate_promotion(conn, "shadow-promo", config, NOW)

        assert list_opportunities(conn)[0]["status"] == expected_status
        assert list_shadow_signals(conn)[0]["status"] == expected_status


def test_paper_proposal_bridge_requires_promotion_and_records_paper_queue_lineage():
    conn = _conn()
    _seed_validated_shadow(conn)
    with pytest.raises(ValueError, match="promote"):
        create_paper_proposal_from_promotion(conn, "missing", "dep-1", NOW)

    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)

    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert proposal["proposal_id"] == proposal_id
    assert proposal["status"] == "proposed"
    assert proposal["size"] == 25.0
    assert proposal["features"]["source"] == "poly_alpha"
    assert proposal["features"]["paper_only"] is True
    assert proposal["features"]["promotion_id"] == promotion_id
    assert proposal["features"]["shadow_signal_id"] == "shadow-promo"
    assert proposal["features"]["opportunity_id"] == "opp-promo"
    assert proposal["features"]["strategy_version_id"] == "strat-v1"
    assert list_promotion_decisions(conn)[0]["proposal_id"] == proposal_id
    assert list_opportunities(conn)[0]["status"] == "proposed"
    assert "proposal_created" in [row["action"] for row in list_poly_alpha_audit_events(conn)]
    assert "proposal_created" in [row["action"] for row in list_audit_events(conn, "dep-1")]


def test_paper_proposal_bridge_rolls_back_when_opportunity_lineage_update_fails():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    conn.execute(
        f"""
        CREATE TRIGGER reject_opportunity_before_proposal_lineage
        AFTER UPDATE OF proposal_id ON poly_alpha_promotion_decisions
        WHEN NEW.promotion_id = '{promotion_id}'
        BEGIN
            UPDATE poly_alpha_opportunities
            SET status = 'rejected'
            WHERE opportunity_id = 'opp-promo';
        END
        """
    )

    with pytest.raises(ValueError, match="proposal_created"):
        create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)

    assert list_trade_proposals(conn, "dep-1") == []
    assert list_promotion_decisions(conn)[0]["proposal_id"] == ""
    assert "proposal_created" not in [row["action"] for row in list_poly_alpha_audit_events(conn)]


def test_manual_proposal_and_paper_fill_lifecycle_bridge_writes_poly_alpha_audit():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)

    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")
    assert list_opportunities(conn)[0]["status"] == "approved"
    assert "proposal_approved" in [row["action"] for row in list_poly_alpha_audit_events(conn)]

    assert record_paper_fill_recorded(conn, "opp-promo", proposal_id, "trade-1", NOW)
    assert list_opportunities(conn)[0]["status"] == "filled"
    assert "paper_fill_recorded" in [row["action"] for row in list_poly_alpha_audit_events(conn)]

    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "rejected", "user", NOW, "no")
    assert list_opportunities(conn)[0]["status"] == "rejected"
    assert "proposal_rejected" in [row["action"] for row in list_poly_alpha_audit_events(conn)]

    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")
    assert record_post_approval_skip(conn, "opp-promo", proposal_id, "approval_latency_risk", NOW)
    assert list_opportunities(conn)[0]["status"] == "skipped"
    assert list_opportunities(conn)[0]["primary_reason"] == "approval_latency_risk"
    assert "paper_fill_skipped" in [row["action"] for row in list_poly_alpha_audit_events(conn)]
    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert proposal["status"] == "failed"
    assert proposal["decision_reason"] == "approval_latency_risk"
    assert proposal["reason"] == "gate_passed"
    assert proposal["fill_trade_id"] == ""


def test_post_approval_skip_rolls_back_when_opportunity_update_fails():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")
    conn.execute(
        f"""
        CREATE TRIGGER reset_opportunity_before_skip_lineage
        AFTER UPDATE OF status ON algo_polymarket_trade_proposals
        WHEN NEW.proposal_id = '{proposal_id}' AND NEW.status = 'failed'
        BEGIN
            UPDATE poly_alpha_opportunities
            SET status = 'proposed'
            WHERE opportunity_id = 'opp-promo';
        END
        """
    )

    with pytest.raises(ValueError, match="paper_fill_skipped"):
        record_post_approval_skip(conn, "opp-promo", proposal_id, "approval_latency_risk", NOW)

    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert proposal["status"] == "approved"
    assert proposal["decision_reason"] == "ok"
    assert list_opportunities(conn)[0]["status"] == "approved"
    assert "paper_fill_skipped" not in [row["action"] for row in list_poly_alpha_audit_events(conn)]


def test_proposal_decision_rolls_back_when_opportunity_lineage_update_fails():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = 'rejected'
        WHERE opportunity_id = 'opp-promo'
        """
    )

    with pytest.raises(ValueError, match="proposal_approved"):
        record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")

    proposal = list_trade_proposals(conn, "dep-1")[0]
    poly_alpha_actions = [row["action"] for row in list_poly_alpha_audit_events(conn)]
    polymarket_actions = [row["action"] for row in list_audit_events(conn, "dep-1")]
    assert proposal["status"] == "proposed"
    assert proposal["decided_by"] == ""
    assert proposal["decided_at"] == ""
    assert proposal["decision_reason"] == ""
    assert list_opportunities(conn)[0]["status"] == "rejected"
    assert "proposal_approved" not in poly_alpha_actions
    assert "proposal_approved" not in polymarket_actions


def test_post_approval_skip_requires_approved_proposal():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)

    assert record_post_approval_skip(conn, "opp-promo", proposal_id, "approval_latency_risk", NOW) is False
    assert list_opportunities(conn)[0]["status"] == "proposed"


def test_post_approval_skip_requires_matching_opportunity_id():
    conn = _conn()
    _seed_validated_shadow(conn)
    _seed_wrong_opportunity(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")

    assert record_post_approval_skip(conn, "opp-wrong", proposal_id, "approval_latency_risk", NOW) is False

    statuses = {row["opportunity_id"]: row["status"] for row in list_opportunities(conn)}
    assert statuses["opp-promo"] == "approved"
    assert statuses["opp-wrong"] == "watch"


def test_poly_alpha_proposal_bridge_rejects_missing_opportunity_id_as_value_error():
    conn = _conn()
    signal = SignalDecision(
        asset_id="asset-1",
        action="buy",
        entry_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.7,
        reason="malformed",
        features={"source": "poly_alpha", "paper_only": True},
    )
    proposal_id = record_trade_proposal(
        conn,
        "dep-1",
        "strat-v1",
        "market-1",
        "condition-1",
        signal,
        25.0,
        NOW,
        "2026-05-08T00:00:00Z",
    )

    with pytest.raises(ValueError, match="opportunity_id"):
        record_post_approval_skip(conn, "opp-promo", proposal_id, "approval_latency_risk", NOW)


def test_paper_fill_requires_matching_opportunity_id_without_half_success():
    conn = _conn()
    _seed_validated_shadow(conn)
    _seed_wrong_opportunity(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")

    assert record_paper_fill_recorded(conn, "opp-wrong", proposal_id, "trade-1", NOW) is False

    statuses = {row["opportunity_id"]: row["status"] for row in list_opportunities(conn)}
    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert statuses["opp-promo"] == "approved"
    assert statuses["opp-wrong"] == "watch"
    assert proposal["status"] == "approved"
    assert proposal["fill_trade_id"] == ""


def test_paper_fill_does_not_fill_proposal_when_opportunity_update_would_fail():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = 'proposed'
        WHERE opportunity_id = 'opp-promo'
        """
    )

    assert record_paper_fill_recorded(conn, "opp-promo", proposal_id, "trade-1", NOW) is False

    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert list_opportunities(conn)[0]["status"] == "proposed"
    assert proposal["status"] == "approved"
    assert proposal["fill_trade_id"] == ""


def test_paper_fill_rolls_back_when_opportunity_lineage_update_fails():
    conn = _conn()
    _seed_validated_shadow(conn)
    promotion_id = evaluate_promotion(conn, "shadow-promo", _passing_config(), NOW)
    proposal_id = create_paper_proposal_from_promotion(conn, promotion_id, "dep-1", NOW)
    assert record_proposal_decision(conn, proposal_id, "approved", "user", NOW, "ok")
    conn.execute(
        f"""
        CREATE TRIGGER reset_opportunity_before_fill_lineage
        AFTER UPDATE OF status ON algo_polymarket_trade_proposals
        WHEN NEW.proposal_id = '{proposal_id}' AND NEW.status = 'filled'
        BEGIN
            UPDATE poly_alpha_opportunities
            SET status = 'rejected'
            WHERE opportunity_id = 'opp-promo';
        END
        """
    )

    with pytest.raises(ValueError, match="paper_fill_recorded"):
        record_paper_fill_recorded(conn, "opp-promo", proposal_id, "trade-1", NOW)

    proposal = list_trade_proposals(conn, "dep-1")[0]
    assert proposal["status"] == "approved"
    assert proposal["fill_trade_id"] == ""
    assert list_opportunities(conn)[0]["status"] == "approved"
    assert "paper_fill_recorded" not in [row["action"] for row in list_poly_alpha_audit_events(conn)]


@pytest.mark.parametrize(
    "live_key",
    [
        "api_key",
        "api_token",
        "api_passphrase",
        "api_secret",
        "authenticated_clob_client",
        "clob",
        "clob_api_key",
        "clob_api_passphrase",
        "clob_api_secret",
        "clob_client",
        "clob_order_client",
        "clob_order_endpoint",
        "live_order_endpoint",
        "live_trading",
        "order_client",
        "order_endpoint",
        "private_key",
        "secret",
    ],
)
def test_live_trading_fields_are_rejected(live_key):
    conn = _conn()
    _seed_validated_shadow(conn)

    config = _passing_config(nested=[{"safe": [{"live": {live_key: "bad"}}]}])
    with pytest.raises(ValueError, match="live trading fields"):
        evaluate_promotion(conn, "shadow-promo", config, NOW)
