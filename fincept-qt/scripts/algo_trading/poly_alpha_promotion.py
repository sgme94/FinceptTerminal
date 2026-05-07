from __future__ import annotations

import json
import sqlite3
from typing import Any

from poly_alpha_store import (
    list_agent_findings,
    list_opportunities,
    list_promotion_decisions,
    list_shadow_signals,
    list_validation_results,
    record_promotion_decision,
    update_opportunity_status,
)
from polymarket_models import SignalDecision
from polymarket_store import (
    record_audit_event,
    record_trade_proposal,
    update_trade_proposal_status,
)


_LIVE_TRADING_KEYS = {
    "api_secret",
    "authenticated_clob_client",
    "clob_client",
    "live_order_endpoint",
    "live_trading",
    "order_endpoint",
    "private_key",
}

_MIN_PROMOTION_SAMPLES_FLOOR = 30
_MIN_PROMOTION_HISTORY_DAYS_FLOOR = 90


def evaluate_promotion(
    conn: sqlite3.Connection,
    shadow_signal_id: str,
    config: dict[str, Any],
    now: str,
) -> str:
    _reject_live_fields(config)
    shadow = _one(
        [row for row in list_shadow_signals(conn) if row["shadow_signal_id"] == shadow_signal_id],
        f"Unknown shadow_signal_id: {shadow_signal_id}",
    )
    opportunity = _one(
        [
            row
            for row in list_opportunities(conn)
            if row["opportunity_id"] == shadow["opportunity_id"]
        ],
        f"Unknown opportunity_id: {shadow['opportunity_id']}",
    )
    validations = [
        row for row in list_validation_results(conn) if row["shadow_signal_id"] == shadow_signal_id
    ]
    critic_blockers = _unresolved_critic_blockers(conn, shadow["opportunity_id"])

    prediction_metrics = _prediction_metrics(validations, config)
    trading_metrics = {
        "cost_adjusted_net_return": _number(config, "cost_adjusted_net_return"),
        "median_clv_after_costs": _number(config, "median_clv_after_costs"),
        "max_drawdown": _number(config, "max_drawdown"),
        "hit_rate": _number(config, "hit_rate"),
        "payoff_ratio": _number(config, "payoff_ratio"),
        "capacity": _number(config, "capacity"),
        "paper_order_size": _number(config, "paper_order_size"),
        "approval_latency_impact": config.get("approval_latency_impact", {}),
    }
    risk_checks = {
        "lookahead_check_passed": bool(config.get("lookahead_check_passed", False)),
        "survivorship_check_passed": bool(config.get("survivorship_check_passed", False)),
        "risk_reviewer_approved": bool(config.get("risk_reviewer_approved", False)),
        "risk_reviewer": config.get("risk_reviewer", ""),
        "paper_only": True,
    }
    metrics = {
        "sample_count": int(config.get("sample_count", 0)),
        "history_days": int(config.get("history_days", 0)),
        "min_promotion_samples": max(
            int(config.get("min_promotion_samples", _MIN_PROMOTION_SAMPLES_FLOOR)),
            _MIN_PROMOTION_SAMPLES_FLOOR,
        ),
        "min_promotion_history_days": max(
            int(config.get("min_promotion_history_days", _MIN_PROMOTION_HISTORY_DAYS_FLOOR)),
            _MIN_PROMOTION_HISTORY_DAYS_FLOOR,
        ),
        "max_drawdown_threshold": _number(config, "max_drawdown_threshold"),
        "min_hit_rate": _number(config, "min_hit_rate"),
        "min_payoff_ratio": _number(config, "min_payoff_ratio"),
        "min_capacity_multiple": float(config.get("min_capacity_multiple", 2.0)),
    }

    decision, reason = _gate_decision(
        validations=validations,
        critic_blockers=critic_blockers,
        prediction_metrics=prediction_metrics,
        trading_metrics=trading_metrics,
        risk_checks=risk_checks,
        metrics=metrics,
    )
    return record_promotion_decision(
        conn,
        opportunity_id=opportunity["opportunity_id"],
        shadow_signal_id=shadow_signal_id,
        strategy_version_id=shadow["strategy_version_id"],
        decision=decision,
        reason=reason,
        prediction_metrics=prediction_metrics,
        trading_metrics=trading_metrics,
        metrics=metrics,
        critic_blockers=critic_blockers,
        risk_checks=risk_checks,
        proposal_id="",
        decided_at=now,
        write_audit=True,
    )


