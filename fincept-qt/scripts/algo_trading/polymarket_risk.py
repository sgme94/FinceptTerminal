from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from polymarket_models import RiskConfig, SignalDecision


@dataclass
class RiskResult:
    ok: bool
    reason: str = ""


@dataclass
class RecentTrade:
    asset_id: str
    action: str
    created_at: str


@dataclass
class PortfolioState:
    positions: dict = field(default_factory=dict)
    recent_trades: list[RecentTrade] = field(default_factory=list)
    total_exposure: float = 0.0
    daily_realized_pnl: float = 0.0


def check_entry_risk(signal: SignalDecision, portfolio: PortfolioState, config: RiskConfig, now: str) -> RiskResult:
    price = signal.entry_price or 0.0
    size = float(getattr(signal, "size", 0.0) or 0.0)
    notional = price * size

    if notional > config.max_order_usdc:
        return RiskResult(False, "max_order_usdc")
    if portfolio.total_exposure + notional > config.max_total_exposure:
        return RiskResult(False, "max_total_exposure")
    if abs(min(portfolio.daily_realized_pnl, 0.0)) >= config.daily_loss_limit:
        return RiskResult(False, "daily_loss_limit")
    if len(portfolio.positions) >= config.max_positions and signal.asset_id not in portfolio.positions:
        return RiskResult(False, "max_positions")

    candidate = getattr(signal, "candidate", None)
    hours_to_expiry = getattr(candidate, "hours_to_expiry", None)
    if hours_to_expiry is not None and hours_to_expiry < config.min_time_to_expiry_hours:
        return RiskResult(False, "near_expiry")

    if _within_cooldown(signal, portfolio, config, now):
        return RiskResult(False, "cooldown")

    return RiskResult(True)


def _within_cooldown(signal: SignalDecision, portfolio: PortfolioState, config: RiskConfig, now: str) -> bool:
    now_dt = _parse_utc(now)
    if now_dt is None:
        return False

    for trade in portfolio.recent_trades:
        if trade.asset_id != signal.asset_id or trade.action != signal.action:
            continue
        trade_dt = _parse_utc(trade.created_at)
        if trade_dt is None:
            continue
        elapsed_minutes = (now_dt - trade_dt).total_seconds() / 60.0
        if 0 <= elapsed_minutes < config.cooldown_minutes:
            return True
    return False


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
