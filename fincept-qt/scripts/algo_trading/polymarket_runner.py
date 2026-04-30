from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import fields
from datetime import datetime, timezone

from polymarket_config import default_bot_config
from polymarket_edge import compute_edge_signal
from polymarket_models import OrderBook, RiskConfig, SignalDecision
from polymarket_paper import apply_fill_to_position, should_exit_position, simulate_entry_fill, simulate_exit_fill
from polymarket_risk import PortfolioState, check_entry_risk
from polymarket_scanner import scan_markets
from polymarket_sources import PolymarketRestSource
from polymarket_store import (
    delete_position,
    ensure_polymarket_schema,
    load_positions,
    record_candidate,
    record_scan_skip,
    record_signal,
    record_skip,
    record_trade,
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

        positions = load_positions(conn, deployment_id)
        exited_assets = _process_exits(conn, deployment_id, positions, books, overrides, cfg, now, result)
        _process_entries(conn, deployment_id, positions, exited_assets, candidates, books, overrides, cfg, now, result)

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


def _process_entries(conn, deployment_id, positions, exited_assets, candidates, books, overrides, cfg, now, result) -> None:
    for candidate in candidates:
        if candidate.asset_id in positions:
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
