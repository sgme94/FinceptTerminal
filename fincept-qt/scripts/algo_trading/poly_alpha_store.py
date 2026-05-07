from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from poly_alpha_models import (
    OPPORTUNITY_STATUSES,
    PROMOTION_DECISIONS,
    SHADOW_SIGNAL_STATUSES,
    apply_opportunity_transition,
)


_EXPLORATION_STATUS_BY_DECISION = {
    "pass": "watch",
    "watch": "watch",
    "reject": "rejected",
}

_LIFECYCLE_AUDIT_ACTIONS = {
    "config_version_created": "config_version_created",
    "strategy_version_created": "strategy_version_created",
    "opportunity_discovered": "opportunity_discovered",
    "document_ingested": "document_ingested",
    "evidence_pack_created": "evidence_pack_created",
    "event_linked": "event_linked",
    "research_started": "research_started",
    "research_completed": "research_completed",
    "exploration_pass": "exploration_passed",
    "exploration_watch": "exploration_watch",
    "exploration_reject": "exploration_rejected",
    "shadow_signal_created": "shadow_signal_created",
    "validation_pass": "validation_completed",
    "validation_fail": "validation_completed",
    "promotion_promote": "promotion_approved",
    "promotion_reject": "promotion_rejected",
    "promotion_watch": "promotion_watch",
    "proposal_created": "proposal_created",
    "proposal_approved": "proposal_approved",
    "proposal_rejected": "proposal_rejected",
    "paper_fill_recorded": "paper_fill_recorded",
    "paper_fill_skipped": "paper_fill_skipped",
    "signal_ttl_expired": "expired",
    "proposal_ttl_expired": "expired",
    "opportunity_ttl_expired": "expired",
}


def ensure_poly_alpha_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_config_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_version_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            validation_freshness_window_sec INTEGER NOT NULL,
            min_exploration_samples INTEGER NOT NULL,
            min_promotion_samples INTEGER NOT NULL,
            min_promotion_history_days INTEGER NOT NULL,
            max_drawdown_threshold REAL NOT NULL,
            min_hit_rate REAL NOT NULL,
            min_payoff_ratio REAL NOT NULL,
            min_capacity_multiple REAL NOT NULL,
            promotion_defaults_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_source_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_set_version TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            enabled_sources_json TEXT DEFAULT '[]',
            trust_policy_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_strategy_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_version_id TEXT NOT NULL UNIQUE,
            strategy_family TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            version TEXT NOT NULL,
            config_version_id TEXT NOT NULL,
            prompt_version TEXT DEFAULT '',
            source_set_version TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            url TEXT DEFAULT '',
            api_endpoint TEXT DEFAULT '',
            market_id TEXT DEFAULT '',
            venue TEXT DEFAULT '',
            venue_market_id TEXT DEFAULT '',
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            asset_symbol TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            published_at TEXT DEFAULT '',
            fetched_at TEXT DEFAULT '',
            observed_at TEXT DEFAULT '',
            payload_hash TEXT NOT NULL UNIQUE,
            title TEXT DEFAULT '',
            normalized_text TEXT DEFAULT '',
            raw_payload_json TEXT DEFAULT '{}',
            trust_level TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            primary_assets_json TEXT DEFAULT '[]',
            event_time TEXT DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_event_market_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT NOT NULL UNIQUE,
            event_id TEXT NOT NULL,
            venue TEXT NOT NULL,
            venue_market_id TEXT NOT NULL,
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            adapter_metadata_json TEXT DEFAULT '{}',
            outcome TEXT DEFAULT '',
            link_reason TEXT DEFAULT '',
            link_confidence REAL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_research_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            trigger_type TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            evidence_pack_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            event_id TEXT DEFAULT '',
            venue TEXT DEFAULT '',
            venue_market_id TEXT DEFAULT '',
            requested_by TEXT DEFAULT '',
            started_at TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            status TEXT NOT NULL,
            model_config_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_run_id TEXT NOT NULL UNIQUE,
            trigger_type TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            config_version_id TEXT NOT NULL,
            source_set_version TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            scanned_count INTEGER NOT NULL DEFAULT 0,
            ignored_count INTEGER NOT NULL DEFAULT 0,
            watch_count INTEGER NOT NULL DEFAULT 0,
            created_opportunity_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_result_id TEXT NOT NULL UNIQUE,
            scan_run_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            venue TEXT NOT NULL,
            venue_market_id TEXT NOT NULL,
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            source_snapshot_ids_json TEXT DEFAULT '[]',
            source_document_ids_json TEXT DEFAULT '[]',
            created_opportunity_id TEXT DEFAULT '',
            observed_at TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT NOT NULL UNIQUE,
            strategy_version_id TEXT NOT NULL,
            venue TEXT NOT NULL,
            venue_market_id TEXT NOT NULL,
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            alpha_family TEXT NOT NULL,
            status TEXT NOT NULL,
            primary_reason TEXT DEFAULT '',
            market_probability REAL,
            estimated_probability REAL,
            edge REAL,
            confidence REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_evidence_packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_pack_id TEXT NOT NULL UNIQUE,
            opportunity_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            document_ids_json TEXT DEFAULT '[]',
            snapshot_ids_json TEXT DEFAULT '[]',
            event_ids_json TEXT DEFAULT '[]',
            source_set_version TEXT NOT NULL,
            latest_published_at TEXT DEFAULT '',
            latest_fetched_at TEXT DEFAULT '',
            latest_observed_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            payload_hash TEXT NOT NULL UNIQUE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_exploration_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exploration_id TEXT NOT NULL UNIQUE,
            opportunity_id TEXT NOT NULL,
            evidence_pack_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            metrics_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL UNIQUE,
            venue TEXT NOT NULL,
            venue_market_id TEXT NOT NULL,
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            adapter_metadata_json TEXT DEFAULT '{}',
            source_api TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            best_bid REAL,
            best_ask REAL,
            spread REAL,
            top_bid_depth REAL,
            top_ask_depth REAL,
            mid_price REAL,
            last_trade_price REAL,
            liquidity REAL,
            volume REAL,
            raw_payload_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_agent_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finding_id TEXT NOT NULL UNIQUE,
            run_id TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            evidence_pack_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            agent_role TEXT NOT NULL,
            estimated_probability REAL,
            market_probability REAL,
            edge REAL,
            confidence REAL,
            recommendation TEXT NOT NULL,
            thesis TEXT DEFAULT '',
            evidence_ids_json TEXT DEFAULT '[]',
            counter_evidence_ids_json TEXT DEFAULT '[]',
            resolution_risks_json TEXT DEFAULT '[]',
            blockers_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_shadow_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shadow_signal_id TEXT NOT NULL UNIQUE,
            opportunity_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            strategy_family TEXT NOT NULL,
            venue TEXT NOT NULL,
            venue_market_id TEXT NOT NULL,
            venue_contract_id TEXT DEFAULT '',
            outcome_id TEXT DEFAULT '',
            adapter_metadata_json TEXT DEFAULT '{}',
            side TEXT NOT NULL,
            observed_price REAL,
            estimated_probability REAL,
            edge REAL,
            confidence REAL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            validation_id TEXT NOT NULL UNIQUE,
            opportunity_id TEXT NOT NULL,
            shadow_signal_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            entry_snapshot_id TEXT DEFAULT '',
            exit_snapshot_id TEXT DEFAULT '',
            validation_type TEXT NOT NULL,
            entry_price REAL,
            exit_price REAL,
            holding_period TEXT DEFAULT '',
            gross_return REAL,
            cost_adjusted_return REAL,
            closing_line_value REAL,
            brier_score REAL,
            calibration_error REAL,
            edge_decay REAL,
            information_lag_sec INTEGER,
            fetch_lag_sec INTEGER,
            market_move_before_signal REAL,
            market_move_after_signal REAL,
            max_adverse_excursion REAL,
            max_favorable_excursion REAL,
            liquidity_assumption TEXT DEFAULT '',
            slippage_assumption TEXT DEFAULT '',
            pass_fail TEXT NOT NULL,
            failure_reason TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_promotion_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promotion_id TEXT NOT NULL UNIQUE,
            opportunity_id TEXT NOT NULL,
            shadow_signal_id TEXT NOT NULL,
            strategy_version_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            prediction_metrics_json TEXT DEFAULT '{}',
            trading_metrics_json TEXT DEFAULT '{}',
            metrics_json TEXT DEFAULT '{}',
            critic_blockers_json TEXT DEFAULT '[]',
            risk_checks_json TEXT DEFAULT '{}',
            proposal_id TEXT DEFAULT '',
            decided_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poly_alpha_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT NOT NULL UNIQUE,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT DEFAULT '',
            opportunity_id TEXT DEFAULT '',
            strategy_version_id TEXT DEFAULT '',
            actor_type TEXT NOT NULL,
            actor_id TEXT DEFAULT '',
            before_json TEXT DEFAULT '{}',
            after_json TEXT DEFAULT '{}',
            result TEXT NOT NULL,
            reason TEXT DEFAULT '',
            request_id TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )


