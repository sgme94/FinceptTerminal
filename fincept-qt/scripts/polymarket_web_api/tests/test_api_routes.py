import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
ALGO_ROOT = SCRIPT_ROOT / "algo_trading"
for path in (SCRIPT_ROOT, ALGO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from polymarket_web_api.app import create_app
from polymarket_store import ensure_polymarket_schema, record_audit_event


def insert_proposal(conn, proposal_id="proposal-1", deployment_id="dep-1"):
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
            "proposed",
            "2026-05-06T00:00:00Z",
            "2026-05-07T00:00:00Z",
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
