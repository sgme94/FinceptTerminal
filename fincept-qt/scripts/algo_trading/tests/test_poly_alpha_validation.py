import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_config import default_poly_alpha_config
from poly_alpha_store import (
    ensure_poly_alpha_schema,
    list_documents,
    list_market_snapshots,
    list_opportunities,
    list_shadow_signals,
    list_validation_results,
    record_document,
    record_evidence_pack,
    record_market_snapshot,
    record_opportunity,
    record_research_run,
    record_shadow_signal,
    record_source_set,
    record_strategy_version,
)
from poly_alpha_validation import (
    calculate_event_time_metrics,
    run_signal_validation,
    select_entry_snapshot,
)


NOW = "2026-05-07T12:10:00Z"
SIGNAL_AT = "2026-05-07T12:00:00Z"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ensure_poly_alpha_schema(conn)
    _seed_versions(conn)
    return conn


def _seed_versions(conn: sqlite3.Connection) -> None:
    record_source_set(
        conn,
        source_set_version="sources-v1",
        name="phase-1-sources",
        enabled_sources=["polymarket_clob", "official_rss"],
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
    )


def _seed_shadow_signal(
    conn: sqlite3.Connection,
    *,
    market_id: str = "market-1",
    side: str = "buy",
) -> str:
    opportunity_id = record_opportunity(
        conn,
        opportunity_id=f"opp-{market_id}",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        title=f"Opportunity {market_id}",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.57,
        edge=0.15,
        confidence=0.72,
        created_at="2026-05-07T11:50:00Z",
        updated_at="2026-05-07T11:50:00Z",
    )
    evidence_pack_id = record_evidence_pack(
        conn,
        evidence_pack_id=f"pack-{market_id}",
        opportunity_id=opportunity_id,
        strategy_version_id="strat-v1",
        document_ids=[],
        snapshot_ids=[],
        event_ids=[],
        source_set_version="sources-v1",
        latest_published_at="",
        latest_fetched_at="",
        latest_observed_at="",
        created_at="2026-05-07T11:55:00Z",
        payload_hash=f"pack-hash-{market_id}",
    )
    run_id = record_research_run(
        conn,
        run_id=f"run-{market_id}",
        trigger_type="manual_task",
        opportunity_id=opportunity_id,
        evidence_pack_id=evidence_pack_id,
        strategy_version_id="strat-v1",
        event_id="",
        venue="polymarket",
        venue_market_id=market_id,
        requested_by="user",
        started_at="2026-05-07T11:55:00Z",
        completed_at=SIGNAL_AT,
        status="completed",
        model_config={},
        created_at="2026-05-07T11:55:00Z",
    )
    return record_shadow_signal(
        conn,
        shadow_signal_id=f"shadow-{market_id}",
        opportunity_id=opportunity_id,
        run_id=run_id,
        strategy_version_id="strat-v1",
        strategy_family="cross_market_probability",
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        adapter_metadata={},
        side=side,
        observed_price=0.42,
        estimated_probability=0.57,
        edge=0.15,
        confidence=0.72,
        status="shadow",
        created_at=SIGNAL_AT,
        expires_at="2026-05-08T00:00:00Z",
    )


def _insert_snapshot(
    conn: sqlite3.Connection,
    snapshot_id: str,
    observed_at: str,
    price: float,
    *,
    fetched_at: str | None = None,
    market_id: str = "market-1",
) -> str:
    return record_market_snapshot(
        conn,
        snapshot_id=snapshot_id,
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        adapter_metadata={},
        source_api="clob",
        observed_at=observed_at,
        fetched_at=fetched_at or observed_at,
        payload_hash=f"hash-{snapshot_id}",
        best_bid=price - 0.01,
        best_ask=price + 0.01,
        spread=0.02,
        top_bid_depth=250.0,
        top_ask_depth=220.0,
        mid_price=price,
        last_trade_price=price,
        liquidity=1200.0,
        volume=5000.0,
        raw_payload={"id": snapshot_id},
        created_at=NOW,
    )


