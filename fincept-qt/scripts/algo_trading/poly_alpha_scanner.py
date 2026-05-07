from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from poly_alpha_config import default_poly_alpha_config
from poly_alpha_store import (
    list_documents,
    list_event_market_links,
    list_events,
    list_evidence_packs,
    list_market_snapshots,
    list_opportunities,
    list_strategy_versions,
    record_document,
    record_evidence_pack,
    record_exploration_decision,
    record_market_snapshot,
    record_opportunity,
    record_scan_result,
    record_scan_run,
)


DEFAULT_MAX_SPREAD = 0.05
DEFAULT_MIN_LIQUIDITY = 500.0
DEFAULT_MIN_TOP_OF_BOOK_DEPTH = 100.0
DEFAULT_MIN_EDGE = 0.0


def run_deterministic_scan(
    conn,
    strategy_version_id,
    config,
    source_documents,
    market_snapshots,
    now,
):
    strategy = _strategy(conn, strategy_version_id)
    config_version_id = (
        config.get("config_version")
        or config.get("config_version_id")
        or strategy["config_version_id"]
    )
    scan_run_id = record_scan_run(
        conn,
        trigger_type="scheduled_scan",
        strategy_version_id=strategy_version_id,
        config_version_id=config_version_id,
        source_set_version=strategy["source_set_version"],
        status="completed",
        started_at=now,
        completed_at=now,
        created_at=now,
    )

    document_ids_by_market: dict[tuple[str, str, str, str], list[str]] = {}
    document_ids = []
    for source_document in source_documents:
        document_id = _record_document(conn, source_document, now)
        document_ids.append(document_id)
        key = _market_key(source_document)
        document_ids_by_market.setdefault(key, []).append(document_id)

    snapshot_ids = []
    opportunity_ids = []
    scan_result_ids = []
    for snapshot in market_snapshots:
        snapshot_id = _record_snapshot(conn, snapshot, now)
        snapshot_ids.append(snapshot_id)
        document_ids_for_market = document_ids_by_market.get(_market_key(snapshot), [])
        decision, reason, opportunity_id = _scan_decision(
            conn,
            strategy,
            snapshot,
            config,
            now,
        )
        if opportunity_id:
            opportunity_ids.append(opportunity_id)
        scan_result_ids.append(
            record_scan_result(
                conn,
                scan_run_id=scan_run_id,
                strategy_version_id=strategy_version_id,
                venue=snapshot.get("venue", ""),
                venue_market_id=snapshot.get("venue_market_id", ""),
                venue_contract_id=snapshot.get("venue_contract_id", ""),
                outcome_id=snapshot.get("outcome_id", ""),
                decision=decision,
                reason=reason,
                source_snapshot_ids=[snapshot_id],
                source_document_ids=document_ids_for_market,
                created_opportunity_id=opportunity_id,
                observed_at=snapshot.get("observed_at", now),
                created_at=now,
            )
        )

    return {
        "scan_run_id": scan_run_id,
        "document_ids": document_ids,
        "snapshot_ids": snapshot_ids,
        "scan_result_ids": scan_result_ids,
        "opportunity_ids": opportunity_ids,
    }


def build_evidence_pack(
    conn,
    opportunity_id,
    document_ids,
    snapshot_ids,
    event_ids,
    now,
):
    opportunity = _opportunity(conn, opportunity_id)
    strategy = _strategy(conn, opportunity["strategy_version_id"])
    documents = _rows_by_ids(list_documents(conn), "document_id", document_ids)
    snapshots = _rows_by_ids(list_market_snapshots(conn), "snapshot_id", snapshot_ids)
    events = _rows_by_ids(list_events(conn), "event_id", event_ids)

    payload = {
        "opportunity_id": opportunity_id,
        "strategy_version_id": opportunity["strategy_version_id"],
        "document_ids": list(document_ids),
        "snapshot_ids": list(snapshot_ids),
        "event_ids": list(event_ids),
        "latest_published_at": _latest(documents, "published_at"),
        "latest_fetched_at": _latest(
            [*documents, *snapshots],
            "fetched_at",
        ),
        "latest_observed_at": max(
            [
                value
                for value in [
                    _latest(documents, "observed_at"),
                    _latest(snapshots, "observed_at"),
                    _latest(events, "event_time"),
                ]
                if value
            ],
            default="",
        ),
    }
    payload_hash = _stable_hash(payload)
    for pack in list_evidence_packs(conn):
        if pack["payload_hash"] == payload_hash:
            return pack["evidence_pack_id"]

    return record_evidence_pack(
        conn,
        opportunity_id=opportunity_id,
        strategy_version_id=opportunity["strategy_version_id"],
        document_ids=list(document_ids),
        snapshot_ids=list(snapshot_ids),
        event_ids=list(event_ids),
        source_set_version=strategy["source_set_version"],
        latest_published_at=payload["latest_published_at"],
        latest_fetched_at=payload["latest_fetched_at"],
        latest_observed_at=payload["latest_observed_at"],
        created_at=now,
        payload_hash=payload_hash,
        write_audit=True,
    )


