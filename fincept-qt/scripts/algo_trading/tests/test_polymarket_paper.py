import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_models import OrderBook, OrderLevel, PaperPosition, SignalDecision
from polymarket_paper import (
    apply_fill_to_position,
    should_exit_position,
    simulate_entry_fill,
    simulate_exit_fill,
)


def make_book(best_bid=0.40, best_ask=0.42, bid_depth=20, ask_depth=20):
    return OrderBook(
        asset_id="yes-token",
        bids=[OrderLevel(price=best_bid, size=bid_depth)] if best_bid is not None else [],
        asks=[OrderLevel(price=best_ask, size=ask_depth)] if best_ask is not None else [],
        source_api="https://clob.polymarket.com",
        fetched_at="2026-04-30T00:00:00Z",
    )


def buy_signal(size=10):
    signal = SignalDecision(
        asset_id="yes-token",
        action="buy",
        entry_price=0.42,
        estimated_probability=0.60,
        edge=0.18,
        confidence=0.80,
    )
    signal.size = size
    return signal


def test_buy_fills_at_best_ask():
    fill = simulate_entry_fill(signal=buy_signal(size=10), book=make_book(best_bid=0.40, best_ask=0.42, ask_depth=20))

    assert fill.ok
    assert fill.price == 0.42
    assert fill.size == 10
    assert fill.side == "BUY"


def test_buy_rejects_when_top_ask_depth_is_insufficient():
    fill = simulate_entry_fill(signal=buy_signal(size=10), book=make_book(best_bid=0.40, best_ask=0.42, ask_depth=5))

    assert not fill.ok
    assert fill.reason == "insufficient_depth"


def test_sell_fills_at_best_bid_and_realizes_pnl():
    pos = PaperPosition(asset_id="yes-token", size=10, avg_price=0.42)

    fill = simulate_exit_fill(pos, book=make_book(best_bid=0.55, best_ask=0.57, bid_depth=20), reason="take_profit")

    assert fill.price == 0.55
    assert fill.side == "SELL"
    assert fill.realized_pnl == pytest.approx(1.30)


def test_exit_reason_stop_loss_is_preserved():
    pos = PaperPosition(asset_id="yes-token", size=10, avg_price=0.60)

    fill = simulate_exit_fill(pos, book=make_book(best_bid=0.40, best_ask=0.42, bid_depth=20), reason="stop_loss")

    assert fill.reason == "stop_loss"
    assert fill.realized_pnl < 0


def test_apply_fill_updates_position_average_price():
    pos = apply_fill_to_position(None, simulate_entry_fill(buy_signal(size=10), make_book(best_ask=0.42)))
    updated = apply_fill_to_position(pos, simulate_entry_fill(buy_signal(size=10), make_book(best_ask=0.52)))

    assert updated.size == 20
    assert updated.avg_price == pytest.approx(0.47)


def test_should_exit_position_on_stop_loss_and_take_profit():
    pos = PaperPosition(asset_id="yes-token", size=10, avg_price=0.50)

    assert should_exit_position(pos, make_book(best_bid=0.34), {"stop_loss_pct": 30.0}) == "stop_loss"
    assert should_exit_position(pos, make_book(best_bid=0.76), {"take_profit_pct": 50.0}) == "take_profit"
