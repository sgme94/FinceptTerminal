from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from poly_alpha_models import (
    PRIMARY_REASON_LATE_INFORMATION,
    PRIMARY_REASON_MISSING_MARKET_SNAPSHOT,
)
from poly_alpha_store import (
    list_documents,
    list_evidence_packs,
    list_market_snapshots,
    list_research_runs,
    list_shadow_signals,
    record_validation_result,
)


EXIT_TEMPLATES = ("fixed_horizon", "target_stop", "resolution_expiry")


def select_entry_snapshot(
    snapshots: list[dict[str, Any]],
    signal_created_at: str | dict[str, Any],
    freshness_sec: int,
) -> dict[str, Any] | None:
    if isinstance(signal_created_at, dict):
        signal_at_value = signal_created_at.get("created_at", "")
        market_key = _market_key(signal_created_at)
    else:
        signal_at_value = signal_created_at
        market_key = None
    signal_at = _parse_timestamp(signal_at_value)
    if signal_at is None:
        return None
    oldest_allowed = signal_at - timedelta(seconds=freshness_sec)
    candidates = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        if observed_at is None:
            continue
        if not oldest_allowed <= observed_at <= signal_at:
            continue
        if market_key is None or _market_key(snapshot) == market_key:
            candidates.append(snapshot)
    return _latest_snapshot(candidates)


def run_signal_validation(conn, shadow_signal_id, config, now):
    shadow_signal = _shadow_signal(conn, shadow_signal_id)
    snapshots = [
        snapshot
        for snapshot in list_market_snapshots(conn)
        if _market_key(snapshot) == _market_key(shadow_signal)
    ]
    freshness_sec = int(config.get("validation_freshness_window_sec", 300))
    entry_snapshot = select_entry_snapshot(snapshots, shadow_signal, freshness_sec)
    if entry_snapshot is None:
        validation_id = _record_result(
            conn,
            shadow_signal,
            now,
            validation_type="entry_snapshot",
            pass_fail="fail",
            failure_reason=PRIMARY_REASON_MISSING_MARKET_SNAPSHOT,
        )
        return {
            "validation_ids": [validation_id],
            "pass_fail": "fail",
            "failure_reason": PRIMARY_REASON_MISSING_MARKET_SNAPSHOT,
        }

    documents = _cited_documents(conn, shadow_signal)
    event_metrics = calculate_event_time_metrics(
        shadow_signal=shadow_signal,
        entry_snapshot=entry_snapshot,
        documents=documents,
        snapshots=snapshots,
    )
    failure_reason = event_metrics.get("failure_reason", "")
    pass_fail = "fail" if failure_reason else "pass"

    validation_ids = []
    for validation_type in EXIT_TEMPLATES:
        template_result = calculate_template_result(
            validation_type=validation_type,
            shadow_signal=shadow_signal,
            entry_snapshot=entry_snapshot,
            snapshots=snapshots,
            config=config,
            now=now,
        )
        validation_ids.append(
            _record_result(
                conn,
                shadow_signal,
                now,
                validation_type=validation_type,
                pass_fail=pass_fail,
                failure_reason=failure_reason,
                entry_snapshot=entry_snapshot,
                template_result=template_result,
                event_metrics=event_metrics,
            )
        )

    return {
        "validation_ids": validation_ids,
        "pass_fail": pass_fail,
        "failure_reason": failure_reason,
    }