def create_paper_proposal_from_promotion(
    conn: sqlite3.Connection,
    promotion_id: str,
    deployment_id: str,
    now: str,
) -> str:
    promotion = _one(
        [row for row in list_promotion_decisions(conn) if row["promotion_id"] == promotion_id],
        "Promotion decision must exist and be promote",
    )
    if promotion["decision"] != "promote":
        raise ValueError("Promotion decision must be promote before creating a proposal")
    opportunity = _one(
        [
            row
            for row in list_opportunities(conn)
            if row["opportunity_id"] == promotion["opportunity_id"]
        ],
        f"Unknown opportunity_id: {promotion['opportunity_id']}",
    )
    shadow = _one(
        [
            row
            for row in list_shadow_signals(conn)
            if row["shadow_signal_id"] == promotion["shadow_signal_id"]
        ],
        f"Unknown shadow_signal_id: {promotion['shadow_signal_id']}",
    )
    if opportunity["status"] != "promoted" or shadow["status"] != "promoted":
        raise ValueError("Promotion decision must leave opportunity and shadow promoted")

    features = {
        "source": "poly_alpha",
        "promotion_id": promotion_id,
        "shadow_signal_id": shadow["shadow_signal_id"],
        "opportunity_id": opportunity["opportunity_id"],
        "strategy_version_id": promotion["strategy_version_id"],
        "paper_only": True,
    }
    signal = SignalDecision(
        asset_id=shadow["adapter_metadata"].get("asset_id") or shadow["outcome_id"],
        action=shadow["side"],
        entry_price=shadow["observed_price"],
        estimated_probability=shadow["estimated_probability"],
        edge=shadow["edge"],
        confidence=shadow["confidence"],
        reason=promotion["reason"],
        features=features,
    )
    size = float(promotion["trading_metrics"].get("paper_order_size") or 0.0)
    proposal_id = record_trade_proposal(
        conn,
        deployment_id,
        promotion["strategy_version_id"],
        opportunity["venue_market_id"],
        opportunity["venue_contract_id"],
        signal,
        size,
        now,
        shadow["expires_at"],
    )
    conn.execute(
        """
        UPDATE poly_alpha_promotion_decisions
        SET proposal_id = ?
        WHERE promotion_id = ?
        """,
        (proposal_id, promotion_id),
    )
    update_opportunity_status(
        conn,
        opportunity_id=opportunity["opportunity_id"],
        lifecycle_event="proposal_created",
        updated_at=now,
        expected_status="promoted",
        write_audit=True,
    )
    record_audit_event(
        conn,
        deployment_id,
        promotion["strategy_version_id"],
        "system",
        "poly_alpha_promotion",
        "proposal_created",
        "proposal",
        proposal_id,
        {},
        {"status": "proposed", "features": features},
        "success",
        "promotion_approved",
        "",
        now,
    )
    return proposal_id


def record_proposal_decision(
    conn: sqlite3.Connection,
    proposal_id: str,
    status: str,
    decided_by: str,
    decided_at: str,
    decision_reason: str,
) -> bool:
    if status not in {"approved", "rejected"}:
        raise ValueError("Proposal decision must be approved or rejected")
    bridge = _proposal_bridge(conn, proposal_id)
    updated = update_trade_proposal_status(
        conn,
        proposal_id,
        status,
        decided_by,
        decided_at,
        decision_reason,
        deployment_id=bridge["deployment_id"],
        expected_status="proposed",
    )
    if not updated:
        return False
    update_opportunity_status(
        conn,
        opportunity_id=bridge["opportunity_id"],
        lifecycle_event=f"proposal_{status}",
        primary_reason=decision_reason if status == "rejected" else None,
        updated_at=decided_at,
        expected_status="proposed",
        write_audit=True,
    )
    record_audit_event(
        conn,
        bridge["deployment_id"],
        bridge["strategy_id"],
        "user",
        decided_by,
        f"proposal_{status}",
        "proposal",
        proposal_id,
        {"status": "proposed"},
        {"status": status},
        "success",
        decision_reason,
        "",
        decided_at,
    )
    return True


def record_post_approval_skip(
    conn: sqlite3.Connection,
    opportunity_id: str,
    proposal_id: str,
    reason: str,
    now: str,
) -> bool:
    bridge = _proposal_bridge(conn, proposal_id)
    if bridge["status"] != "approved":
        return False
    if bridge["features"].get("opportunity_id") != opportunity_id:
        return False
    return update_opportunity_status(
        conn,
        opportunity_id=opportunity_id,
        lifecycle_event="paper_fill_skipped",
        primary_reason=reason,
        updated_at=now,
        expected_status="approved",
        write_audit=True,
    )


def record_paper_fill_recorded(
    conn: sqlite3.Connection,
    opportunity_id: str,
    proposal_id: str,
    fill_trade_id: str,
    now: str,
) -> bool:
    bridge = _proposal_bridge(conn, proposal_id)
    updated = update_trade_proposal_status(
        conn,
        proposal_id,
        "filled",
        "polymarket_runner",
        now,
        "paper_fill_recorded",
        fill_trade_id=fill_trade_id,
        deployment_id=bridge["deployment_id"],
        expected_status="approved",
    )
    if not updated:
        return False
    return update_opportunity_status(
        conn,
        opportunity_id=opportunity_id,
        lifecycle_event="paper_fill_recorded",
        updated_at=now,
        expected_status="approved",
        write_audit=True,
    )


