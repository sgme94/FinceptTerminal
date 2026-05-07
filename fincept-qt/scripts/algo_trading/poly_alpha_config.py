from copy import deepcopy


DEFAULT_POLY_ALPHA_CONFIG = {
    "config_version": "poly_alpha_phase_1",
    "validation_freshness_window_sec": 300,
    "min_exploration_samples": 10,
    "min_promotion_samples": 30,
    "min_promotion_history_days": 90,
    "max_drawdown_threshold": -0.20,
    "min_hit_rate": 0.52,
    "min_payoff_ratio": 1.10,
    "min_capacity_multiple": 2.0,
}


def default_poly_alpha_config(overrides: dict | None = None) -> dict:
    cfg = deepcopy(DEFAULT_POLY_ALPHA_CONFIG)
    if overrides:
        cfg.update(overrides)
    return cfg