def _insert_document(
    conn: sqlite3.Connection,
    document_id: str,
    published_at: str,
    fetched_at: str,
    *,
    market_id: str = "market-1",
) -> str:
    return record_document(
        conn,
        document_id=document_id,
        source_type="rss",
        source_name="Official feed",
        url="https://example.invalid/feed",
        api_endpoint="",
        venue="polymarket",
        venue_market_id=market_id,
        venue_contract_id=f"contract-{market_id}",
        outcome_id="yes",
        asset_symbol="BTC",
        topic="crypto",
        published_at=published_at,
        fetched_at=fetched_at,
        observed_at=fetched_at,
        payload_hash=f"doc-hash-{document_id}",
        title=f"Document {document_id}",
        normalized_text="normalized evidence",
        raw_payload={"id": document_id},
        trust_level="official",
        created_at=NOW,
    )


def test_select_entry_snapshot_requires_fresh_snapshot_at_or_before_signal():
    snapshots = [
        {
            "snapshot_id": "old",
            "venue": "polymarket",
            "venue_market_id": "market-1",
            "venue_contract_id": "contract-market-1",
            "outcome_id": "yes",
            "observed_at": "2026-05-07T11:54:59Z",
        },
        {
            "snapshot_id": "future",
            "venue": "polymarket",
            "venue_market_id": "market-1",
            "venue_contract_id": "contract-market-1",
            "outcome_id": "yes",
            "observed_at": "2026-05-07T12:00:01Z",
        },
    ]
    signal = {
        "venue": "polymarket",
        "venue_market_id": "market-1",
        "venue_contract_id": "contract-market-1",
        "outcome_id": "yes",
        "created_at": SIGNAL_AT,
    }

    assert select_entry_snapshot(snapshots, signal, 300) is None


def test_select_entry_snapshot_accepts_signal_created_at_string():
    snapshots = [
        {
            "snapshot_id": "entry",
            "observed_at": "2026-05-07T11:59:30Z",
        }
    ]

    selected = select_entry_snapshot(snapshots, SIGNAL_AT, 300)

    assert selected["snapshot_id"] == "entry"


def test_validation_records_missing_market_snapshot_failure():
    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn)
    _insert_snapshot(conn, "snap-stale", "2026-05-07T11:54:59Z", 0.40)

    result = run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config(),
        NOW,
    )

    rows = list_validation_results(conn)
    assert result["pass_fail"] == "fail"
    assert result["failure_reason"] == "missing_market_snapshot"
    assert len(rows) == 1
    assert rows[0]["validation_type"] == "entry_snapshot"
    assert rows[0]["pass_fail"] == "fail"
    assert rows[0]["failure_reason"] == "missing_market_snapshot"
    assert rows[0]["entry_snapshot_id"] == ""
    assert list_opportunities(conn)[0]["status"] == "rejected"
    assert list_opportunities(conn)[0]["primary_reason"] == "missing_market_snapshot"
    assert list_shadow_signals(conn)[0]["status"] == "rejected"


def test_event_time_metrics_detect_late_information_from_cited_documents():
    conn = _conn()
    _seed_shadow_signal(conn)
    entry_id = _insert_snapshot(
        conn,
        "snap-entry",
        "2026-05-07T11:59:30Z",
        0.55,
        fetched_at="2026-05-07T11:59:35Z",
    )
    _insert_snapshot(conn, "snap-before-info", "2026-05-07T11:44:00Z", 0.40)
    _insert_snapshot(conn, "snap-at-info", "2026-05-07T11:45:00Z", 0.40)
    _insert_snapshot(conn, "snap-after-signal", "2026-05-07T12:05:00Z", 0.57)
    document_id = _insert_document(
        conn,
        "doc-late",
        published_at="2026-05-07T11:45:00Z",
        fetched_at="2026-05-07T11:58:00Z",
    )

    metrics = calculate_event_time_metrics(
        shadow_signal=list_shadow_signals(conn)[0],
        entry_snapshot=[
            row for row in list_market_snapshots(conn)
            if row["snapshot_id"] == entry_id
        ][0],
        documents=[row for row in list_documents(conn) if row["document_id"] == document_id],
        snapshots=list_market_snapshots(conn),
    )

    assert metrics["information_lag_sec"] == 900
    assert metrics["fetch_lag_sec"] == 120
    assert metrics["market_move_before_signal"] == pytest.approx(0.15)
    assert metrics["market_move_after_signal"] == pytest.approx(0.02)
    assert metrics["failure_reason"] == "late_information"


