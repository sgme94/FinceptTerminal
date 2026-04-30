import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_models import (
    MarketCandidate,
    OrderBook,
    PaperFill,
    PaperPosition,
    RiskConfig,
    SignalDecision,
)
from polymarket_scanner import scan_markets
from polymarket_sources import load_fixture


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def gamma_fixture():
    return load_fixture(FIXTURE_DIR / "polymarket_gamma_markets.json")


def test_order_book_best_prices_parse_string_numbers():
    book = OrderBook.from_clob(
        {
            "asset_id": "123",
            "bids": [{"price": "0.41", "size": "100"}],
            "asks": [{"price": "0.43", "size": "80"}],
        },
        source_api="https://clob.polymarket.com",
        fetched_at="2026-04-30T00:00:00Z",
    )

    assert book.best_bid == 0.41
    assert book.best_ask == 0.43
    assert book.spread == pytest.approx(0.02)
    assert book.bid_depth == 100.0
    assert book.ask_depth == 80.0


def test_order_book_handles_empty_sides():
    book = OrderBook.from_clob(
        {"asset_id": "123", "bids": [], "asks": []},
        source_api="https://clob.polymarket.com",
        fetched_at="2026-04-30T00:00:00Z",
    )

    assert book.best_bid is None
    assert book.best_ask is None
    assert book.spread is None


def test_polymarket_model_defaults_are_constructible():
    candidate = MarketCandidate(
        market_id="market-1",
        condition_id="condition-1",
        question="Will it happen?",
        outcome="Yes",
        asset_id="yes-token-1",
        price=0.42,
        volume=2500.0,
        liquidity=1200.0,
        end_date="2026-05-10T00:00:00Z",
        fetched_at="2026-04-30T00:00:00Z",
    )
    signal = SignalDecision(
        asset_id="yes-token-1",
        action="buy",
        entry_price=0.42,
        estimated_probability=0.50,
        edge=0.08,
        confidence=0.70,
    )
    fill = PaperFill(asset_id="yes-token-1", side="BUY", price=0.42, size=10.0)
    position = PaperPosition(asset_id="yes-token-1", size=10.0, avg_price=0.42)

    assert candidate.outcome == "Yes"
    assert signal.features == {}
    assert RiskConfig(max_order_usdc=25).max_order_usdc == 25
    assert fill.notional == pytest.approx(4.2)
    assert position.market_value(0.55) == pytest.approx(5.5)


def test_scanner_filters_closed_low_liquidity_tags_and_expiry(gamma_fixture):
    result = scan_markets(
        gamma_fixture["data"],
        config={
            "min_volume": 1000,
            "min_liquidity": 500,
            "min_price": 0.05,
            "max_price": 0.95,
            "excluded_tags": ["sports"],
            "min_time_to_expiry_hours": 24,
            "sort_by": "volume",
        },
        fetched_at=gamma_fixture["fetched_at"],
    )

    assert [c.asset_id for c in result.candidates] == ["yes-token-1", "no-token-1"]
    assert any(s.reason == "closed" for s in result.skipped)
    assert any(s.reason == "low_liquidity" for s in result.skipped)
    assert any(s.reason == "excluded_tag" for s in result.skipped)
    assert any(s.reason == "near_expiry" for s in result.skipped)
