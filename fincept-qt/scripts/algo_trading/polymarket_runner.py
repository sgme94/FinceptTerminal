from __future__ import annotations

import argparse
import json
import sqlite3
import time
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket_config import default_bot_config
from polymarket_edge import compute_edge_signal
from polymarket_models import OrderBook, RiskConfig, SignalDecision
from polymarket_paper import apply_fill_to_position, should_exit_position, simulate_entry_fill, simulate_exit_fill
from polymarket_risk import PortfolioState, check_entry_risk
from polymarket_scanner import scan_markets
from polymarket_sources import PolymarketRestSource, load_fixture
from polymarket_store import (
    delete_position,
    ensure_polymarket_schema,
    has_open_trade_proposal,
    list_trade_proposals,
    load_positions,
    record_candidate,
    record_audit_event,
    record_scan_skip,
    record_signal,
    record_skip,
    record_trade,
    record_trade_proposal,
    update_trade_proposal_status,
    upsert_position,
)


def run_polymarket_cycle(
    *,
    db_path: str,
    deployment_id: str,
    strategy_id: str,
    market_payload: dict,
    order_books: dict[str, dict] | None = None,
    edge_overrides: dict[str, dict] | None = None,
    source: PolymarketRestSource | None = None,
    now: str,
) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        ensure_polymarket_schema(conn)
        cfg = _load_bot_config(conn, strategy_id)
        books = dict(order_books or {})
        should_fetch_books = order_books is None
        overrides = edge_overrides or {}

        result = {
            "success": True,
            "scanned": 0,
            "signals": 0,
            "fills": 0,
            "proposals": 0,
            "exits": 0,
            "skips": 0,
        }

        scan = scan_markets(market_payload.get("data", []), config=cfg, fetched_at=market_payload.get("fetched_at", now))
        for skipped in scan.skipped:
            record_scan_skip(conn, deployment_id, skipped, now)
            result["skips"] += 1

        candidates = scan.candidates[: int(cfg.get("max_candidates", 20))]
        for candidate in candidates:
            record_candidate(conn, deployment_id, strategy_id, candidate, now)
        result["scanned"] = len(candidates)

        if should_fetch_books:
            source = source or PolymarketRestSource()
            for candidate in candidates:
                if candidate.asset_id not in books:
                    books[candidate.asset_id] = source.fetch_clob_order_book(candidate.asset_id)

        _expire_proposed_proposals(conn, deployment_id, now)
        positions = load_positions(conn, deployment_id)
        exited_assets = _process_exits(conn, deployment_id, positions, books, overrides, cfg, now, result)
        _process_approved_proposals(
            conn,
            deployment_id,
            positions,
            books,
            source if should_fetch_books else None,
            cfg,
            now,
            result,
        )
        _process_entries(conn, deployment_id, strategy_id, positions, exited_assets, candidates, books, overrides, cfg, now, result)

        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_polymarket_loop(*, args, strategy: dict) -> None:
    if getattr(args, "mode", "paper") != "paper":
        raise RuntimeError("Polymarket bot supports paper mode only")

    cfg = default_bot_config(strategy.get("bot_config", {}))
    source = PolymarketRestSource()
    while True:
        now = source._now()
        market_payload = source.fetch_gamma_markets(
            limit=int(cfg.get("max_candidates", 20)),
            sort_by=str(cfg.get("sort_by", "volume")),
        )
        run_polymarket_cycle(
            db_path=args.db,
            deployment_id=args.deploy_id,
            strategy_id=args.strategy_id,
            market_payload=market_payload,
            order_books=None,
            source=source,
            now=now,
        )
        time.sleep(int(cfg.get("scan_interval_sec", 60)))


def _process_exits(conn, deployment_id, positions, books, overrides, cfg, now, result) -> set[str]:
    exited_assets: set[str] = set()
    for asset_id, position in list(positions.items()):
        book_payload = books.get(asset_id)
        if not book_payload:
            record_skip(conn, deployment_id, "missing_orderbook", now, asset_id=asset_id)
            result["skips"] += 1
            continue
        book = _book_from_payload(book_payload)
        override = overrides.get(asset_id)
        signal = None
        if override:
            signal = SignalDecision(asset_id=asset_id, action=override.get("action", "skip"), reason=override.get("reason", ""))
        reason = should_exit_position(position, book, cfg, signal=signal)
        if not reason:
            continue
        fill = simulate_exit_fill(position, book, reason=reason)
        if not fill.ok:
            record_skip(conn, deployment_id, fill.reason, now, asset_id=asset_id)
            result["skips"] += 1
            continue
        record_trade(conn, deployment_id, fill, now)
        delete_position(conn, deployment_id, asset_id)
        positions.pop(asset_id, None)
        exited_assets.add(asset_id)
        result["exits"] += 1
    return exited_assets