def decide_exploration(
    conn,
    opportunity_id,
    evidence_pack_id,
    config,
    now,
):
    opportunity = _opportunity(conn, opportunity_id)
    evidence_pack = _evidence_pack(conn, evidence_pack_id)
    documents = _rows_by_ids(
        list_documents(conn),
        "document_id",
        evidence_pack["document_ids"],
    )
    snapshots = _rows_by_ids(
        list_market_snapshots(conn),
        "snapshot_id",
        evidence_pack["snapshot_ids"],
    )
    events = _rows_by_ids(list_events(conn), "event_id", evidence_pack["event_ids"])

    merged_config = default_poly_alpha_config(config)
    historical_sample_count = int(merged_config.get("historical_sample_count", 0))
    min_exploration_samples = int(merged_config["min_exploration_samples"])
    snapshot_freshness_sec = int(
        merged_config.get(
            "exploration_snapshot_freshness_sec",
            merged_config["validation_freshness_window_sec"],
        )
    )
    current_snapshots = _current_snapshots(snapshots, now, snapshot_freshness_sec)
    current_snapshot = _latest_snapshot(current_snapshots)
    evidence_completeness = _evidence_completeness(documents, snapshots, events)
    current_market_metrics = _current_market_metrics(current_snapshot)
    metrics = {
        "historical_sample_count": historical_sample_count,
        "min_exploration_samples": min_exploration_samples,
        "event_market_link_confidence_recorded": _has_link_confidence(
            conn,
            opportunity,
            evidence_pack["event_ids"],
        ),
        "snapshot_freshness_sec": snapshot_freshness_sec,
        "current_snapshot_count": len(current_snapshots),
        "current_market_metrics": current_market_metrics,
        "evidence_completeness": evidence_completeness,
        "evidence_completeness_metrics_recorded": True,
        "agent_findings_required": False,
    }

    decision, reason = _exploration_decision(metrics)
    return record_exploration_decision(
        conn,
        opportunity_id=opportunity_id,
        evidence_pack_id=evidence_pack_id,
        strategy_version_id=opportunity["strategy_version_id"],
        decision=decision,
        reason=reason,
        metrics=metrics,
        created_at=now,
        expected_status="watch",
        write_audit=True,
    )


def _strategy(conn, strategy_version_id: str) -> dict[str, Any]:
    for row in list_strategy_versions(conn):
        if row["strategy_version_id"] == strategy_version_id:
            return row
    raise ValueError(f"Unknown strategy_version_id: {strategy_version_id}")


def _opportunity(conn, opportunity_id: str) -> dict[str, Any]:
    for row in list_opportunities(conn):
        if row["opportunity_id"] == opportunity_id:
            return row
    raise ValueError(f"Unknown opportunity_id: {opportunity_id}")


def _evidence_pack(conn, evidence_pack_id: str) -> dict[str, Any]:
    for row in list_evidence_packs(conn):
        if row["evidence_pack_id"] == evidence_pack_id:
            return row
    raise ValueError(f"Unknown evidence_pack_id: {evidence_pack_id}")


def _rows_by_ids(
    rows: list[dict[str, Any]],
    id_key: str,
    requested_ids: list[str],
) -> list[dict[str, Any]]:
    by_id = {row[id_key]: row for row in rows}
    missing_ids = [requested_id for requested_id in requested_ids if requested_id not in by_id]
    if missing_ids:
        raise ValueError(f"Unknown {id_key}: {missing_ids[0]}")
    return [by_id[requested_id] for requested_id in requested_ids]