def _gate_decision(
    *,
    validations: list[dict],
    critic_blockers: list[dict],
    prediction_metrics: dict,
    trading_metrics: dict,
    risk_checks: dict,
    metrics: dict,
) -> tuple[str, str]:
    for row in validations:
        if row["validation_type"] == "event_time" and row["failure_reason"] == "late_information":
            return "reject", "late_information"
    if critic_blockers:
        return "reject", "critic_blocker"
    if not risk_checks["lookahead_check_passed"]:
        return "reject", "lookahead_check_failed"
    if not risk_checks["survivorship_check_passed"]:
        return "reject", "survivorship_check_failed"
    if not risk_checks["risk_reviewer_approved"]:
        return "reject", "risk_reviewer_not_approved"
    if (
        prediction_metrics.get("resolved_outcomes_exist", True)
        and (
            prediction_metrics.get("brier_score") is None
            or prediction_metrics.get("calibration_error") is None
        )
    ):
        return "reject", "missing_resolved_prediction_metrics"
    if prediction_metrics.get("unresolved_markets_exist", True) and prediction_metrics.get("edge_decay") is None:
        return "reject", "missing_unresolved_edge_decay"
    if not trading_metrics.get("approval_latency_impact"):
        return "reject", "missing_approval_latency_impact"
    if trading_metrics["cost_adjusted_net_return"] <= 0:
        return "reject", "non_positive_net_return"
    if trading_metrics["median_clv_after_costs"] <= 0:
        return "reject", "non_positive_median_clv"
    if trading_metrics["max_drawdown"] < metrics["max_drawdown_threshold"]:
        return "reject", "drawdown_below_threshold"
    if trading_metrics["hit_rate"] < metrics["min_hit_rate"]:
        return "reject", "hit_rate_below_threshold"
    if trading_metrics["payoff_ratio"] < metrics["min_payoff_ratio"]:
        return "reject", "payoff_ratio_below_threshold"
    if trading_metrics["capacity"] < metrics["min_capacity_multiple"] * trading_metrics["paper_order_size"]:
        return "reject", "capacity_too_small"
    coverage_ok = (
        metrics["sample_count"] >= metrics["min_promotion_samples"]
        or metrics["history_days"] >= metrics["min_promotion_history_days"]
    )
    if not coverage_ok:
        return "watch", "insufficient_promotion_coverage"
    return "promote", "gate_passed"


def _prediction_metrics(validations: list[dict], config: dict[str, Any]) -> dict:
    resolved_outcomes_exist = bool(
        config["resolved_outcomes_exist"]
        if "resolved_outcomes_exist" in config
        else validations
    )
    unresolved_markets_exist = bool(config.get("unresolved_markets_exist", True))
    resolved = [
        row for row in validations if row.get("brier_score") is not None and row.get("calibration_error") is not None
    ]
    brier_score = _median([row["brier_score"] for row in resolved])
    calibration_error = _median([row["calibration_error"] for row in resolved])
    unresolved_edge_decay = config.get("unresolved_metrics", {}).get("edge_decay")
    if unresolved_edge_decay is None:
        unresolved_edge_decay = _median(
            [row["edge_decay"] for row in validations if row.get("edge_decay") is not None]
        )
    return {
        "brier_score": brier_score,
        "calibration_error": calibration_error,
        "edge_decay": unresolved_edge_decay,
        "resolved_outcomes_exist": resolved_outcomes_exist,
        "unresolved_markets_exist": unresolved_markets_exist,
    }


def _unresolved_critic_blockers(conn: sqlite3.Connection, opportunity_id: str) -> list[dict]:
    blockers: list[dict] = []
    for finding in list_agent_findings(conn):
        if finding["opportunity_id"] != opportunity_id or finding["agent_role"] != "critic":
            continue
        for blocker in finding["blockers"]:
            if not blocker.get("resolved", False):
                blockers.append(blocker)
    return blockers


def _proposal_bridge(conn: sqlite3.Connection, proposal_id: str) -> dict:
    row = conn.execute(
        """
        SELECT deployment_id, strategy_id, features_json, status
        FROM algo_polymarket_trade_proposals
        WHERE proposal_id = ?
        """,
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown proposal_id: {proposal_id}")
    features = json.loads(row[2] or "{}")
    if features.get("source") != "poly_alpha" or features.get("paper_only") is not True:
        raise ValueError("Proposal is not a Poly Alpha paper proposal")
    return {
        "deployment_id": row[0],
        "strategy_id": row[1],
        "opportunity_id": features["opportunity_id"],
        "features": features,
        "status": row[3],
    }


def _reject_live_fields(value: Any) -> None:
    if isinstance(value, dict):
        if _LIVE_TRADING_KEYS.intersection(value):
            raise ValueError("MVP paper-only bridge rejects live trading fields")
        for nested in value.values():
            _reject_live_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_live_fields(nested)


def _number(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if value is None:
        return 0.0
    return float(value)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return float(sorted_values[mid])
    return float((sorted_values[mid - 1] + sorted_values[mid]) / 2)


def _one(rows: list[dict], message: str) -> dict:
    if not rows:
        raise ValueError(message)
    return rows[0]