def record_config_version(
    conn: sqlite3.Connection,
    *,
    name: str,
    validation_freshness_window_sec: int,
    min_exploration_samples: int,
    min_promotion_samples: int,
    min_promotion_history_days: int,
    max_drawdown_threshold: float,
    min_hit_rate: float,
    min_payoff_ratio: float,
    min_capacity_multiple: float,
    promotion_defaults: dict,
    created_at: str,
    config_version_id: str | None = None,
    is_active: bool = True,
    write_audit: bool = False,
) -> str:
    config_version_id = config_version_id or _new_id("cfg")
    conn.execute(
        """
        INSERT INTO poly_alpha_config_versions
            (config_version_id, name, validation_freshness_window_sec,
             min_exploration_samples, min_promotion_samples, min_promotion_history_days,
             max_drawdown_threshold, min_hit_rate, min_payoff_ratio,
             min_capacity_multiple, promotion_defaults_json, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            config_version_id,
            name,
            validation_freshness_window_sec,
            min_exploration_samples,
            min_promotion_samples,
            min_promotion_history_days,
            max_drawdown_threshold,
            min_hit_rate,
            min_payoff_ratio,
            min_capacity_multiple,
            _json_dumps(promotion_defaults),
            created_at,
            int(is_active),
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="config_version_created",
            entity_type="config_version",
            entity_id=config_version_id,
            strategy_version_id="",
            opportunity_id="",
            after={"config_version_id": config_version_id, "name": name},
            created_at=created_at,
        )
    return config_version_id


def record_source_set(
    conn: sqlite3.Connection,
    *,
    source_set_version: str,
    name: str,
    enabled_sources: list,
    trust_policy: dict,
    created_at: str,
    is_active: bool = True,
) -> str:
    conn.execute(
        """
        INSERT INTO poly_alpha_source_sets
            (source_set_version, name, enabled_sources_json, trust_policy_json,
             created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source_set_version,
            name,
            _json_dumps(enabled_sources),
            _json_dumps(trust_policy),
            created_at,
            int(is_active),
        ),
    )
    return source_set_version


