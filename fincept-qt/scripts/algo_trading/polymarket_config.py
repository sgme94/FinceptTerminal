from copy import deepcopy


DEFAULT_BOT_CONFIG = {
    "strategy_mode": "auto_scan",
    "scan_interval_sec": 60,
    "max_candidates": 20,
    "sort_by": "volume",
    "min_volume": 1000.0,
    "min_liquidity": 500.0,
    "max_spread": 0.05,
    "min_depth": 10.0,
    "min_price": 0.05,
    "max_price": 0.95,
    "excluded_categories": [],
    "excluded_tags": [],
    "min_time_to_expiry_hours": 24,
    "freshness_ttl_sec": 30,
    "min_edge": 0.04,
    "confidence_threshold": 0.55,
    "momentum_weight": 0.20,
    "volatility_penalty": 0.15,
    "imbalance_weight": 0.20,
    "liquidity_weight": 0.10,
    "spread_penalty": 0.20,
    "paper_order_size": 10.0,
    "max_order_usdc": 25.0,
    "max_total_exposure": 100.0,
    "daily_loss_limit": 25.0,
    "max_positions": 5,
    "cooldown_minutes": 10,
    "stop_loss_pct": 30.0,
    "take_profit_pct": 50.0,
    "trailing_stop_pct": 0.0,
}


def default_bot_config(overrides: dict | None = None) -> dict:
    cfg = deepcopy(DEFAULT_BOT_CONFIG)
    if overrides:
        cfg.update(overrides)
    return cfg