def test_event_time_metrics_anchor_moves_at_signal_entry_snapshot():
    conn = _conn()
    _seed_shadow_signal(conn)
    entry_id = _insert_snapshot(
        conn,
        "snap-entry",
        "2026-05-07T11:59:30Z",
        0.55,
        fetched_at="2026-05-07T11:59:35Z",
    )
    _insert_snapshot(conn, "snap-before-info", "2026-05-07T11:44:00Z", 0.40)
    _insert_snapshot(conn, "snap-at-info", "2026-05-07T11:45:00Z", 0.40)
    _insert_snapshot(conn, "snap-after-signal", "2026-05-07T12:05:00Z", 0.56)
    document_id = _insert_document(
        conn,
        "doc-signal-anchor",
        published_at="2026-05-07T11:45:00Z",
        fetched_at="2026-05-07T11:58:00Z",
    )

    metrics = calculate_event_time_metrics(
        shadow_signal=list_shadow_signals(conn)[0],
        entry_snapshot=[
            row for row in list_market_snapshots(conn)
            if row["snapshot_id"] == entry_id
        ][0],
        documents=[row for row in list_documents(conn) if row["document_id"] == document_id],
        snapshots=list_market_snapshots(conn),
    )

    assert metrics["market_move_before_signal"] == pytest.approx(0.15)
    assert metrics["market_move_after_signal"] == pytest.approx(0.01)
    assert metrics["failure_reason"] == "late_information"


def test_validation_records_late_information_on_template_rows():
    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn)
    _insert_snapshot(
        conn,
        "snap-entry",
        "2026-05-07T11:59:30Z",
        0.55,
        fetched_at="2026-05-07T11:59:35Z",
    )
    _insert_snapshot(conn, "snap-before-info", "2026-05-07T11:44:00Z", 0.40)
    _insert_snapshot(conn, "snap-at-info", "2026-05-07T11:45:00Z", 0.40)
    _insert_snapshot(conn, "snap-after-signal", "2026-05-07T12:05:00Z", 0.57)
    document_id = _insert_document(
        conn,
        "doc-late",
        published_at="2026-05-07T11:45:00Z",
        fetched_at="2026-05-07T11:58:00Z",
    )
    conn.execute(
        "UPDATE poly_alpha_evidence_packs SET document_ids_json = ? WHERE evidence_pack_id = ?",
        (f'["{document_id}"]', "pack-market-1"),
    )

    run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config(),
        NOW,
    )

    rows = list_validation_results(conn)
    assert {row["validation_type"] for row in rows} == {
        "fixed_horizon",
        "target_stop",
        "resolution_expiry",
    }
    assert {row["failure_reason"] for row in rows} == {"late_information"}
    assert all(row["pass_fail"] == "fail" for row in rows)
    assert all(row["information_lag_sec"] == 900 for row in rows)
    assert all(row["fetch_lag_sec"] == 120 for row in rows)
    assert all(row["market_move_before_signal"] == pytest.approx(0.15) for row in rows)
    assert all(row["market_move_after_signal"] == pytest.approx(0.02) for row in rows)


