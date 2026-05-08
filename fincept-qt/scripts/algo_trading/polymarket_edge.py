from __future__ import annotations

from polymarket_config import default_bot_config
from polymarket_models import MarketCandidate, OrderBook, SignalDecision


def compute_edge_signal(candidate: MarketCandidate, book: OrderBook | None, config: dict) -> SignalDecision:
    cfg = default_bot_config(config)
    if book is None or book.best_ask is None or book.best_bid is None:
        return SignalDecision(asset_id=candidate.asset_id, action="skip", reason="missing_orderbook")

    entry_price = book.best_ask
    spread = book.spread or 0.0
    total_depth = book.bid_depth + book.ask_depth
    imbalance = 0.0 if total_depth <= 0 else (book.bid_depth - book.ask_depth) / total_depth

    features = {
        "base_price": _clamp(candidate.price, 0.01, 0.99),
        "momentum": _clamp(candidate.momentum, -0.20, 0.20) * float(cfg["momentum_weight"]),
        "imbalance": _clamp(imbalance, -1.0, 1.0) * float(cfg["imbalance_weight"]),
        "liquidity": min(total_depth / 400.0, 1.0) * float(cfg["liquidity_weight"]),
        "spread_penalty": -spread * float(cfg["spread_penalty"]),
        "volatility_penalty": -max(candidate.volatility, 0.0) * float(cfg["volatility_penalty"]),
    }
    estimated_probability = _clamp(sum(features.values()), 0.01, 0.99)
    edge = estimated_probability - entry_price
    confidence = _clamp(0.50 + abs(edge) * 2.0 + max(features["liquidity"], 0.0), 0.0, 0.99)

    if confidence < float(cfg["confidence_threshold"]):
        return SignalDecision(
            asset_id=candidate.asset_id,
            action="skip",
            entry_price=entry_price,
            estimated_probability=estimated_probability,
            edge=edge,
            confidence=confidence,
            reason="low_confidence",
            features=features,
        )

    if edge < float(cfg["min_edge"]):
        return SignalDecision(
            asset_id=candidate.asset_id,
            action="skip",
            entry_price=entry_price,
            estimated_probability=estimated_probability,
            edge=edge,
            confidence=confidence,
            reason="min_edge",
            features=features,
        )

    return SignalDecision(
        asset_id=candidate.asset_id,
        action="buy",
        entry_price=entry_price,
        estimated_probability=estimated_probability,
        edge=edge,
        confidence=confidence,
        features=features,
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