def record_strategy_version(
    conn: sqlite3.Connection,
    *,
    strategy_version_id: str,
    strategy_family: str,
    strategy_name: str,
    version: str,
    config_version_id: str,
    prompt_version: str,
    source_set_version: str,
    description: str,
    created_at: str,
    is_active: bool = True,
    write_audit: bool = False,
) -> str:
    conn.execute(
        """
        INSERT INTO poly_alpha_strategy_versions
            (strategy_version_id, strategy_family, strategy_name, version,
             config_version_id, prompt_version, source_set_version, description,
             created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            strategy_version_id,
            strategy_family,
            strategy_name,
            version,
            config_version_id,
            prompt_version,
            source_set_version,
            description,
            created_at,
            int(is_active),
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="strategy_version_created",
            entity_type="strategy_version",
            entity_id=strategy_version_id,
            strategy_version_id=strategy_version_id,
            opportunity_id="",
            after={"strategy_version_id": strategy_version_id},
            created_at=created_at,
        )
    return strategy_version_id


def record_document(
    conn: sqlite3.Connection,
    *,
    source_type: str,
    source_name: str,
    url: str,
    api_endpoint: str,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    asset_symbol: str,
    topic: str,
    published_at: str,
    fetched_at: str,
    observed_at: str,
    payload_hash: str,
    title: str,
    normalized_text: str,
    raw_payload: dict,
    trust_level: str,
    created_at: str,
    document_id: str | None = None,
    market_id: str = "",
    write_audit: bool = False,
) -> str:
    existing = conn.execute(
        "SELECT document_id FROM poly_alpha_documents WHERE payload_hash = ?",
        (payload_hash,),
    ).fetchone()
    if existing is not None:
        return existing[0]

    document_id = document_id or _new_id("doc")
    conn.execute(
        """
        INSERT INTO poly_alpha_documents
            (document_id, source_type, source_name, url, api_endpoint, market_id,
             venue, venue_market_id, venue_contract_id, outcome_id, asset_symbol,
             topic, published_at, fetched_at, observed_at, payload_hash, title,
             normalized_text, raw_payload_json, trust_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            source_type,
            source_name,
            url,
            api_endpoint,
            market_id,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            asset_symbol,
            topic,
            published_at,
            fetched_at,
            observed_at,
            payload_hash,
            title,
            normalized_text,
            _json_dumps(raw_payload),
            trust_level,
            created_at,
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="document_ingested",
            entity_type="document",
            entity_id=document_id,
            strategy_version_id="",
            opportunity_id="",
            after={"document_id": document_id, "payload_hash": payload_hash},
            created_at=created_at,
        )
    return document_id


def record_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    title: str,
    summary: str,
    primary_assets: list,
    event_time: str,
    status: str,
    created_at: str,
    updated_at: str,
    event_id: str | None = None,
) -> str:
    event_id = event_id or _new_id("event")
    conn.execute(
        """
        INSERT INTO poly_alpha_events
            (event_id, event_type, title, summary, primary_assets_json, event_time,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            event_type,
            title,
            summary,
            _json_dumps(primary_assets),
            event_time,
            status,
            created_at,
            updated_at,
        ),
    )
    return event_id


def record_event_market_link(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    adapter_metadata: dict,
    outcome: str,
    link_reason: str,
    link_confidence: float,
    created_at: str,
    link_id: str | None = None,
    write_audit: bool = False,
) -> str:
    link_id = link_id or _new_id("link")
    conn.execute(
        """
        INSERT INTO poly_alpha_event_market_links
            (link_id, event_id, venue, venue_market_id, venue_contract_id,
             outcome_id, adapter_metadata_json, outcome, link_reason,
             link_confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            link_id,
            event_id,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            _json_dumps(adapter_metadata),
            outcome,
            link_reason,
            link_confidence,
            created_at,
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="event_linked",
            entity_type="event_market_link",
            entity_id=link_id,
            strategy_version_id="",
            opportunity_id="",
            after={"event_id": event_id, "venue_market_id": venue_market_id},
            created_at=created_at,
        )
    return link_id


def record_research_run(
    conn: sqlite3.Connection,
    *,
    trigger_type: str,
    opportunity_id: str,
    evidence_pack_id: str,
    strategy_version_id: str,
    event_id: str,
    venue: str,
    venue_market_id: str,
    requested_by: str,
    started_at: str,
    status: str,
    model_config: dict,
    created_at: str,
    completed_at: str = "",
    run_id: str | None = None,
    write_audit: bool = False,
) -> str:
    run_id = run_id or _new_id("run")
    conn.execute(
        """
        INSERT INTO poly_alpha_research_runs
            (run_id, trigger_type, opportunity_id, evidence_pack_id,
             strategy_version_id, event_id, venue, venue_market_id, requested_by,
             started_at, completed_at, status, model_config_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            trigger_type,
            opportunity_id,
            evidence_pack_id,
            strategy_version_id,
            event_id,
            venue,
            venue_market_id,
            requested_by,
            started_at,
            completed_at,
            status,
            _json_dumps(model_config),
            created_at,
        ),
    )
    if write_audit:
        action = "research_completed" if status == "completed" else "research_started"
        _record_audit_event(
            conn,
            action=action,
            entity_type="research_run",
            entity_id=run_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={"status": status, "evidence_pack_id": evidence_pack_id},
            created_at=created_at,
        )
    return run_id


def record_scan_run(
    conn: sqlite3.Connection,
    *,
    trigger_type: str,
    strategy_version_id: str,
    config_version_id: str,
    source_set_version: str,
    status: str,
    started_at: str,
    created_at: str,
    completed_at: str = "",
    scanned_count: int = 0,
    ignored_count: int = 0,
    watch_count: int = 0,
    created_opportunity_count: int = 0,
    error_message: str = "",
    scan_run_id: str | None = None,
) -> str:
    scan_run_id = scan_run_id or _new_id("scan")
    conn.execute(
        """
        INSERT INTO poly_alpha_scan_runs
            (scan_run_id, trigger_type, strategy_version_id, config_version_id,
             source_set_version, status, started_at, completed_at, scanned_count,
             ignored_count, watch_count, created_opportunity_count, error_message,
             created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan_run_id,
            trigger_type,
            strategy_version_id,
            config_version_id,
            source_set_version,
            status,
            started_at,
            completed_at,
            scanned_count,
            ignored_count,
            watch_count,
            created_opportunity_count,
            error_message,
            created_at,
        ),
    )
    return scan_run_id


def record_scan_result(
    conn: sqlite3.Connection,
    *,
    scan_run_id: str,
    strategy_version_id: str,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    decision: str,
    reason: str,
    source_snapshot_ids: list,
    source_document_ids: list,
    observed_at: str,
    created_at: str,
    created_opportunity_id: str = "",
    scan_result_id: str | None = None,
) -> str:
    scan_result_id = scan_result_id or _new_id("scan-result")
    conn.execute(
        """
        INSERT INTO poly_alpha_scan_results
            (scan_result_id, scan_run_id, strategy_version_id, venue,
             venue_market_id, venue_contract_id, outcome_id, decision, reason,
             source_snapshot_ids_json, source_document_ids_json,
             created_opportunity_id, observed_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan_result_id,
            scan_run_id,
            strategy_version_id,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            decision,
            reason,
            _json_dumps(source_snapshot_ids),
            _json_dumps(source_document_ids),
            created_opportunity_id,
            observed_at,
            created_at,
        ),
    )
    conn.execute(
        """
        UPDATE poly_alpha_scan_runs
        SET scanned_count = scanned_count + 1,
            ignored_count = ignored_count + ?,
            watch_count = watch_count + ?,
            created_opportunity_count = created_opportunity_count + ?
        WHERE scan_run_id = ?
        """,
        (
            1 if decision == "ignore" else 0,
            1 if decision == "watch" else 0,
            1 if decision == "create_opportunity" else 0,
            scan_run_id,
        ),
    )
    return scan_result_id


def record_opportunity(
    conn: sqlite3.Connection,
    *,
    strategy_version_id: str,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    title: str,
    alpha_family: str,
    status: str,
    primary_reason: str,
    market_probability: float,
    estimated_probability: float,
    edge: float,
    confidence: float,
    created_at: str,
    updated_at: str,
    opportunity_id: str | None = None,
    write_audit: bool = False,
) -> str:
    _require_opportunity_status(status)
    opportunity_id = opportunity_id or _new_id("opp")
    conn.execute(
        """
        INSERT INTO poly_alpha_opportunities
            (opportunity_id, strategy_version_id, venue, venue_market_id,
             venue_contract_id, outcome_id, title, alpha_family, status,
             primary_reason, market_probability, estimated_probability, edge,
             confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            strategy_version_id,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            title,
            alpha_family,
            status,
            primary_reason,
            market_probability,
            estimated_probability,
            edge,
            confidence,
            created_at,
            updated_at,
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="opportunity_discovered",
            entity_type="opportunity",
            entity_id=opportunity_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={"status": status, "primary_reason": primary_reason},
            created_at=created_at,
        )
    return opportunity_id


def update_opportunity_status(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    updated_at: str,
    status: str | None = None,
    primary_reason: str | None = None,
    lifecycle_event: str | None = None,
    expected_status: str | None = None,
    write_audit: bool = False,
) -> bool:
    row = conn.execute(
        """
        SELECT status, primary_reason, strategy_version_id
        FROM poly_alpha_opportunities
        WHERE opportunity_id = ?
        """,
        (opportunity_id,),
    ).fetchone()
    if row is None:
        return False
    if expected_status is not None and row[0] != expected_status:
        return False

    if lifecycle_event is not None:
        transition = apply_opportunity_transition(lifecycle_event)
        status = status or transition.opportunity_status
    if status is None:
        raise ValueError("Opportunity status or lifecycle_event is required")
    _require_opportunity_status(status)

    audit_action = ""
    if write_audit:
        audit_action = (
            audit_action_for_lifecycle_event(lifecycle_event)
            if lifecycle_event is not None
            else "opportunity_status_updated"
        )

    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = ?,
            primary_reason = CASE WHEN ? IS NULL THEN primary_reason ELSE ? END,
            updated_at = ?
        WHERE opportunity_id = ?
        """,
        (status, primary_reason, primary_reason, updated_at, opportunity_id),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action=audit_action,
            entity_type="opportunity",
            entity_id=opportunity_id,
            strategy_version_id=row[2],
            opportunity_id=opportunity_id,
            before={"status": row[0], "primary_reason": row[1]},
            after={"status": status, "primary_reason": primary_reason},
            reason=primary_reason or "",
            created_at=updated_at,
        )
    return True


def record_market_snapshot(
    conn: sqlite3.Connection,
    *,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    adapter_metadata: dict,
    source_api: str,
    observed_at: str,
    fetched_at: str,
    payload_hash: str,
    best_bid: float,
    best_ask: float,
    spread: float,
    top_bid_depth: float,
    top_ask_depth: float,
    mid_price: float,
    last_trade_price: float,
    liquidity: float,
    volume: float,
    raw_payload: dict,
    created_at: str,
    snapshot_id: str | None = None,
) -> str:
    snapshot_id = snapshot_id or _new_id("snap")
    conn.execute(
        """
        INSERT INTO poly_alpha_market_snapshots
            (snapshot_id, venue, venue_market_id, venue_contract_id, outcome_id,
             adapter_metadata_json, source_api, observed_at, fetched_at,
             payload_hash, best_bid, best_ask, spread, top_bid_depth,
             top_ask_depth, mid_price, last_trade_price, liquidity, volume,
             raw_payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            _json_dumps(adapter_metadata),
            source_api,
            observed_at,
            fetched_at,
            payload_hash,
            best_bid,
            best_ask,
            spread,
            top_bid_depth,
            top_ask_depth,
            mid_price,
            last_trade_price,
            liquidity,
            volume,
            _json_dumps(raw_payload),
            created_at,
        ),
    )
    return snapshot_id


def record_evidence_pack(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    strategy_version_id: str,
    document_ids: list,
    snapshot_ids: list,
    event_ids: list,
    source_set_version: str,
    latest_published_at: str,
    latest_fetched_at: str,
    latest_observed_at: str,
    created_at: str,
    payload_hash: str,
    evidence_pack_id: str | None = None,
    write_audit: bool = False,
) -> str:
    evidence_pack_id = evidence_pack_id or _new_id("pack")
    conn.execute(
        """
        INSERT INTO poly_alpha_evidence_packs
            (evidence_pack_id, opportunity_id, strategy_version_id,
             document_ids_json, snapshot_ids_json, event_ids_json,
             source_set_version, latest_published_at, latest_fetched_at,
             latest_observed_at, created_at, payload_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_pack_id,
            opportunity_id,
            strategy_version_id,
            _json_dumps(document_ids),
            _json_dumps(snapshot_ids),
            _json_dumps(event_ids),
            source_set_version,
            latest_published_at,
            latest_fetched_at,
            latest_observed_at,
            created_at,
            payload_hash,
        ),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="evidence_pack_created",
            entity_type="evidence_pack",
            entity_id=evidence_pack_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={
                "document_ids": document_ids,
                "snapshot_ids": snapshot_ids,
                "event_ids": event_ids,
            },
            created_at=created_at,
        )
    return evidence_pack_id


def record_exploration_decision(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    evidence_pack_id: str,
    strategy_version_id: str,
    decision: str,
    reason: str,
    metrics: dict,
    created_at: str,
    expected_status: str | None = None,
    exploration_id: str | None = None,
    write_audit: bool = False,
) -> str:
    if decision not in _EXPLORATION_STATUS_BY_DECISION:
        raise ValueError(f"Unsupported exploration decision: {decision}")

    row = conn.execute(
        "SELECT status FROM poly_alpha_opportunities WHERE opportunity_id = ?",
        (opportunity_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown opportunity_id: {opportunity_id}")
    if expected_status is not None and row[0] != expected_status:
        raise ValueError(
            f"Expected opportunity status {expected_status}, found {row[0]}"
        )

    next_status = _EXPLORATION_STATUS_BY_DECISION[decision]
    exploration_id = exploration_id or _new_id("exploration")
    conn.execute(
        """
        INSERT INTO poly_alpha_exploration_decisions
            (exploration_id, opportunity_id, evidence_pack_id, strategy_version_id,
             decision, reason, metrics_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            exploration_id,
            opportunity_id,
            evidence_pack_id,
            strategy_version_id,
            decision,
            reason,
            _json_dumps(metrics),
            created_at,
        ),
    )
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = ?, primary_reason = ?, updated_at = ?
        WHERE opportunity_id = ?
        """,
        (next_status, reason if decision == "reject" else "", created_at, opportunity_id),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action=audit_action_for_lifecycle_event(f"exploration_{decision}"),
            entity_type="exploration_decision",
            entity_id=exploration_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            before={"status": row[0]},
            after={"status": next_status, "decision": decision},
            reason=reason,
            created_at=created_at,
        )
    return exploration_id


def record_agent_finding(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    opportunity_id: str,
    evidence_pack_id: str,
    strategy_version_id: str,
    agent_role: str,
    estimated_probability: float,
    market_probability: float,
    edge: float,
    confidence: float,
    recommendation: str,
    thesis: str,
    evidence_ids: list,
    counter_evidence_ids: list,
    resolution_risks: list,
    blockers: list,
    created_at: str,
    finding_id: str | None = None,
) -> str:
    finding_id = finding_id or _new_id("finding")
    conn.execute(
        """
        INSERT INTO poly_alpha_agent_findings
            (finding_id, run_id, opportunity_id, evidence_pack_id,
             strategy_version_id, agent_role, estimated_probability,
             market_probability, edge, confidence, recommendation, thesis,
             evidence_ids_json, counter_evidence_ids_json, resolution_risks_json,
             blockers_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding_id,
            run_id,
            opportunity_id,
            evidence_pack_id,
            strategy_version_id,
            agent_role,
            estimated_probability,
            market_probability,
            edge,
            confidence,
            recommendation,
            thesis,
            _json_dumps(evidence_ids),
            _json_dumps(counter_evidence_ids),
            _json_dumps(resolution_risks),
            _json_dumps(blockers),
            created_at,
        ),
    )
    return finding_id


