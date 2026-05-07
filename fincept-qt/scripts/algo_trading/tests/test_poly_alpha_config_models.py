import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_config import default_poly_alpha_config
from poly_alpha_models import apply_opportunity_transition


def test_default_config_has_phase_1_gate_values():
    cfg = default_poly_alpha_config()

    assert cfg["validation_freshness_window_sec"] == 300
    assert cfg["min_exploration_samples"] == 10
    assert cfg["min_promotion_samples"] == 30
    assert cfg["min_promotion_history_days"] == 90
    assert cfg["max_drawdown_threshold"] == -0.20
    assert cfg["min_hit_rate"] == 0.52
    assert cfg["min_payoff_ratio"] == 1.10
    assert cfg["min_capacity_multiple"] == 2.0


def test_default_config_overrides_do_not_mutate_defaults():
    cfg = default_poly_alpha_config({"min_promotion_samples": 40})

    assert cfg["min_promotion_samples"] == 40
    assert default_poly_alpha_config()["min_promotion_samples"] == 30


def test_promotion_watch_keeps_validated_status():
    state = apply_opportunity_transition("promotion_watch")

    assert state.opportunity_status == "validated"
    assert state.shadow_signal_status == "validated"
    assert state.promotion_decision == "watch"


def test_post_approval_skip_is_first_class():
    state = apply_opportunity_transition("paper_fill_skipped")

    assert state.opportunity_status == "skipped"
    assert state.shadow_signal_status == "promoted"
    assert state.promotion_decision == "promote"


@pytest.mark.parametrize(
    ("event", "opportunity_status", "shadow_signal_status", "promotion_decision"),
    [
        ("scanner_ignore", None, None, None),
        ("opportunity_discovered", "watch", None, None),
        ("exploration_pass", "watch", None, None),
        ("exploration_watch", "watch", None, None),
        ("exploration_reject", "rejected", None, None),
        ("shadow_signal_created", "shadow", "shadow", None),
        ("validation_pass", "validated", "validated", None),
        ("validation_fail", "rejected", "rejected", None),
        ("promotion_watch", "validated", "validated", "watch"),
        ("promotion_reject", "rejected", "rejected", "reject"),
        ("promotion_promote", "promoted", "promoted", "promote"),
        ("proposal_created", "proposed", "promoted", "promote"),
        ("proposal_rejected", "rejected", "promoted", "promote"),
        ("proposal_approved", "approved", "promoted", "promote"),
        ("paper_fill_skipped", "skipped", "promoted", "promote"),
        ("paper_fill_recorded", "filled", "promoted", "promote"),
        ("signal_ttl_expired", "expired", "expired", None),
        ("proposal_ttl_expired", "expired", "promoted", "promote"),
    ],
)
def test_lifecycle_transition_table(
    event,
    opportunity_status,
    shadow_signal_status,
    promotion_decision,
):
    state = apply_opportunity_transition(event)

    assert state.opportunity_status == opportunity_status
    assert state.shadow_signal_status == shadow_signal_status
    assert state.promotion_decision == promotion_decision


def test_proposal_ttl_expired_does_not_expire_promoted_signal_state():
    state = apply_opportunity_transition(
        "proposal_ttl_expired",
        previous_shadow_signal_status="promoted",
        previous_promotion_decision="promote",
    )

    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status == "promoted"
    assert state.promotion_decision == "promote"


def test_signal_ttl_expired_preserves_existing_promotion_decision():
    state = apply_opportunity_transition(
        "signal_ttl_expired",
        previous_shadow_signal_status="promoted",
        previous_promotion_decision="promote",
    )

    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status == "expired"
    assert state.promotion_decision == "promote"


def test_watch_opportunity_ttl_expired_preserves_missing_signal_state():
    state = apply_opportunity_transition(
        "opportunity_ttl_expired",
        previous_shadow_signal_status=None,
        previous_promotion_decision=None,
    )

    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status is None
    assert state.promotion_decision is None


def test_opportunity_ttl_expired_preserves_existing_signal_and_promotion_state():
    state = apply_opportunity_transition(
        "opportunity_ttl_expired",
        previous_shadow_signal_status="validated",
        previous_promotion_decision="watch",
    )

    assert state.opportunity_status == "expired"
    assert state.shadow_signal_status == "validated"
    assert state.promotion_decision == "watch"