def calculate_event_time_metrics(
    *,
    shadow_signal: dict[str, Any],
    entry_snapshot: dict[str, Any],
    documents: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    signal_at = _parse_timestamp(shadow_signal.get("created_at", ""))
    if signal_at is None:
        return _empty_event_metrics()
    latest_document = _latest_row(documents, "published_at")
    if latest_document is None:
        return _empty_event_metrics()

    info_at = _parse_timestamp(latest_document.get("published_at", ""))
    fetched_at = _parse_timestamp(latest_document.get("fetched_at", ""))
    if info_at is None:
        return _empty_event_metrics()

    before_info = _latest_snapshot_before(snapshots, info_at, strict=True)
    at_info = _latest_snapshot_before(snapshots, info_at, strict=False)
    after_signal = _earliest_snapshot_after(snapshots, signal_at)
    price_before_info = _price(before_info)
    price_at_info = _price(at_info)
    price_after_signal = _price(after_signal)
    market_move_before_signal = _delta(price_at_info, price_before_info)
    market_move_after_signal = _delta(price_after_signal, price_at_info)

    failure_reason = ""
    if abs(market_move_before_signal) > abs(market_move_after_signal):
        failure_reason = PRIMARY_REASON_LATE_INFORMATION

    return {
        "information_lag_sec": max(0, int((signal_at - info_at).total_seconds())),
        "fetch_lag_sec": (
            max(0, int((signal_at - fetched_at).total_seconds()))
            if fetched_at is not None
            else 0
        ),
        "market_move_before_signal": market_move_before_signal,
        "market_move_after_signal": market_move_after_signal,
        "failure_reason": failure_reason,
    }


def calculate_template_result(
    *,
    validation_type: str,
    shadow_signal: dict[str, Any],
    entry_snapshot: dict[str, Any],
    snapshots: list[dict[str, Any]],
    config: dict[str, Any],
    now: str,
) -> dict[str, Any]:
    signal_at = _parse_timestamp(shadow_signal.get("created_at", ""))
    entry_price = _price(entry_snapshot)
    exit_snapshot = _select_exit_snapshot(
        validation_type,
        signal_at,
        entry_price,
        snapshots,
        config,
        now,
    )
    exit_price = _price(exit_snapshot)
    if exit_price is None:
        exit_price = config.get("current_market_price", entry_price)

    estimated_probability = shadow_signal.get("estimated_probability")
    resolved_outcome = config.get("resolved_outcome")
    brier_score = None
    calibration_error = None
    edge_decay = None
    if resolved_outcome in (0, 1) and _is_probability(estimated_probability):
        brier_score = (resolved_outcome - estimated_probability) ** 2
        calibration_error = abs(resolved_outcome - estimated_probability)
        edge_decay = 0.0
    elif _is_number(exit_price) and _is_number(entry_price):
        edge_decay = abs(exit_price - entry_price)

    holding_period = ""
    if signal_at is not None and exit_snapshot is not None:
        exit_at = _parse_timestamp(exit_snapshot.get("observed_at", ""))
        if exit_at is not None:
            holding_period = f"{max(0, int((exit_at - signal_at).total_seconds()))}s"

    return {
        "entry_price": entry_price,
        "exit_snapshot_id": exit_snapshot.get("snapshot_id", "") if exit_snapshot else "",
        "exit_price": exit_price,
        "holding_period": holding_period,
        "gross_return": _gross_return(entry_price, exit_price, shadow_signal.get("side", "")),
        "cost_adjusted_return": _gross_return(
            entry_price,
            exit_price,
            shadow_signal.get("side", ""),
        ),
        "closing_line_value": _delta(exit_price, entry_price),
        "brier_score": brier_score,
        "calibration_error": calibration_error,
        "edge_decay": edge_decay,
        "max_adverse_excursion": _max_excursion(entry_price, snapshots, signal_at, favorable=False),
        "max_favorable_excursion": _max_excursion(entry_price, snapshots, signal_at, favorable=True),
    }


def _record_result(
    conn,
    shadow_signal: dict[str, Any],
    now: str,
    *,
    validation_type: str,
    pass_fail: str,
    failure_reason: str,
    entry_snapshot: dict[str, Any] | None = None,
    template_result: dict[str, Any] | None = None,
    event_metrics: dict[str, Any] | None = None,
) -> str:
    template_result = template_result or {}
    event_metrics = event_metrics or _empty_event_metrics()
    return record_validation_result(
        conn,
        opportunity_id=shadow_signal["opportunity_id"],
        shadow_signal_id=shadow_signal["shadow_signal_id"],
        strategy_version_id=shadow_signal["strategy_version_id"],
        entry_snapshot_id=entry_snapshot.get("snapshot_id", "") if entry_snapshot else "",
        exit_snapshot_id=template_result.get("exit_snapshot_id", ""),
        validation_type=validation_type,
        entry_price=template_result.get("entry_price"),
        exit_price=template_result.get("exit_price"),
        holding_period=template_result.get("holding_period", ""),
        gross_return=template_result.get("gross_return"),
        cost_adjusted_return=template_result.get("cost_adjusted_return"),
        closing_line_value=template_result.get("closing_line_value"),
        brier_score=template_result.get("brier_score"),
        calibration_error=template_result.get("calibration_error"),
        edge_decay=template_result.get("edge_decay"),
        information_lag_sec=event_metrics["information_lag_sec"],
        fetch_lag_sec=event_metrics["fetch_lag_sec"],
        market_move_before_signal=event_metrics["market_move_before_signal"],
        market_move_after_signal=event_metrics["market_move_after_signal"],
        max_adverse_excursion=template_result.get("max_adverse_excursion"),
        max_favorable_excursion=template_result.get("max_favorable_excursion"),
        liquidity_assumption="paper_top_of_book",
        slippage_assumption="none",
        pass_fail=pass_fail,
        failure_reason=failure_reason,
        created_at=now,
    )


def _select_exit_snapshot(
    validation_type: str,
    signal_at: datetime | None,
    entry_price: float | None,
    snapshots: list[dict[str, Any]],
    config: dict[str, Any],
    now: str,
) -> dict[str, Any] | None:
    if signal_at is None:
        return None
    future = [
        snapshot
        for snapshot in snapshots
        if (_parse_timestamp(snapshot.get("observed_at", "")) or datetime.min.replace(tzinfo=timezone.utc))
        >= signal_at
    ]
    if validation_type == "fixed_horizon":
        target_at = signal_at + timedelta(seconds=int(config.get("fixed_horizon_sec", 3600)))
        return _earliest_snapshot_at_or_after(future, target_at) or _latest_snapshot(future)
    if validation_type == "target_stop":
        target_return = config.get("target_return", 0.10)
        stop_return = config.get("stop_return", -0.05)
        for snapshot in sorted(future, key=_snapshot_time_key):
            gross_return = _gross_return(entry_price, _price(snapshot), "buy")
            if gross_return is None:
                continue
            if gross_return >= target_return or gross_return <= stop_return:
                return snapshot
        return _latest_snapshot(future)
    if validation_type == "resolution_expiry":
        resolution_at = _parse_timestamp(config.get("resolution_at", ""))
        if resolution_at is not None:
            return _earliest_snapshot_at_or_after(future, resolution_at) or _latest_snapshot(future)
        return _latest_snapshot(future)
    raise ValueError(f"Unsupported validation_type: {validation_type}")


def _cited_documents(conn, shadow_signal: dict[str, Any]) -> list[dict[str, Any]]:
    research_run = _research_run(conn, shadow_signal["run_id"])
    evidence_pack_id = research_run.get("evidence_pack_id", "")
    pack = None
    for row in list_evidence_packs(conn):
        if row["evidence_pack_id"] == evidence_pack_id:
            pack = row
            break
    if pack is None:
        return []
    documents_by_id = {row["document_id"]: row for row in list_documents(conn)}
    return [
        documents_by_id[document_id]
        for document_id in pack["document_ids"]
        if document_id in documents_by_id
    ]


def _shadow_signal(conn, shadow_signal_id: str) -> dict[str, Any]:
    for row in list_shadow_signals(conn):
        if row["shadow_signal_id"] == shadow_signal_id:
            return row
    raise ValueError(f"Unknown shadow_signal_id: {shadow_signal_id}")


def _research_run(conn, run_id: str) -> dict[str, Any]:
    for row in list_research_runs(conn):
        if row["run_id"] == run_id:
            return row
    raise ValueError(f"Unknown run_id: {run_id}")


def _latest_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    candidates = [row for row in rows if _parse_timestamp(row.get(key, "")) is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda row: _parse_timestamp(row.get(key, "")))


def _latest_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not snapshots:
        return None
    return max(snapshots, key=_snapshot_time_key)


def _latest_snapshot_before(
    snapshots: list[dict[str, Any]],
    at: datetime,
    *,
    strict: bool,
) -> dict[str, Any] | None:
    matches = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        if observed_at is None:
            continue
        if observed_at < at or (not strict and observed_at <= at):
            matches.append(snapshot)
    return _latest_snapshot(matches)


def _earliest_snapshot_after(
    snapshots: list[dict[str, Any]],
    at: datetime,
) -> dict[str, Any] | None:
    matches = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        if observed_at is not None and observed_at > at:
            matches.append(snapshot)
    return min(matches, key=_snapshot_time_key) if matches else None


def _earliest_snapshot_at_or_after(
    snapshots: list[dict[str, Any]],
    at: datetime,
) -> dict[str, Any] | None:
    matches = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        if observed_at is not None and observed_at >= at:
            matches.append(snapshot)
    return min(matches, key=_snapshot_time_key) if matches else None


def _snapshot_time_key(snapshot: dict[str, Any]) -> datetime:
    return _parse_timestamp(snapshot.get("observed_at", "")) or datetime.min.replace(
        tzinfo=timezone.utc
    )


def _price(snapshot: dict[str, Any] | None) -> float | None:
    if snapshot is None:
        return None
    if _is_probability(snapshot.get("mid_price")):
        return snapshot["mid_price"]
    best_bid = snapshot.get("best_bid")
    best_ask = snapshot.get("best_ask")
    if _is_probability(best_bid) and _is_probability(best_ask) and best_bid <= best_ask:
        return (best_bid + best_ask) / 2
    if _is_probability(snapshot.get("last_trade_price")):
        return snapshot["last_trade_price"]
    return None


def _gross_return(
    entry_price: float | None,
    exit_price: float | None,
    side: str,
) -> float | None:
    if not _is_number(entry_price) or not _is_number(exit_price) or entry_price == 0:
        return None
    move = exit_price - entry_price
    if side == "sell":
        move = -move
    return move / entry_price


def _max_excursion(
    entry_price: float | None,
    snapshots: list[dict[str, Any]],
    signal_at: datetime | None,
    *,
    favorable: bool,
) -> float | None:
    if not _is_number(entry_price) or signal_at is None:
        return None
    moves = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        price = _price(snapshot)
        if observed_at is None or observed_at < signal_at or not _is_number(price):
            continue
        moves.append(price - entry_price)
    if not moves:
        return 0.0
    return max(moves) if favorable else min(moves)


def _delta(left: float | None, right: float | None) -> float:
    if not _is_number(left) or not _is_number(right):
        return 0.0
    return left - right


def _empty_event_metrics() -> dict[str, Any]:
    return {
        "information_lag_sec": 0,
        "fetch_lag_sec": 0,
        "market_move_before_signal": 0.0,
        "market_move_after_signal": 0.0,
        "failure_reason": "",
    }


def _market_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        row.get("venue", ""),
        row.get("venue_market_id", ""),
        row.get("venue_contract_id", ""),
        row.get("outcome_id", ""),
    )


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _is_probability(value: Any) -> bool:
    return _is_number(value) and 0 <= value <= 1