def record_shadow_signal(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    run_id: str,
    strategy_version_id: str,
    strategy_family: str,
    venue: str,
    venue_market_id: str,
    venue_contract_id: str,
    outcome_id: str,
    adapter_metadata: dict,
    side: str,
    observed_price: float,
    estimated_probability: float,
    edge: float,
    confidence: float,
    status: str,
    created_at: str,
    expires_at: str,
    shadow_signal_id: str | None = None,
    write_audit: bool = False,
) -> str:
    if status not in SHADOW_SIGNAL_STATUSES:
        raise ValueError(f"Unsupported shadow signal status: {status}")

    shadow_signal_id = shadow_signal_id or _new_id("shadow")
    conn.execute(
        """
        INSERT INTO poly_alpha_shadow_signals
            (shadow_signal_id, opportunity_id, run_id, strategy_version_id,
             strategy_family, venue, venue_market_id, venue_contract_id,
             outcome_id, adapter_metadata_json, side, observed_price,
             estimated_probability, edge, confidence, status, created_at,
             expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            shadow_signal_id,
            opportunity_id,
            run_id,
            strategy_version_id,
            strategy_family,
            venue,
            venue_market_id,
            venue_contract_id,
            outcome_id,
            _json_dumps(adapter_metadata),
            side,
            observed_price,
            estimated_probability,
            edge,
            confidence,
            status,
            created_at,
            expires_at,
        ),
    )
    transition = apply_opportunity_transition("shadow_signal_created")
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = ?, updated_at = ?
        WHERE opportunity_id = ?
        """,
        (transition.opportunity_status, created_at, opportunity_id),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action="shadow_signal_created",
            entity_type="shadow_signal",
            entity_id=shadow_signal_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={"status": status, "side": side},
            created_at=created_at,
        )
    return shadow_signal_id


