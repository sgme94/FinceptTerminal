import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_config import default_bot_config


def test_default_bot_config_contains_required_controls():
    cfg = default_bot_config()

    assert cfg["strategy_mode"] == "auto_scan"
    assert cfg["sort_by"] == "volume"
    assert cfg["min_time_to_expiry_hours"] == 24
    assert cfg["freshness_ttl_sec"] == 30
    assert cfg["approval_mode"] == "manual_approval"
    assert cfg["proposal_ttl_sec"] == 60
    assert cfg["stop_loss_pct"] == 30.0
    assert cfg["take_profit_pct"] == 50.0
    assert "momentum_weight" in cfg


def test_default_bot_config_overrides_do_not_mutate_defaults():
    cfg = default_bot_config({"max_candidates": 3, "sort_by": "liquidity"})

    assert cfg["max_candidates"] == 3
    assert cfg["sort_by"] == "liquidity"
    assert default_bot_config()["max_candidates"] == 20
    assert default_bot_config()["sort_by"] == "volume"
