import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_config import default_poly_alpha_config
from poly_alpha_scanner import (
    build_evidence_pack,
    decide_exploration,
    run_deterministic_scan,
)
from poly_alpha_store import (
    ensure_poly_alpha_schema,
    list_agent_findings,
    list_documents,
    list_evidence_packs,
    list_exploration_decisions,
    list_market_snapshots,
    list_opportunities,
    list_scan_results,
    list_scan_runs,
    record_document,
    record_event,
    record_event_market_link,
    record_market_snapshot,
    record_opportunity,
    record_source_set,
    record_strategy_version,
)


NOW = "2026-05-07T12:00:00Z"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ensure_poly_alpha_schema(conn)
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


def _document(
    document_id: str,
    venue_market_id: str,
    *,
    source_name: str = "Official feed",
    fetched_at: str = "2026-05-07T11:45:00Z",
    payload_hash: str | None = None,
) -> dict:
    return {
        "document_id": document_id,
        "source_type": "rss",
        "source_name": source_name,
        "url": "https://example.invalid/feed",
        "api_endpoint": "",
        "market_id": "",
        "venue": "polymarket",
        "venue_market_id": venue_market_id,
        "venue_contract_id": f"contract-{venue_market_id}",
        "outcome_id": "yes",
        "asset_symbol": "BTC",
        "topic": "crypto",
        "published_at": "2026-05-07T11:30:00Z",
        "fetched_at": fetched_at,
        "observed_at": "2026-05-07T11:46:00Z",
        "payload_hash": payload_hash if payload_hash is not None else f"hash-{document_id}",
        "title": f"Document {document_id}",
        "normalized_text": "normalized evidence",
        "raw_payload": {"id": document_id},
        "trust_level": "official",
    }


def _snapshot(
    snapshot_id: str,
    venue_market_id: str,
    *,
    spread: float | None = 0.02,
    liquidity: float | None = 1200.0,
    top_bid_depth: float | None = 250.0,
    top_ask_depth: float | None = 220.0,
    mid_price: float | None = 0.42,
    market_probability: float | None = 0.42,
    qualifies: bool = False,
    estimated_probability: float = 0.57,
    payload_hash: str | None = None,
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "venue": "polymarket",
        "venue_market_id": venue_market_id,
        "venue_contract_id": f"contract-{venue_market_id}",
        "outcome_id": "yes",
        "adapter_metadata": {"condition_id": f"cond-{venue_market_id}"},
        "source_api": "clob",
        "observed_at": "2026-05-07T11:59:30Z",
        "fetched_at": "2026-05-07T11:59:35Z",
        "payload_hash": payload_hash if payload_hash is not None else f"hash-{snapshot_id}",
        "best_bid": 0.41,
        "best_ask": 0.43,
        "spread": spread,
        "top_bid_depth": top_bid_depth,
        "top_ask_depth": top_ask_depth,
        "mid_price": mid_price,
        "last_trade_price": 0.421,
        "liquidity": liquidity,
        "volume": 5000.0,
        "raw_payload": {"id": snapshot_id},
        "title": f"Market {venue_market_id}",
        "alpha_family": "cross_market_probability",
        "market_probability": market_probability,
        "estimated_probability": estimated_probability,
        "confidence": 0.72,
        "qualifies": qualifies,
    }


def _insert_document(conn: sqlite3.Connection, document: dict) -> str:
    return record_document(conn, created_at=NOW, **document)