def record_validation_result(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    shadow_signal_id: str,
    strategy_version_id: str,
    entry_snapshot_id: str,
    exit_snapshot_id: str,
    validation_type: str,
    entry_price: float,
    exit_price: float,
    holding_period: str,
    gross_return: float,
    cost_adjusted_return: float,
    closing_line_value: float,
    brier_score: float,
    calibration_error: float,
    edge_decay: float,
    information_lag_sec: int,
    fetch_lag_sec: int,
    market_move_before_signal: float,
    market_move_after_signal: float,
    max_adverse_excursion: float,
    max_favorable_excursion: float,
    liquidity_assumption: str,
    slippage_assumption: str,
    pass_fail: str,
    failure_reason: str,
    created_at: str,
    validation_id: str | None = None,
    write_audit: bool = False,
) -> str:
    validation_id = validation_id or _new_id("validation")
    conn.execute(
        """
        INSERT INTO poly_alpha_validation_results
            (validation_id, opportunity_id, shadow_signal_id, strategy_version_id,
             entry_snapshot_id, exit_snapshot_id, validation_type, entry_price,
             exit_price, holding_period, gross_return, cost_adjusted_return,
             closing_line_value, brier_score, calibration_error, edge_decay,
             information_lag_sec, fetch_lag_sec, market_move_before_signal,
             market_move_after_signal, max_adverse_excursion,
             max_favorable_excursion, liquidity_assumption, slippage_assumption,
             pass_fail, failure_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            validation_id,
            opportunity_id,
            shadow_signal_id,
            strategy_version_id,
            entry_snapshot_id,
            exit_snapshot_id,
            validation_type,
            entry_price,
            exit_price,
            holding_period,
            gross_return,
            cost_adjusted_return,
            closing_line_value,
            brier_score,
            calibration_error,
            edge_decay,
            information_lag_sec,
            fetch_lag_sec,
            market_move_before_signal,
            market_move_after_signal,
            max_adverse_excursion,
            max_favorable_excursion,
            liquidity_assumption,
            slippage_assumption,
            pass_fail,
            failure_reason,
            created_at,
        ),
    )
    lifecycle_event = "validation_pass" if pass_fail == "pass" else "validation_fail"
    transition = apply_opportunity_transition(lifecycle_event)
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = ?,
            primary_reason = CASE WHEN ? = '' THEN primary_reason ELSE ? END,
            updated_at = ?
        WHERE opportunity_id = ?
        """,
        (
            transition.opportunity_status,
            failure_reason,
            failure_reason,
            created_at,
            opportunity_id,
        ),
    )
    conn.execute(
        """
        UPDATE poly_alpha_shadow_signals
        SET status = ?
        WHERE shadow_signal_id = ?
        """,
        (transition.shadow_signal_status, shadow_signal_id),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action=audit_action_for_lifecycle_event(lifecycle_event),
            entity_type="validation_result",
            entity_id=validation_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={"pass_fail": pass_fail, "failure_reason": failure_reason},
            reason=failure_reason,
            created_at=created_at,
        )
    return validation_id