def _process_entries(conn, deployment_id, strategy_id, positions, exited_assets, candidates, books, overrides, cfg, now, result) -> None:
    for candidate in candidates:
        if candidate.asset_id in positions:
            continue
        if has_open_trade_proposal(conn, deployment_id, candidate.asset_id):
            record_skip(
                conn,
                deployment_id,
                "open_proposal_exists",
                now,
                market_id=candidate.market_id,
                asset_id=candidate.asset_id,
            )
            result["skips"] += 1
            continue
        if candidate.asset_id in exited_assets:
            record_skip(conn, deployment_id, "exited_this_cycle", now, market_id=candidate.market_id, asset_id=candidate.asset_id)
            result["skips"] += 1
            continue

        book_payload = books.get(candidate.asset_id)
        if not book_payload:
            record_skip(conn, deployment_id, "missing_orderbook", now, market_id=candidate.market_id, asset_id=candidate.asset_id)
            result["skips"] += 1
            continue
        if _is_stale(book_payload, now, int(cfg.get("freshness_ttl_sec", 30))):
            record_skip(conn, deployment_id, "stale_orderbook", now, market_id=candidate.market_id, asset_id=candidate.asset_id)
            result["skips"] += 1
            continue

        book = _book_from_payload(book_payload)
        signal = _signal_for_candidate(candidate, book, overrides, cfg)
        record_signal(conn, deployment_id, signal, now)
        result["signals"] += 1
        if signal.action != "buy":
            if signal.reason:
                record_skip(conn, deployment_id, signal.reason, now, market_id=candidate.market_id, asset_id=candidate.asset_id)
                result["skips"] += 1
            continue

        signal.size = float(cfg.get("paper_order_size", 10.0))
        signal.candidate = candidate
        risk = check_entry_risk(
            signal=signal,
            portfolio=_portfolio_from_positions(positions),
            config=_risk_config(cfg),
            now=now,
        )
        if not risk.ok:
            record_skip(conn, deployment_id, risk.reason, now, market_id=candidate.market_id, asset_id=candidate.asset_id)
            result["skips"] += 1
            continue

        approval_mode = str(cfg.get("approval_mode", "manual_approval"))
        if approval_mode != "auto_paper":
            expires_at = _proposal_expires_at(now, int(cfg.get("proposal_ttl_sec", 60)))
            proposal_id = record_trade_proposal(
                conn,
                deployment_id,
                strategy_id,
                candidate.market_id,
                candidate.condition_id,
                signal,
                signal.size,
                now,
                expires_at,
            )
            record_audit_event(
                conn,
                deployment_id,
                strategy_id,
                "runner",
                "polymarket_runner",
                "proposal_created",
                "proposal",
                proposal_id,
                {},
                {
                    "status": "proposed",
                    "proposal_id": proposal_id,
                    "asset_id": signal.asset_id,
                    "side": signal.action,
                    "price": signal.entry_price,
                    "size": signal.size,
                    "expires_at": expires_at,
                },
                "success",
                signal.reason,
                "",
                now,
            )
            result["proposals"] += 1
            continue

        fill = simulate_entry_fill(signal, book)
        if not fill.ok:
            record_skip(conn, deployment_id, fill.reason, now, market_id=candidate.market_id, asset_id=candidate.asset_id)
            result["skips"] += 1
            continue
        position = apply_fill_to_position(positions.get(candidate.asset_id), fill)
        if position is not None:
            positions[candidate.asset_id] = position
            upsert_position(conn, deployment_id, position, now)
        record_trade(conn, deployment_id, fill, now)
        result["fills"] += 1


def _is_poly_alpha_paper_proposal(proposal: dict) -> bool:
    features = proposal.get("features") or {}
    return features.get("source") == "poly_alpha" and features.get("paper_only") is True