def _insert_snapshot(conn: sqlite3.Connection, snapshot: dict) -> str:
    stored_snapshot = {
        key: value
        for key, value in snapshot.items()
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
    return record_market_snapshot(conn, created_at=NOW, **stored_snapshot)


def _seed_full_evidence(
    conn: sqlite3.Connection,
    *,
    document_overrides: dict | None = None,
    snapshot_overrides: dict | None = None,
    create_snapshot: bool = True,
    create_link: bool = True,
    market_probability: float | None = 0.42,
) -> tuple[str, str]:
    _seed_versions(conn)
    opportunity_id = record_opportunity(
        conn,
        opportunity_id="opp-1",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-pass",
        venue_contract_id="contract-market-pass",
        outcome_id="yes",
        title="BTC above 100k",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=market_probability,
        estimated_probability=0.57,
        edge=0.15,
        confidence=0.72,
        created_at=NOW,
        updated_at=NOW,
    )
    document = _document("doc-1", "market-pass")
    if document_overrides:
        document.update(document_overrides)
    document_id = _insert_document(conn, document)
    event_id = record_event(
        conn,
        event_id="event-1",
        event_type="crypto_price",
        title="BTC breaks level",
        summary="BTC moved quickly",
        primary_assets=["BTC"],
        event_time="2026-05-07T11:40:00Z",
        status="open",
        created_at=NOW,
        updated_at=NOW,
    )
    if create_link:
        record_event_market_link(
            conn,
            event_id=event_id,
            venue="polymarket",
            venue_market_id="market-pass",
            venue_contract_id="contract-market-pass",
            outcome_id="yes",
            adapter_metadata={"condition_id": "cond-market-pass"},
            outcome="yes",
            link_reason="same underlying event",
            link_confidence=0.82,
            created_at=NOW,
        )
    snapshot_ids = []
    if create_snapshot:
        snapshot = _snapshot("snap-1", "market-pass")
        if snapshot_overrides:
            snapshot.update(snapshot_overrides)
        snapshot_ids.append(_insert_snapshot(conn, snapshot))
    evidence_pack_id = build_evidence_pack(
        conn,
        opportunity_id,
        [document_id],
        snapshot_ids,
        [event_id],
        NOW,
    )
    return opportunity_id, evidence_pack_id


def test_scheduled_scan_groups_results_snapshots_and_opportunity_creation():
    conn = _conn()
    _seed_versions(conn)

    result = run_deterministic_scan(
        conn,
        "strat-v1",
        {
            "config_version": "cfg-v1",
            "max_spread": 0.05,
            "min_liquidity": 500.0,
            "min_top_of_book_depth": 100.0,
        },
        [
            _document("doc-good", "market-good"),
            _document("doc-wide", "market-wide"),
            _document("doc-thin", "market-thin"),
        ],
        [
            _snapshot("snap-good", "market-good", qualifies=True),
            _snapshot("snap-wide", "market-wide", spread=0.12, qualifies=True),
            _snapshot("snap-thin", "market-thin", liquidity=100.0, qualifies=True),
        ],
        NOW,
    )

    scan_runs = list_scan_runs(conn)
    assert len(scan_runs) == 1
    assert scan_runs[0]["scan_run_id"] == result["scan_run_id"]
    assert scan_runs[0]["trigger_type"] == "scheduled_scan"
    assert scan_runs[0]["status"] == "completed"
    assert scan_runs[0]["scanned_count"] == 3
    assert scan_runs[0]["ignored_count"] == 2
    assert scan_runs[0]["created_opportunity_count"] == 1

    assert {row["snapshot_id"] for row in list_market_snapshots(conn)} == {
        "snap-good",
        "snap-wide",
        "snap-thin",
    }
    assert {row["document_id"] for row in list_documents(conn)} == {
        "doc-good",
        "doc-wide",
        "doc-thin",
    }

    results_by_market = {
        row["venue_market_id"]: row for row in list_scan_results(conn, result["scan_run_id"])
    }
    assert results_by_market["market-good"]["decision"] == "create_opportunity"
    assert results_by_market["market-good"]["reason"] == "edge_detected"
    assert results_by_market["market-good"]["source_snapshot_ids"] == ["snap-good"]
    assert results_by_market["market-good"]["source_document_ids"] == ["doc-good"]
    assert results_by_market["market-good"]["created_opportunity_id"]
    assert results_by_market["market-wide"]["decision"] == "ignore"
    assert results_by_market["market-wide"]["reason"] == "wide_spread"
    assert results_by_market["market-thin"]["decision"] == "ignore"
    assert results_by_market["market-thin"]["reason"] == "low_liquidity"

    opportunities = list_opportunities(conn)
    assert len(opportunities) == 1
    assert opportunities[0]["opportunity_id"] == results_by_market["market-good"][
        "created_opportunity_id"
    ]
    assert opportunities[0]["status"] == "watch"
    assert opportunities[0]["market_probability"] == pytest.approx(0.42)
    assert opportunities[0]["estimated_probability"] == pytest.approx(0.57)
    assert opportunities[0]["edge"] == pytest.approx(0.15)


def test_build_evidence_pack_persists_citable_ids_and_latest_timestamps():
    conn = _conn()
    _seed_versions(conn)
    opportunity_id = record_opportunity(
        conn,
        opportunity_id="opp-pack",
        strategy_version_id="strat-v1",
        venue="polymarket",
        venue_market_id="market-pack",
        venue_contract_id="contract-market-pack",
        outcome_id="yes",
        title="BTC above 100k",
        alpha_family="cross_market_probability",
        status="watch",
        primary_reason="",
        market_probability=0.42,
        estimated_probability=0.57,
        edge=0.15,
        confidence=0.72,
        created_at=NOW,
        updated_at=NOW,
    )
    doc_early = _insert_document(
        conn,
        {
            **_document("doc-early", "market-pack"),
            "published_at": "2026-05-07T10:00:00Z",
            "fetched_at": "2026-05-07T10:01:00Z",
            "observed_at": "2026-05-07T10:02:00Z",
        },
    )
    doc_late = _insert_document(
        conn,
        {
            **_document("doc-late", "market-pack"),
            "published_at": "2026-05-07T11:00:00Z",
            "fetched_at": "2026-05-07T11:01:00Z",
            "observed_at": "2026-05-07T11:02:00Z",
        },
    )
    snapshot_id = _insert_snapshot(
        conn,
        {
            **_snapshot("snap-pack", "market-pack"),
            "fetched_at": "2026-05-07T11:10:00Z",
            "observed_at": "2026-05-07T11:09:00Z",
        },
    )
    event_id = record_event(
        conn,
        event_id="event-pack",
        event_type="crypto_price",
        title="BTC breaks level",
        summary="BTC moved quickly",
        primary_assets=["BTC"],
        event_time="2026-05-07T10:30:00Z",
        status="open",
        created_at=NOW,
        updated_at=NOW,
    )

    evidence_pack_id = build_evidence_pack(
        conn,
        opportunity_id,
        [doc_early, doc_late],
        [snapshot_id],
        [event_id],
        NOW,
    )

    packs = list_evidence_packs(conn)
    assert len(packs) == 1
    assert packs[0]["evidence_pack_id"] == evidence_pack_id
    assert packs[0]["opportunity_id"] == opportunity_id
    assert packs[0]["strategy_version_id"] == "strat-v1"
    assert packs[0]["source_set_version"] == "sources-v1"
    assert packs[0]["document_ids"] == [doc_early, doc_late]
    assert packs[0]["snapshot_ids"] == [snapshot_id]
    assert packs[0]["event_ids"] == [event_id]
    assert packs[0]["latest_published_at"] == "2026-05-07T11:00:00Z"
    assert packs[0]["latest_fetched_at"] == "2026-05-07T11:10:00Z"
    assert packs[0]["latest_observed_at"] == "2026-05-07T11:09:00Z"
    assert packs[0]["payload_hash"]


def test_decide_exploration_passes_with_phase_1_default_without_agent_findings():
    conn = _conn()
    opportunity_id, evidence_pack_id = _seed_full_evidence(conn)
    config = default_poly_alpha_config({"historical_sample_count": 10})

    exploration_id = decide_exploration(
        conn,
        opportunity_id,
        evidence_pack_id,
        config,
        NOW,
    )

    decisions = list_exploration_decisions(conn)
    assert len(decisions) == 1
    assert decisions[0]["exploration_id"] == exploration_id
    assert decisions[0]["decision"] == "pass"
    assert config["min_exploration_samples"] == 10
    assert list_opportunities(conn)[0]["status"] == "watch"
    assert list_agent_findings(conn) == []

    metrics = decisions[0]["metrics"]
    assert metrics["historical_sample_count"] == 10
    assert metrics["min_exploration_samples"] == 10
    assert metrics["event_market_link_confidence_recorded"] is True
    assert metrics["current_market_metrics"]["market_probability"] == pytest.approx(0.42)
    assert metrics["current_market_metrics"]["spread"] == pytest.approx(0.02)
    assert metrics["current_market_metrics"]["top_bid_depth"] == pytest.approx(250.0)
    assert metrics["current_market_metrics"]["top_ask_depth"] == pytest.approx(220.0)
    assert metrics["current_market_metrics"]["liquidity"] == pytest.approx(1200.0)
    assert metrics["evidence_completeness"] == {
        "document_count": 1,
        "snapshot_count": 1,
        "event_count": 1,
        "source_metadata_complete": True,
        "fetched_timestamps_complete": True,
        "payload_hashes_complete": True,
    }


@pytest.mark.parametrize(
    (
        "case",
        "historical_sample_count",
        "document_overrides",
        "snapshot_overrides",
        "create_snapshot",
        "create_link",
        "market_probability",
        "expected_decision",
        "expected_status",
        "expected_reason",
    ),
    [
        (
            "sample_count_below_default",
            9,
            None,
            None,
            True,
            True,
            0.42,
            "watch",
            "watch",
            "insufficient_exploration_samples",
        ),
        (
            "missing_source_metadata",
            10,
            {"source_name": ""},
            None,
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "incomplete_source_metadata",
        ),
        (
            "missing_fetched_timestamp",
            10,
            {"fetched_at": ""},
            None,
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_fetched_timestamps",
        ),
        (
            "missing_payload_hash",
            10,
            {"payload_hash": ""},
            None,
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_payload_hashes",
        ),
        (
            "missing_current_snapshot",
            10,
            None,
            None,
            False,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_current_snapshot",
        ),
        (
            "missing_link_confidence",
            10,
            None,
            None,
            True,
            False,
            0.42,
            "reject",
            "rejected",
            "missing_link_confidence",
        ),
        (
            "missing_market_probability",
            10,
            None,
            None,
            True,
            True,
            None,
            "reject",
            "rejected",
            "missing_market_metrics",
        ),
        (
            "missing_market_spread",
            10,
            None,
            {"spread": None},
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_market_metrics",
        ),
        (
            "missing_market_depth",
            10,
            None,
            {"top_bid_depth": None},
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_market_metrics",
        ),
        (
            "missing_market_liquidity",
            10,
            None,
            {"liquidity": None},
            True,
            True,
            0.42,
            "reject",
            "rejected",
            "missing_market_metrics",
        ),
    ],
)
def test_decide_exploration_requires_deterministic_gate_inputs(
    case,
    historical_sample_count,
    document_overrides,
    snapshot_overrides,
    create_snapshot,
    create_link,
    market_probability,
    expected_decision,
    expected_status,
    expected_reason,
):
    conn = _conn()
    opportunity_id, evidence_pack_id = _seed_full_evidence(
        conn,
        document_overrides=document_overrides,
        snapshot_overrides=snapshot_overrides,
        create_snapshot=create_snapshot,
        create_link=create_link,
        market_probability=market_probability,
    )

    decide_exploration(
        conn,
        opportunity_id,
        evidence_pack_id,
        default_poly_alpha_config({"historical_sample_count": historical_sample_count}),
        NOW,
    )

    decision = list_exploration_decisions(conn)[0]
    assert decision["decision"] == expected_decision, case
    assert decision["reason"] == expected_reason, case
    assert list_opportunities(conn)[0]["status"] == expected_status, case