def test_validation_records_exit_templates_with_resolved_and_unresolved_metrics():
    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn)
    _insert_snapshot(conn, "snap-entry", "2026-05-07T11:59:30Z", 0.42)
    _insert_snapshot(conn, "snap-1h", "2026-05-07T13:00:00Z", 0.48)
    _insert_snapshot(conn, "snap-target", "2026-05-07T12:20:00Z", 0.55)
    _insert_snapshot(conn, "snap-resolution", "2026-05-08T00:00:00Z", 0.62)

    run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config(
            {
                "fixed_horizon_sec": 3600,
                "target_return": 0.10,
                "stop_return": -0.05,
                "resolution_at": "2026-05-08T00:00:00Z",
                "resolved_outcome": 1,
            }
        ),
        NOW,
    )

    resolved = {row["validation_type"]: row for row in list_validation_results(conn)}
    assert set(resolved) == {"fixed_horizon", "target_stop", "resolution_expiry"}
    assert resolved["fixed_horizon"]["exit_snapshot_id"] == "snap-1h"
    assert resolved["target_stop"]["exit_snapshot_id"] == "snap-target"
    assert resolved["resolution_expiry"]["exit_snapshot_id"] == "snap-resolution"
    assert resolved["fixed_horizon"]["closing_line_value"] == pytest.approx(0.06)
    assert resolved["target_stop"]["closing_line_value"] == pytest.approx(0.13)
    assert resolved["resolution_expiry"]["brier_score"] == pytest.approx((1 - 0.57) ** 2)
    assert resolved["resolution_expiry"]["calibration_error"] == pytest.approx(0.43)
    assert all(row["edge_decay"] == pytest.approx(0.0) for row in resolved.values())

    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn)
    _insert_snapshot(conn, "snap-entry-open", "2026-05-07T11:59:30Z", 0.42)
    _insert_snapshot(conn, "snap-now", "2026-05-07T12:08:00Z", 0.44)

    run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config({"current_market_price": 0.44}),
        NOW,
    )

    unresolved = list_validation_results(conn)
    assert {row["validation_type"] for row in unresolved} == {
        "fixed_horizon",
        "target_stop",
        "resolution_expiry",
    }
    assert all(row["brier_score"] is None for row in unresolved)
    assert all(row["calibration_error"] is None for row in unresolved)
    assert all(row["edge_decay"] == pytest.approx(0.02) for row in unresolved)


def test_validation_records_market_move_after_signal_per_exit_template():
    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn)
    _insert_snapshot(conn, "snap-info", "2026-05-07T11:45:00Z", 0.45)
    _insert_snapshot(conn, "snap-entry", "2026-05-07T11:59:30Z", 0.50)
    _insert_snapshot(conn, "snap-fixed", "2026-05-07T13:00:00Z", 0.52)
    _insert_snapshot(conn, "snap-target", "2026-05-07T13:30:00Z", 0.60)
    _insert_snapshot(conn, "snap-resolution", "2026-05-08T00:00:00Z", 0.55)
    document_id = _insert_document(
        conn,
        "doc-row-specific-move",
        published_at="2026-05-07T11:45:00Z",
        fetched_at="2026-05-07T11:58:00Z",
    )
    conn.execute(
        "UPDATE poly_alpha_evidence_packs SET document_ids_json = ? WHERE evidence_pack_id = ?",
        (f'["{document_id}"]', "pack-market-1"),
    )

    run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config(
            {
                "fixed_horizon_sec": 3600,
                "target_return": 0.19,
                "stop_return": -0.05,
                "resolution_at": "2026-05-08T00:00:00Z",
            }
        ),
        NOW,
    )

    rows = {row["validation_type"]: row for row in list_validation_results(conn)}
    assert rows["fixed_horizon"]["exit_snapshot_id"] == "snap-fixed"
    assert rows["target_stop"]["exit_snapshot_id"] == "snap-target"
    assert rows["resolution_expiry"]["exit_snapshot_id"] == "snap-resolution"
    assert rows["fixed_horizon"]["market_move_after_signal"] == pytest.approx(0.02)
    assert rows["target_stop"]["market_move_after_signal"] == pytest.approx(0.10)
    assert rows["resolution_expiry"]["market_move_after_signal"] == pytest.approx(0.05)


def test_validation_target_stop_uses_sell_side_for_exit_selection():
    conn = _conn()
    shadow_signal_id = _seed_shadow_signal(conn, side="sell")
    _insert_snapshot(conn, "snap-entry", "2026-05-07T11:59:30Z", 0.60)
    _insert_snapshot(conn, "snap-buy-stop", "2026-05-07T12:05:00Z", 0.57)
    _insert_snapshot(conn, "snap-sell-target", "2026-05-07T12:10:00Z", 0.54)

    run_signal_validation(
        conn,
        shadow_signal_id,
        default_poly_alpha_config(
            {
                "target_return": 0.10,
                "stop_return": -0.05,
            }
        ),
        NOW,
    )

    rows = {row["validation_type"]: row for row in list_validation_results(conn)}
    assert rows["target_stop"]["exit_snapshot_id"] == "snap-sell-target"
    assert rows["target_stop"]["gross_return"] == pytest.approx(0.10)