def _process_approved_proposals(conn, deployment_id, positions, books, source, cfg, now, result) -> None:
    approved = [
        proposal
        for proposal in list_trade_proposals(conn, deployment_id)
        if proposal["status"] == "approved"
    ]
    for proposal in approved:
        if _is_poly_alpha_paper_proposal(proposal):
            # Poly Alpha proposals are finalized through poly_alpha_promotion bridge to preserve lineage.
            continue
        if _is_expired(proposal.get("expires_at"), now):
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "expired",
                now,
                action="proposal_expired",
                result="failed",
                reason="proposal_expired",
            )
            continue

        asset_id = proposal.get("asset_id") or ""
        book_payload = books.get(asset_id)
        if not book_payload and source is not None:
            book_payload = source.fetch_clob_order_book(asset_id)
            books[asset_id] = book_payload
        if not book_payload:
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "failed",
                now,
                action="error",
                result="failed",
                reason="missing_orderbook",
            )
            continue
        if _is_stale(book_payload, now, int(cfg.get("freshness_ttl_sec", 30))):
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "failed",
                now,
                action="error",
                result="failed",
                reason="stale_orderbook",
            )
            continue

        book = _book_from_payload(book_payload)
        signal = SignalDecision(
            asset_id=asset_id,
            action=proposal.get("side") or "buy",
            entry_price=book.best_ask,
            estimated_probability=proposal.get("estimated_probability"),
            edge=float(proposal.get("edge") or 0.0),
            confidence=float(proposal.get("confidence") or 0.0),
            reason=proposal.get("reason") or "manual approval",
            features=proposal.get("features") or {},
        )
        signal.size = float(proposal.get("size") or 0.0)
        risk = check_entry_risk(
            signal=signal,
            portfolio=_portfolio_from_positions(positions),
            config=_risk_config(cfg),
            now=now,
        )
        if not risk.ok:
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "failed",
                now,
                action="error",
                result="failed",
                reason=risk.reason,
            )
            continue

        fill = simulate_entry_fill(signal, book)
        if not fill.ok:
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "failed",
                now,
                action="error",
                result="failed",
                reason=fill.reason,
            )
            continue
        if not _claim_proposal(conn, deployment_id, proposal):
            continue
        position = apply_fill_to_position(positions.get(asset_id), fill)
        if position is not None:
            positions[asset_id] = position
            upsert_position(conn, deployment_id, position, now)
        trade_id = record_trade(conn, deployment_id, fill, now)
        if not _transition_proposal(
            conn,
            deployment_id,
            proposal,
            "filled",
            now,
            action="fill_simulated",
            result="success",
            reason=proposal.get("decision_reason") or "manual approval",
            fill_trade_id=trade_id,
        ):
            raise RuntimeError("proposal_transition_conflict")
        result["fills"] += 1


def _expire_proposed_proposals(conn, deployment_id, now) -> None:
    for proposal in list_trade_proposals(conn, deployment_id):
        if proposal["status"] == "proposed" and _is_expired(proposal.get("expires_at"), now):
            _transition_proposal(
                conn,
                deployment_id,
                proposal,
                "expired",
                now,
                action="proposal_expired",
                result="failed",
                reason="proposal_expired",
            )


def _claim_proposal(conn, deployment_id, proposal) -> bool:
    return update_trade_proposal_status(
        conn,
        proposal["proposal_id"],
        proposal["status"],
        proposal.get("decided_by") or "polymarket_runner",
        proposal.get("decided_at") or "",
        proposal.get("decision_reason") or "",
        deployment_id=deployment_id,
        expected_status=proposal["status"],
    )


def _transition_proposal(
    conn,
    deployment_id,
    proposal,
    status,
    now,
    *,
    action,
    result,
    reason,
    fill_trade_id: str | None = None,
) -> bool:
    after = dict(proposal)
    after["status"] = status
    if fill_trade_id:
        after["fill_trade_id"] = fill_trade_id
    updated = update_trade_proposal_status(
        conn,
        proposal["proposal_id"],
        status,
        proposal.get("decided_by") or "polymarket_runner",
        proposal.get("decided_at") or now,
        proposal.get("decision_reason") or reason,
        fill_trade_id=fill_trade_id,
        deployment_id=deployment_id,
        expected_status=proposal["status"],
    )
    if not updated:
        return False
    record_audit_event(
        conn,
        deployment_id,
        proposal.get("strategy_id") or "",
        "runner",
        "polymarket_runner",
        action,
        "proposal",
        proposal["proposal_id"],
        proposal,
        after,
        result,
        reason,
        "",
        now,
    )
    return True