def record_promotion_decision(
    conn: sqlite3.Connection,
    *,
    opportunity_id: str,
    shadow_signal_id: str,
    strategy_version_id: str,
    decision: str,
    reason: str,
    prediction_metrics: dict,
    trading_metrics: dict,
    metrics: dict,
    critic_blockers: list,
    risk_checks: dict,
    proposal_id: str,
    decided_at: str,
    promotion_id: str | None = None,
    write_audit: bool = False,
) -> str:
    if decision not in PROMOTION_DECISIONS:
        raise ValueError(f"Unsupported promotion decision: {decision}")

    promotion_id = promotion_id or _new_id("promotion")
    conn.execute(
        """
        INSERT INTO poly_alpha_promotion_decisions
            (promotion_id, opportunity_id, shadow_signal_id, strategy_version_id,
             decision, reason, prediction_metrics_json, trading_metrics_json,
             metrics_json, critic_blockers_json, risk_checks_json, proposal_id,
             decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            promotion_id,
            opportunity_id,
            shadow_signal_id,
            strategy_version_id,
            decision,
            reason,
            _json_dumps(prediction_metrics),
            _json_dumps(trading_metrics),
            _json_dumps(metrics),
            _json_dumps(critic_blockers),
            _json_dumps(risk_checks),
            proposal_id,
            decided_at,
        ),
    )
    transition = apply_opportunity_transition(f"promotion_{decision}")
    conn.execute(
        """
        UPDATE poly_alpha_opportunities
        SET status = ?, updated_at = ?
        WHERE opportunity_id = ?
        """,
        (transition.opportunity_status, decided_at, opportunity_id),
    )
    conn.execute(
        """
        UPDATE poly_alpha_shadow_signals
        SET status = ?
        WHERE shadow_signal_id = ?
        """,
        (transition.shadow_signal_status, shadow_signal_id),
    )
    if write_audit:
        _record_audit_event(
            conn,
            action=audit_action_for_lifecycle_event(f"promotion_{decision}"),
            entity_type="promotion_decision",
            entity_id=promotion_id,
            strategy_version_id=strategy_version_id,
            opportunity_id=opportunity_id,
            after={"decision": decision, "proposal_id": proposal_id},
            reason=reason,
            created_at=decided_at,
        )
    return promotion_id


def audit_action_for_lifecycle_event(event: str) -> str:
    try:
        return _LIFECYCLE_AUDIT_ACTIONS[event]
    except KeyError as exc:
        raise ValueError(f"Unknown lifecycle event: {event}") from exc


def list_config_versions(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT config_version_id, name, validation_freshness_window_sec,
               min_exploration_samples, min_promotion_samples,
               min_promotion_history_days, max_drawdown_threshold, min_hit_rate,
               min_payoff_ratio, min_capacity_multiple, created_at, is_active,
               promotion_defaults_json
        FROM poly_alpha_config_versions
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [("promotion_defaults_json", "promotion_defaults", {})],
        )
        for row in rows
    ]


def list_source_sets(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT source_set_version, name, created_at, is_active,
               enabled_sources_json, trust_policy_json
        FROM poly_alpha_source_sets
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("enabled_sources_json", "enabled_sources", []),
                ("trust_policy_json", "trust_policy", {}),
            ],
        )
        for row in rows
    ]


def list_strategy_versions(conn: sqlite3.Connection) -> list[dict]:
    return _select_dicts(
        conn,
        """
        SELECT strategy_version_id, strategy_family, strategy_name, version,
               config_version_id, prompt_version, source_set_version, description,
               created_at, is_active
        FROM poly_alpha_strategy_versions
        ORDER BY id
        """,
    )


def list_scan_runs(conn: sqlite3.Connection) -> list[dict]:
    return _select_dicts(
        conn,
        """
        SELECT scan_run_id, trigger_type, strategy_version_id, config_version_id,
               source_set_version, status, started_at, completed_at, scanned_count,
               ignored_count, watch_count, created_opportunity_count, error_message,
               created_at
        FROM poly_alpha_scan_runs
        ORDER BY id
        """,
    )


def list_scan_results(
    conn: sqlite3.Connection,
    scan_run_id: str | None = None,
) -> list[dict]:
    where = ""
    params: tuple[Any, ...] = ()
    if scan_run_id is not None:
        where = "WHERE scan_run_id = ?"
        params = (scan_run_id,)
    rows = _select_dicts(
        conn,
        f"""
        SELECT scan_result_id, scan_run_id, strategy_version_id, venue,
               venue_market_id, venue_contract_id, outcome_id, decision, reason,
               source_snapshot_ids_json, source_document_ids_json,
               created_opportunity_id, observed_at, created_at
        FROM poly_alpha_scan_results
        {where}
        ORDER BY id
        """,
        params,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("source_snapshot_ids_json", "source_snapshot_ids", []),
                ("source_document_ids_json", "source_document_ids", []),
            ],
        )
        for row in rows
    ]


def list_opportunities(conn: sqlite3.Connection) -> list[dict]:
    return _select_dicts(
        conn,
        """
        SELECT opportunity_id, strategy_version_id, venue, venue_market_id,
               venue_contract_id, outcome_id, title, alpha_family, status,
               primary_reason, market_probability, estimated_probability, edge,
               confidence, created_at, updated_at
        FROM poly_alpha_opportunities
        ORDER BY id
        """,
    )


def list_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT document_id, source_type, source_name, url, api_endpoint, market_id,
               venue, venue_market_id, venue_contract_id, outcome_id, asset_symbol,
               topic, published_at, fetched_at, observed_at, payload_hash, title,
               normalized_text, raw_payload_json, trust_level, created_at
        FROM poly_alpha_documents
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(row, [("raw_payload_json", "raw_payload", {})])
        for row in rows
    ]


def list_events(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT event_id, event_type, title, summary, primary_assets_json,
               event_time, status, created_at, updated_at
        FROM poly_alpha_events
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(row, [("primary_assets_json", "primary_assets", [])])
        for row in rows
    ]


def list_event_market_links(
    conn: sqlite3.Connection,
    event_id: str | None = None,
) -> list[dict]:
    where = ""
    params: tuple[Any, ...] = ()
    if event_id is not None:
        where = "WHERE event_id = ?"
        params = (event_id,)
    rows = _select_dicts(
        conn,
        f"""
        SELECT link_id, event_id, venue, venue_market_id, venue_contract_id,
               outcome_id, adapter_metadata_json, outcome, link_reason,
               link_confidence, created_at
        FROM poly_alpha_event_market_links
        {where}
        ORDER BY id
        """,
        params,
    )
    return [
        _decode_json_fields(row, [("adapter_metadata_json", "adapter_metadata", {})])
        for row in rows
    ]


def list_research_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT run_id, trigger_type, opportunity_id, evidence_pack_id,
               strategy_version_id, event_id, venue, venue_market_id, requested_by,
               started_at, completed_at, status, model_config_json, created_at
        FROM poly_alpha_research_runs
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(row, [("model_config_json", "model_config", {})])
        for row in rows
    ]


def list_evidence_packs(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT evidence_pack_id, opportunity_id, strategy_version_id,
               document_ids_json, snapshot_ids_json, event_ids_json,
               source_set_version, latest_published_at, latest_fetched_at,
               latest_observed_at, created_at, payload_hash
        FROM poly_alpha_evidence_packs
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("document_ids_json", "document_ids", []),
                ("snapshot_ids_json", "snapshot_ids", []),
                ("event_ids_json", "event_ids", []),
            ],
        )
        for row in rows
    ]


def list_exploration_decisions(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT exploration_id, opportunity_id, evidence_pack_id,
               strategy_version_id, decision, reason, metrics_json, created_at
        FROM poly_alpha_exploration_decisions
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(row, [("metrics_json", "metrics", {})])
        for row in rows
    ]


def list_market_snapshots(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT snapshot_id, venue, venue_market_id, venue_contract_id, outcome_id,
               adapter_metadata_json, source_api, observed_at, fetched_at,
               payload_hash, best_bid, best_ask, spread, top_bid_depth,
               top_ask_depth, mid_price, last_trade_price, liquidity, volume,
               raw_payload_json, created_at
        FROM poly_alpha_market_snapshots
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("adapter_metadata_json", "adapter_metadata", {}),
                ("raw_payload_json", "raw_payload", {}),
            ],
        )
        for row in rows
    ]


def list_agent_findings(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT finding_id, run_id, opportunity_id, evidence_pack_id,
               strategy_version_id, agent_role, estimated_probability,
               market_probability, edge, confidence, recommendation, thesis,
               evidence_ids_json, counter_evidence_ids_json, resolution_risks_json,
               blockers_json, created_at
        FROM poly_alpha_agent_findings
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("evidence_ids_json", "evidence_ids", []),
                ("counter_evidence_ids_json", "counter_evidence_ids", []),
                ("resolution_risks_json", "resolution_risks", []),
                ("blockers_json", "blockers", []),
            ],
        )
        for row in rows
    ]


def list_shadow_signals(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT shadow_signal_id, opportunity_id, run_id, strategy_version_id,
               strategy_family, venue, venue_market_id, venue_contract_id,
               outcome_id, adapter_metadata_json, side, observed_price,
               estimated_probability, edge, confidence, status, created_at,
               expires_at
        FROM poly_alpha_shadow_signals
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(row, [("adapter_metadata_json", "adapter_metadata", {})])
        for row in rows
    ]


def list_validation_results(conn: sqlite3.Connection) -> list[dict]:
    return _select_dicts(
        conn,
        """
        SELECT validation_id, opportunity_id, shadow_signal_id, strategy_version_id,
               entry_snapshot_id, exit_snapshot_id, validation_type, entry_price,
               exit_price, holding_period, gross_return, cost_adjusted_return,
               closing_line_value, brier_score, calibration_error, edge_decay,
               information_lag_sec, fetch_lag_sec, market_move_before_signal,
               market_move_after_signal, max_adverse_excursion,
               max_favorable_excursion, liquidity_assumption, slippage_assumption,
               pass_fail, failure_reason, created_at
        FROM poly_alpha_validation_results
        ORDER BY id
        """,
    )


def list_promotion_decisions(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT promotion_id, opportunity_id, shadow_signal_id, strategy_version_id,
               decision, reason, prediction_metrics_json, trading_metrics_json,
               metrics_json, critic_blockers_json, risk_checks_json, proposal_id,
               decided_at
        FROM poly_alpha_promotion_decisions
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("prediction_metrics_json", "prediction_metrics", {}),
                ("trading_metrics_json", "trading_metrics", {}),
                ("metrics_json", "metrics", {}),
                ("critic_blockers_json", "critic_blockers", []),
                ("risk_checks_json", "risk_checks", {}),
            ],
        )
        for row in rows
    ]


def list_poly_alpha_audit_events(conn: sqlite3.Connection) -> list[dict]:
    rows = _select_dicts(
        conn,
        """
        SELECT audit_id, action, entity_type, entity_id, opportunity_id,
               strategy_version_id, actor_type, actor_id, before_json, after_json,
               result, reason, request_id, created_at
        FROM poly_alpha_audit_events
        ORDER BY id
        """,
    )
    return [
        _decode_json_fields(
            row,
            [
                ("before_json", "before", {}),
                ("after_json", "after", {}),
            ],
        )
        for row in rows
    ]


def _record_audit_event(
    conn: sqlite3.Connection,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    strategy_version_id: str,
    opportunity_id: str,
    created_at: str,
    actor_type: str = "system",
    actor_id: str = "",
    before: dict | None = None,
    after: dict | None = None,
    result: str = "success",
    reason: str = "",
    request_id: str = "",
) -> str:
    audit_id = _new_id("audit")
    conn.execute(
        """
        INSERT INTO poly_alpha_audit_events
            (audit_id, action, entity_type, entity_id, opportunity_id,
             strategy_version_id, actor_type, actor_id, before_json, after_json,
             result, reason, request_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            action,
            entity_type,
            entity_id,
            opportunity_id,
            strategy_version_id,
            actor_type,
            actor_id,
            _json_dumps(before or {}),
            _json_dumps(after or {}),
            result,
            reason,
            request_id,
            created_at,
        ),
    )
    return audit_id


def _select_dicts(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict]:
    cursor = conn.execute(sql, params)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _decode_json_fields(
    row: dict,
    fields: list[tuple[str, str, Any]],
) -> dict:
    decoded = dict(row)
    for stored_key, public_key, fallback in fields:
        raw = decoded.pop(stored_key)
        decoded[public_key] = json.loads(raw) if raw else fallback
    return decoded


def _json_dumps(value: Any) -> str:
    return json.dumps(value)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _require_opportunity_status(status: str) -> None:
    if status not in OPPORTUNITY_STATUSES:
        raise ValueError(f"Unsupported opportunity status: {status}")
