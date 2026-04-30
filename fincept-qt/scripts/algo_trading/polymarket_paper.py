from __future__ import annotations

from polymarket_models import OrderBook, PaperFill, PaperPosition, SignalDecision


def simulate_entry_fill(signal: SignalDecision, book: OrderBook) -> PaperFill:
    size = float(getattr(signal, "size", 0.0) or 0.0)
    if not book.asks:
        return PaperFill(asset_id=signal.asset_id, side="BUY", price=0.0, size=0.0, ok=False, reason="missing_ask")

    best_ask = book.asks[0]
    if best_ask.size < size:
        return PaperFill(asset_id=signal.asset_id, side="BUY", price=best_ask.price, size=0.0, ok=False, reason="insufficient_depth")

    return PaperFill(asset_id=signal.asset_id, side="BUY", price=best_ask.price, size=size)


def simulate_exit_fill(position: PaperPosition, book: OrderBook, reason: str) -> PaperFill:
    if not book.bids:
        return PaperFill(asset_id=position.asset_id, side="SELL", price=0.0, size=0.0, ok=False, reason="missing_bid")

    best_bid = book.bids[0]
    if best_bid.size < position.size:
        return PaperFill(asset_id=position.asset_id, side="SELL", price=best_bid.price, size=0.0, ok=False, reason="insufficient_depth")

    realized_pnl = (best_bid.price - position.avg_price) * position.size
    return PaperFill(
        asset_id=position.asset_id,
        side="SELL",
        price=best_bid.price,
        size=position.size,
        reason=reason,
        realized_pnl=realized_pnl,
    )


def apply_fill_to_position(position: PaperPosition | None, fill: PaperFill) -> PaperPosition | None:
    if not fill.ok:
        return position

    if fill.side == "BUY":
        if position is None:
            return PaperPosition(asset_id=fill.asset_id, size=fill.size, avg_price=fill.price)
        new_size = position.size + fill.size
        avg_price = ((position.avg_price * position.size) + fill.notional) / new_size
        return PaperPosition(
            asset_id=position.asset_id,
            size=new_size,
            avg_price=avg_price,
            realized_pnl=position.realized_pnl,
            max_price_seen=position.max_price_seen,
        )

    if fill.side == "SELL" and position is not None:
        remaining = position.size - fill.size
        if remaining <= 0:
            return None
        return PaperPosition(
            asset_id=position.asset_id,
            size=remaining,
            avg_price=position.avg_price,
            realized_pnl=position.realized_pnl + fill.realized_pnl,
            max_price_seen=position.max_price_seen,
        )

    return position


def should_exit_position(
    position: PaperPosition,
    book: OrderBook,
    config: dict,
    signal: SignalDecision | None = None,
    market_active: bool = True,
) -> str | None:
    if not market_active:
        return "market_closed"
    if signal is not None and signal.action in {"exit", "sell"}:
        return signal.reason or "edge_reversal"
    if not book.bids:
        return None

    current_price = book.bids[0].price
    if position.avg_price <= 0:
        return None

    pnl_pct = (current_price - position.avg_price) / position.avg_price * 100.0
    if pnl_pct <= -float(config.get("stop_loss_pct", 30.0)):
        return "stop_loss"
    if pnl_pct >= float(config.get("take_profit_pct", 50.0)):
        return "take_profit"

    trailing_stop_pct = float(config.get("trailing_stop_pct", 0.0) or 0.0)
    if trailing_stop_pct > 0 and position.max_price_seen:
        drawdown_pct = (position.max_price_seen - current_price) / position.max_price_seen * 100.0
        if drawdown_pct >= trailing_stop_pct:
            return "trailing_stop"

    return None
