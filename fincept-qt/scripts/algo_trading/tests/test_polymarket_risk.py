import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_models import MarketCandidate, RiskConfig, SignalDecision
from polymarket_risk import PortfolioState, RecentTrade, check_entry_risk


NOW = "2026-04-30T00:00:00Z"


def buy_signal(price=0.50, size=10, hours_to_expiry=48):
    signal = SignalDecision(
        asset_id="yes-token-1",
        action="buy",
        entry_price=price,
        estimated_probability=0.60,
        edge=0.10,
        confidence=0.80,
    )
    signal.size = size
    signal.candidate = MarketCandidate(
        market_id="market-1",
        condition_id="condition-1",
        outcome="Yes",
        asset_id="yes-token-1",
        price=price,
        hours_to_expiry=hours_to_expiry,
    )
    return signal


def empty_portfolio():
    return PortfolioState()


def portfolio_with_recent_trade():
    return PortfolioState(
        recent_trades=[
            RecentTrade(
                asset_id="yes-token-1",
                action="buy",
                created_at="2026-04-29T23:55:00Z",
            )
        ]
    )


def test_risk_rejects_order_above_max_usdc():
    cfg = RiskConfig(max_order_usdc=25)

    result = check_entry_risk(signal=buy_signal(price=0.50, size=100), portfolio=empty_portfolio(), config=cfg, now=NOW)

    assert not result.ok
    assert result.reason == "max_order_usdc"


def test_risk_rejects_cooldown_same_market_direction():
    result = check_entry_risk(
        signal=buy_signal(),
        portfolio=portfolio_with_recent_trade(),
        config=RiskConfig(cooldown_minutes=10),
        now=NOW,
    )

    assert not result.ok
    assert result.reason == "cooldown"


def test_risk_rejects_near_expiry_candidate():
    result = check_entry_risk(
        signal=buy_signal(hours_to_expiry=2),
        portfolio=empty_portfolio(),
        config=RiskConfig(min_time_to_expiry_hours=24),
        now=NOW,
    )

    assert not result.ok
    assert result.reason == "near_expiry"


def test_risk_accepts_valid_entry():
    result = check_entry_risk(signal=buy_signal(price=0.50, size=10), portfolio=empty_portfolio(), config=RiskConfig(), now=NOW)

    assert result.ok
    assert result.reason == ""
