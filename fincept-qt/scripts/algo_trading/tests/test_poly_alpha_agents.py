import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from poly_alpha_agents import build_mock_agent_findings, validate_agent_finding


def _evidence_pack(**overrides):
    pack = {
        "evidence_pack_id": "pack-1",
        "document_ids": ["doc-1", "doc-2"],
        "opportunity_id": "opp-1",
        "strategy_version_id": "strat-v1",
        "run_id": "run-1",
    }
    pack.update(overrides)
    return pack


def _finding(**overrides):
    finding = {
        "run_id": "run-1",
        "opportunity_id": "opp-1",
        "evidence_pack_id": "pack-1",
        "strategy_version_id": "strat-v1",
        "agent_role": "researcher",
        "estimated_probability": 0.57,
        "market_probability": 0.42,
        "edge": 0.15,
        "confidence": 0.7,
        "recommendation": "shadow_signal",
        "thesis": "Persisted evidence supports a probability gap.",
        "evidence_ids": ["doc-1"],
        "counter_evidence_ids": [],
        "resolution_risks": [],
        "blockers": [],
    }
    finding.update(overrides)
    return finding


@pytest.mark.parametrize("agent_role", ["researcher", "critic", "risk_reviewer"])
def test_agent_findings_require_evidence_pack_id(agent_role):
    finding = _finding(agent_role=agent_role, evidence_pack_id="")

    with pytest.raises(ValueError, match="evidence_pack_id is required"):
        validate_agent_finding(finding, _evidence_pack())


@pytest.mark.parametrize(
    ("field_name", "bad_ids", "match"),
    [
        ("evidence_ids", ["doc-1", "doc-outside"], "evidence_ids"),
        ("counter_evidence_ids", ["doc-outside"], "counter_evidence_ids"),
    ],
)
def test_agent_finding_evidence_ids_must_belong_to_evidence_pack(
    field_name,
    bad_ids,
    match,
):
    finding = _finding(**{field_name: bad_ids})

    with pytest.raises(ValueError, match=match):
        validate_agent_finding(finding, _evidence_pack())


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("uncaptured_facts", ["outside pack claim"]),
        ("uncited_claims", ["claim without document id"]),
    ],
)
def test_agent_finding_rejects_uncaptured_facts(field_name, bad_value):
    finding = _finding(**{field_name: bad_value})

    with pytest.raises(ValueError, match=field_name):
        validate_agent_finding(finding, _evidence_pack())


@pytest.mark.parametrize(
    "missing_field",
    [
        "evidence_pack_id",
        "document_ids",
        "opportunity_id",
        "strategy_version_id",
    ],
)
def test_validate_agent_finding_requires_complete_evidence_pack(missing_field):
    pack = _evidence_pack()
    del pack[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        validate_agent_finding(_finding(), pack)


def test_validate_agent_finding_accepts_evidence_bounded_finding():
    validate_agent_finding(
        _finding(
            agent_role="critic",
            evidence_ids=["doc-2"],
            counter_evidence_ids=["doc-1"],
            recommendation="watch",
        ),
        _evidence_pack(),
    )


def test_phase_1_mock_adapter_builds_deterministic_evidence_bounded_findings():
    evidence_pack = _evidence_pack(document_ids=["doc-a", "doc-b"])

    first = build_mock_agent_findings(
        evidence_pack,
        market_probability=0.42,
        estimated_probability=0.57,
    )
    second = build_mock_agent_findings(
        evidence_pack,
        market_probability=0.42,
        estimated_probability=0.57,
    )

    assert first == second
    assert [finding["agent_role"] for finding in first] == [
        "researcher",
        "critic",
        "risk_reviewer",
    ]
    for finding in first:
        validate_agent_finding(finding, evidence_pack)
        assert finding["run_id"] == "run-1"
        assert finding["opportunity_id"] == "opp-1"
        assert finding["evidence_pack_id"] == "pack-1"
        assert finding["strategy_version_id"] == "strat-v1"
        assert finding["market_probability"] == pytest.approx(0.42)
        assert finding["estimated_probability"] == pytest.approx(0.57)
        assert finding["edge"] == pytest.approx(0.15)
        assert set(finding["evidence_ids"]).issubset({"doc-a", "doc-b"})
