import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_edge import compute_edge_signal
from polymarket_models import MarketCandidate, OrderBook, OrderLevel


def make_candidate(outcome="Yes", price=0.40, momentum=0.0, volatility=0.0):
    return MarketCandidate(
        market_id="market-1",
        condition_id="condition-1",
        question="Will it happen?",
        outcome=outcome,
        asset_id="yes-token-1",
        price=price,
        volume=2500.0,
        liquidity=1200.0,
        end_date="2026-05-10T00:00:00Z",
        fetched_at="2026-04-30T00:00:00Z",
        momentum=momentum,
        volatility=volatility,
    )


def make_book(best_bid=0.39, best_ask=0.42, bid_depth=200, ask_depth=200):
    return OrderBook(
        asset_id="yes-token-1",
        bids=[OrderLevel(price=best_bid, size=bid_depth)],
        asks=[OrderLevel(price=best_ask, size=ask_depth)],
        source_api="https://clob.polymarket.com",
        fetched_at="2026-04-30T00:00:00Z",
    )


def test_edge_uses_best_ask_for_buyable_yes_signal():
    candidate = make_candidate(outcome="Yes", price=0.40)
    book = make_book(best_bid=0.39, best_ask=0.42, bid_depth=200, ask_depth=200)

    decision = compute_edge_signal(
        candidate,
        book,
        {"min_edge": 0.04, "momentum_weight": 0.2, "imbalance_weight": 0.2},
    )

    assert decision.action == "buy"
    assert decision.estimated_probability > 0.42
    assert decision.edge == pytest.approx(decision.estimated_probability - 0.42)
    assert decision.entry_price == 0.42


def test_edge_rejects_insufficient_inputs():
    decision = compute_edge_signal(make_candidate(), None, {"min_edge": 0.04})

    assert decision.action == "skip"
    assert decision.reason == "missing_orderbook"


def test_edge_applies_weighted_spread_and_volatility_penalties():
    decision = compute_edge_signal(
        make_candidate(outcome="Yes", price=0.40, momentum=0.03, volatility=0.20),
        make_book(best_bid=0.35, best_ask=0.45, bid_depth=50, ask_depth=50),
        {"spread_penalty": 0.5, "volatility_penalty": 0.5},
    )

    assert decision.features["spread_penalty"] < 0
    assert decision.features["volatility_penalty"] < 0