def _record_document(conn, source_document: dict[str, Any], now: str) -> str:
    payload_hash = source_document.get("payload_hash") or _stable_hash(source_document)
    return record_document(
        conn,
        source_type=source_document.get("source_type", ""),
        source_name=source_document.get("source_name", ""),
        url=source_document.get("url", ""),
        api_endpoint=source_document.get("api_endpoint", ""),
        market_id=source_document.get("market_id", ""),
        venue=source_document.get("venue", ""),
        venue_market_id=source_document.get("venue_market_id", ""),
        venue_contract_id=source_document.get("venue_contract_id", ""),
        outcome_id=source_document.get("outcome_id", ""),
        asset_symbol=source_document.get("asset_symbol", ""),
        topic=source_document.get("topic", ""),
        published_at=source_document.get("published_at", ""),
        fetched_at=source_document.get("fetched_at", ""),
        observed_at=source_document.get("observed_at", ""),
        payload_hash=payload_hash,
        title=source_document.get("title", ""),
        normalized_text=source_document.get("normalized_text", ""),
        raw_payload=source_document.get("raw_payload", {}),
        trust_level=source_document.get("trust_level", ""),
        created_at=now,
        document_id=source_document.get("document_id"),
        write_audit=True,
    )


def _record_snapshot(conn, snapshot: dict[str, Any], now: str) -> str:
    payload_hash = snapshot.get("payload_hash") or _stable_hash(snapshot)
    return record_market_snapshot(
        conn,
        venue=snapshot.get("venue", ""),
        venue_market_id=snapshot.get("venue_market_id", ""),
        venue_contract_id=snapshot.get("venue_contract_id", ""),
        outcome_id=snapshot.get("outcome_id", ""),
        adapter_metadata=snapshot.get("adapter_metadata", {}),
        source_api=snapshot.get("source_api", ""),
        observed_at=snapshot.get("observed_at", now),
        fetched_at=snapshot.get("fetched_at", now),
        payload_hash=payload_hash,
        best_bid=snapshot.get("best_bid"),
        best_ask=snapshot.get("best_ask"),
        spread=snapshot.get("spread"),
        top_bid_depth=snapshot.get("top_bid_depth"),
        top_ask_depth=snapshot.get("top_ask_depth"),
        mid_price=snapshot.get("mid_price"),
        last_trade_price=snapshot.get("last_trade_price"),
        liquidity=snapshot.get("liquidity"),
        volume=snapshot.get("volume"),
        raw_payload=snapshot.get("raw_payload", {}),
        created_at=now,
        snapshot_id=snapshot.get("snapshot_id"),
    )


def _scan_decision(
    conn,
    strategy: dict[str, Any],
    snapshot: dict[str, Any],
    config: dict[str, Any],
    now: str,
) -> tuple[str, str, str]:
    spread = snapshot.get("spread")
    if spread is None or spread > config.get("max_spread", DEFAULT_MAX_SPREAD):
        return "ignore", "wide_spread", ""

    min_liquidity = config.get("min_liquidity", DEFAULT_MIN_LIQUIDITY)
    min_depth = config.get("min_top_of_book_depth", DEFAULT_MIN_TOP_OF_BOOK_DEPTH)
    if (
        snapshot.get("liquidity") is None
        or snapshot.get("liquidity") < min_liquidity
        or snapshot.get("top_bid_depth") is None
        or snapshot.get("top_bid_depth") < min_depth
        or snapshot.get("top_ask_depth") is None
        or snapshot.get("top_ask_depth") < min_depth
    ):
        return "ignore", "low_liquidity", ""

    market_probability = _market_probability(snapshot)
    estimated_probability = snapshot.get("estimated_probability")
    edge = _edge(estimated_probability, market_probability)
    qualifies = bool(snapshot.get("qualifies")) or (
        edge is not None and edge > config.get("min_edge", DEFAULT_MIN_EDGE)
    )
    if not qualifies:
        return "watch", "insufficient_edge", ""

    opportunity_id = record_opportunity(
        conn,
        strategy_version_id=strategy["strategy_version_id"],
        venue=snapshot.get("venue", ""),
        venue_market_id=snapshot.get("venue_market_id", ""),
        venue_contract_id=snapshot.get("venue_contract_id", ""),
        outcome_id=snapshot.get("outcome_id", ""),
        title=snapshot.get("title", snapshot.get("venue_market_id", "")),
        alpha_family=snapshot.get("alpha_family", strategy["strategy_family"]),
        status="watch",
        primary_reason="",
        market_probability=market_probability,
        estimated_probability=estimated_probability,
        edge=edge,
        confidence=snapshot.get("confidence", 0.0),
        created_at=now,
        updated_at=now,
        opportunity_id=snapshot.get("opportunity_id"),
        write_audit=True,
    )
    return "create_opportunity", "edge_detected", opportunity_id


