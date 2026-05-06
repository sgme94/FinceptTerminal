import sqlite3
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_models import SignalDecision
from polymarket_store import (
    ensure_polymarket_schema,
    list_audit_events,
    list_trade_proposals,
    record_audit_event,
    record_trade_proposal,
    update_trade_proposal_status,
)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def test_polymarket_schema_aligns_with_spec():
    conn = sqlite3.connect(":memory:")
    ensure_polymarket_schema(conn)

    trade_columns = _table_columns(conn, "algo_polymarket_trade_proposals")
    audit_columns = _table_columns(conn, "algo_polymarket_audit_events")

    assert trade_columns[:6] == ["id", "proposal_id", "deployment_id", "strategy_id", "market_id", "condition_id"]
    assert "side" in trade_columns
    assert "price" in trade_columns
    assert "fill_trade_id" in trade_columns

    assert audit_columns[:4] == ["id", "event_id", "deployment_id", "strategy_id"]
    assert "event_id" in audit_columns


def test_trade_proposal_lifecycle_is_persisted():
    conn = sqlite3.connect(":memory:")
    ensure_polymarket_schema(conn)

    signal = SignalDecision(
        asset_id="asset-1",
        action="buy",
        entry_price=0.42,
        estimated_probability=0.55,
        edge=0.13,
        confidence=0.72,
        reason="edge_threshold_met",
        features={"momentum": 0.2},
    )

    proposal_id = record_trade_proposal(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        market_id="market-1",
        condition_id="cond-1",
        signal=signal,
        size=10.0,
        now="2026-05-06T00:00:00Z",
        expires_at="2026-05-06T00:01:00Z",
    )
    update_trade_proposal_status(
        conn,
        proposal_id=proposal_id,
        status="approved",
        decided_by="user",
        decided_at="2026-05-06T00:00:10Z",
        decision_reason="manual approval",
    )

    proposals = list_trade_proposals(conn, deployment_id="dep-1")
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["id"] == 1
    assert proposal["proposal_id"] == proposal_id
    assert proposal["side"] == "buy"
    assert proposal["price"] == 0.42
    assert proposal["fill_trade_id"] == ""
    assert proposal["features"] == {"momentum": 0.2}
    assert proposal["status"] == "approved"
    assert proposal["edge"] == 0.13


def test_audit_events_are_append_only_records():
    conn = sqlite3.connect(":memory:")
    ensure_polymarket_schema(conn)

    event_id = record_audit_event(
        conn,
        deployment_id="dep-1",
        strategy_id="strat-1",
        actor_type="user",
        actor_id="local-user",
        action="approve",
        entity_type="proposal",
        entity_id="proposal-1",
        before={"status": "proposed"},
        after={"status": "approved"},
        result="success",
        reason="manual approval",
        request_id="req-1",
        now="2026-05-06T00:00:10Z",
    )

    events = list_audit_events(conn, deployment_id="dep-1")
    assert len(events) == 1
    assert events[0]["event_id"] == event_id
    assert events[0]["action"] == "approve"
    assert events[0]["after"]["status"] == "approved"
