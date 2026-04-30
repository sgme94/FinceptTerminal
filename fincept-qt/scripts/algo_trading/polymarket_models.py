from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrderLevel:
    price: float
    size: float

    @classmethod
    def from_clob(cls, raw: dict) -> "OrderLevel":
        return cls(price=float(raw["price"]), size=float(raw["size"]))


@dataclass
class OrderBook:
    asset_id: str
    bids: list[OrderLevel]
    asks: list[OrderLevel]
    source_api: str
    fetched_at: str

    @classmethod
    def from_clob(cls, raw: dict, *, source_api: str, fetched_at: str) -> "OrderBook":
        bids = sorted(
            [OrderLevel.from_clob(level) for level in raw.get("bids", [])],
            key=lambda level: level.price,
            reverse=True,
        )
        asks = sorted(
            [OrderLevel.from_clob(level) for level in raw.get("asks", [])],
            key=lambda level: level.price,
        )
        return cls(
            asset_id=str(raw.get("asset_id") or raw.get("token_id") or ""),
            bids=bids,
            asks=asks,
            source_api=source_api,
            fetched_at=fetched_at,
        )

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def bid_depth(self) -> float:
        return sum(level.size for level in self.bids)

    @property
    def ask_depth(self) -> float:
        return sum(level.size for level in self.asks)


@dataclass
class MarketCandidate:
    market_id: str = ""
    condition_id: str = ""
    question: str = ""
    outcome: str = ""
    asset_id: str = ""
    price: float = 0.0
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    fetched_at: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    momentum: float = 0.0
    volatility: float = 0.0
    hours_to_expiry: float | None = None


@dataclass
class SignalDecision:
    asset_id: str = ""
    action: str = "skip"
    entry_price: float | None = None
    estimated_probability: float | None = None
    edge: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    features: dict = field(default_factory=dict)


@dataclass
class RiskConfig:
    max_order_usdc: float = 25.0
    max_total_exposure: float = 100.0
    daily_loss_limit: float = 25.0
    max_positions: int = 5
    cooldown_minutes: int = 10
    min_time_to_expiry_hours: float = 24.0
    max_spread: float = 0.05
    min_depth: float = 10.0
    min_price: float = 0.05
    max_price: float = 0.95


@dataclass
class PaperFill:
    asset_id: str
    side: str
    price: float
    size: float
    ok: bool = True
    reason: str = ""
    realized_pnl: float = 0.0

    @property
    def notional(self) -> float:
        return self.price * self.size


@dataclass
class PaperPosition:
    asset_id: str
    size: float
    avg_price: float
    realized_pnl: float = 0.0
    max_price_seen: float | None = None

    def market_value(self, price: float) -> float:
        return self.size * price