def _market_probability(snapshot: dict[str, Any]) -> float | None:
    if snapshot.get("market_probability") is not None:
        return snapshot["market_probability"]
    if snapshot.get("mid_price") is not None:
        return snapshot["mid_price"]
    best_bid = snapshot.get("best_bid")
    best_ask = snapshot.get("best_ask")
    if best_bid is not None and best_ask is not None:
        return (best_bid + best_ask) / 2
    return snapshot.get("last_trade_price")


def _edge(
    estimated_probability: float | None,
    market_probability: float | None,
) -> float | None:
    if estimated_probability is None or market_probability is None:
        return None
    return estimated_probability - market_probability


def _market_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        row.get("venue", ""),
        row.get("venue_market_id", ""),
        row.get("venue_contract_id", ""),
        row.get("outcome_id", ""),
    )


def _latest(rows: list[dict[str, Any]], key: str) -> str:
    return max([row[key] for row in rows if row.get(key)], default="")


def _latest_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not snapshots:
        return None
    return max(snapshots, key=lambda snapshot: snapshot.get("observed_at") or "")


def _current_snapshots(
    snapshots: list[dict[str, Any]],
    now: str,
    freshness_sec: int,
) -> list[dict[str, Any]]:
    now_dt = _parse_timestamp(now)
    if now_dt is None:
        return []
    oldest_allowed = now_dt - timedelta(seconds=freshness_sec)
    current = []
    for snapshot in snapshots:
        observed_at = _parse_timestamp(snapshot.get("observed_at", ""))
        if observed_at is None:
            continue
        if oldest_allowed <= observed_at <= now_dt:
            current.append(snapshot)
    return current


def _evidence_completeness(
    documents: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "document_count": len(documents),
        "snapshot_count": len(snapshots),
        "event_count": len(events),
        "source_metadata_complete": bool(documents)
        and all(_has_source_metadata(document) for document in documents)
        and all(_has_snapshot_source_metadata(snapshot) for snapshot in snapshots),
        "fetched_timestamps_complete": bool(documents)
        and all(document.get("fetched_at") for document in documents)
        and all(snapshot.get("fetched_at") for snapshot in snapshots),
        "payload_hashes_complete": bool(documents)
        and all(document.get("payload_hash") for document in documents)
        and all(snapshot.get("payload_hash") for snapshot in snapshots),
    }


def _has_source_metadata(document: dict[str, Any]) -> bool:
    return bool(
        document.get("source_type")
        and document.get("source_name")
        and (document.get("url") or document.get("api_endpoint"))
        and document.get("trust_level")
    )


def _has_snapshot_source_metadata(snapshot: dict[str, Any]) -> bool:
    return bool(snapshot.get("source_api"))


def _has_link_confidence(
    conn,
    opportunity: dict[str, Any],
    event_ids: list[str],
) -> bool:
    for event_id in event_ids:
        for link in list_event_market_links(conn, event_id=event_id):
            if (
                link["venue"] == opportunity["venue"]
                and link["venue_market_id"] == opportunity["venue_market_id"]
                and link["venue_contract_id"] == opportunity["venue_contract_id"]
                and link["outcome_id"] == opportunity["outcome_id"]
                and link["link_confidence"] is not None
            ):
                return True
    return False


def _current_market_metrics(
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    if snapshot is None:
        return {
            "market_probability": None,
            "spread": None,
            "top_bid_depth": None,
            "top_ask_depth": None,
            "liquidity": None,
        }
    return {
        "market_probability": _market_probability(snapshot),
        "spread": snapshot["spread"],
        "top_bid_depth": snapshot["top_bid_depth"],
        "top_ask_depth": snapshot["top_ask_depth"],
        "liquidity": snapshot["liquidity"],
    }


def _exploration_decision(metrics: dict[str, Any]) -> tuple[str, str]:
    if metrics["historical_sample_count"] < metrics["min_exploration_samples"]:
        return "watch", "insufficient_exploration_samples"
    completeness = metrics["evidence_completeness"]
    if not completeness["source_metadata_complete"]:
        return "reject", "incomplete_source_metadata"
    if not completeness["fetched_timestamps_complete"]:
        return "reject", "missing_fetched_timestamps"
    if not completeness["payload_hashes_complete"]:
        return "reject", "missing_payload_hashes"
    if metrics["current_snapshot_count"] < 1:
        return "reject", "missing_current_snapshot"
    if not metrics["event_market_link_confidence_recorded"]:
        return "reject", "missing_link_confidence"
    if any(value is None for value in metrics["current_market_metrics"].values()):
        return "reject", "missing_market_metrics"
    if not metrics["evidence_completeness_metrics_recorded"]:
        return "reject", "missing_evidence_completeness_metrics"
    return "pass", "gate_passed"


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