def _signal_for_candidate(candidate, book, overrides, cfg) -> SignalDecision:
    override = overrides.get(candidate.asset_id)
    if override and override.get("action") != "exit":
        return SignalDecision(
            asset_id=candidate.asset_id,
            action=override.get("action", "skip"),
            reason=override.get("reason", ""),
            entry_price=book.best_ask,
        )
    return compute_edge_signal(candidate, book, cfg)


def _load_bot_config(conn: sqlite3.Connection, strategy_id: str) -> dict:
    if not _table_exists(conn, "algo_strategies"):
        return default_bot_config()
    columns = _columns(conn, "algo_strategies")
    if "bot_config" not in columns:
        return default_bot_config()
    row = conn.execute("SELECT bot_config FROM algo_strategies WHERE id = ?", (strategy_id,)).fetchone()
    if not row:
        return default_bot_config()
    try:
        overrides = json.loads(row[0] or "{}")
    except json.JSONDecodeError:
        overrides = {}
    return default_bot_config(overrides)


def _book_from_payload(payload: dict) -> OrderBook:
    return OrderBook.from_clob(
        payload.get("data", {}),
        source_api=payload.get("source_api", ""),
        fetched_at=payload.get("fetched_at", ""),
    )


def _is_stale(payload: dict, now: str, ttl_sec: int) -> bool:
    fetched_at = payload.get("fetched_at")
    if not fetched_at:
        return True
    fetched_dt = _parse_utc(fetched_at)
    now_dt = _parse_utc(now)
    if fetched_dt is None or now_dt is None:
        return True
    return (now_dt - fetched_dt).total_seconds() > ttl_sec


def _is_expired(expires_at: str | None, now: str) -> bool:
    if not expires_at:
        return False
    expires_dt = _parse_utc(expires_at)
    now_dt = _parse_utc(now)
    return expires_dt is not None and now_dt is not None and expires_dt <= now_dt


def _proposal_expires_at(now: str, ttl_sec: int) -> str:
    parsed = _parse_utc(now)
    if parsed is None:
        return now
    return (parsed + timedelta(seconds=ttl_sec)).isoformat().replace("+00:00", "Z")


def _portfolio_from_positions(positions: dict) -> PortfolioState:
    exposure = sum(position.size * position.avg_price for position in positions.values())
    return PortfolioState(positions=positions, total_exposure=exposure)


def _risk_config(cfg: dict) -> RiskConfig:
    names = {field.name for field in fields(RiskConfig)}
    return RiskConfig(**{name: cfg[name] for name in names if name in cfg})


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _seed_smoke_strategy(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS algo_strategies (
            id TEXT PRIMARY KEY,
            market_type TEXT DEFAULT 'polymarket',
            bot_config TEXT DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO algo_strategies (id, market_type, bot_config)
        VALUES (?, 'polymarket', ?)
        """,
        ("smoke-strategy", json.dumps({"approval_mode": "auto_paper", "max_candidates": 1, "min_edge": 0.01})),
    )
    conn.commit()
    conn.close()


def _run_smoke(args) -> dict:
    fixture_dir = Path(args.fixture_dir)
    _seed_smoke_strategy(args.db)
    return run_polymarket_cycle(
        db_path=args.db,
        deployment_id="smoke-deployment",
        strategy_id="smoke-strategy",
        market_payload=load_fixture(fixture_dir / "polymarket_gamma_markets.json"),
        order_books={"yes-token-1": load_fixture(fixture_dir / "polymarket_clob_book_yes.json")},
        now="2026-04-30T00:00:00Z",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket paper bot runner")
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("smoke", help="Run one fixture-backed paper cycle")
    smoke.add_argument("--fixture-dir", required=True)
    smoke.add_argument("--db", required=True)
    args = parser.parse_args()

    if args.command == "smoke":
        print(json.dumps(_run_smoke(args)))


if __name__ == "__main__":
    main()
