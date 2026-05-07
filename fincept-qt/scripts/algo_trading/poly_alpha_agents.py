from __future__ import annotations

from typing import Any


VALID_AGENT_ROLES = {"researcher", "critic", "risk_reviewer"}

_REQUIRED_EVIDENCE_PACK_FIELDS = (
    "evidence_pack_id",
    "document_ids",
    "opportunity_id",
    "strategy_version_id",
)


def validate_agent_finding(finding: dict[str, Any], evidence_pack: dict[str, Any]) -> None:
    _validate_evidence_pack(evidence_pack)

    agent_role = finding.get("agent_role")
    if agent_role not in VALID_AGENT_ROLES:
        raise ValueError(f"Unsupported agent_role: {agent_role}")

    evidence_pack_id = finding.get("evidence_pack_id")
    if not evidence_pack_id:
        raise ValueError("evidence_pack_id is required")
    if evidence_pack_id != evidence_pack["evidence_pack_id"]:
        raise ValueError("finding evidence_pack_id does not match evidence pack")

    for field_name in ("opportunity_id", "strategy_version_id"):
        if finding.get(field_name) != evidence_pack[field_name]:
            raise ValueError(f"finding {field_name} does not match evidence pack")

    document_ids = set(evidence_pack["document_ids"])
    _validate_document_id_subset(
        "evidence_ids",
        finding.get("evidence_ids", []),
        document_ids,
    )
    _validate_document_id_subset(
        "counter_evidence_ids",
        finding.get("counter_evidence_ids", []),
        document_ids,
    )

    for field_name in ("uncaptured_facts", "uncited_claims"):
        if finding.get(field_name):
            raise ValueError(f"{field_name} must be empty")


def build_mock_agent_findings(
    evidence_pack: dict[str, Any],
    market_probability: float,
    estimated_probability: float,
) -> list[dict[str, Any]]:
    _validate_evidence_pack(evidence_pack)

    edge = estimated_probability - market_probability
    document_ids = list(evidence_pack["document_ids"])
    primary_evidence_ids = document_ids[:1]
    counter_evidence_ids = document_ids[1:2]
    run_scope = evidence_pack.get("run_id") or "no-run"

    common = {
        "run_id": evidence_pack.get("run_id", ""),
        "opportunity_id": evidence_pack["opportunity_id"],
        "evidence_pack_id": evidence_pack["evidence_pack_id"],
        "strategy_version_id": evidence_pack["strategy_version_id"],
        "estimated_probability": estimated_probability,
        "market_probability": market_probability,
        "edge": edge,
    }
    findings = [
        {
            **common,
            "finding_id": f"finding-{run_scope}-{evidence_pack['evidence_pack_id']}-researcher",
            "agent_role": "researcher",
            "confidence": 0.7,
            "recommendation": "shadow_signal" if edge > 0 else "watch",
            "thesis": "Mock researcher cites the persisted evidence pack only.",
            "evidence_ids": primary_evidence_ids,
            "counter_evidence_ids": [],
            "resolution_risks": [],
            "blockers": [],
        },
        {
            **common,
            "finding_id": f"finding-{run_scope}-{evidence_pack['evidence_pack_id']}-critic",
            "agent_role": "critic",
            "confidence": 0.55,
            "recommendation": "watch",
            "thesis": "Mock critic checks only cited pack documents for objections.",
            "evidence_ids": primary_evidence_ids,
            "counter_evidence_ids": counter_evidence_ids,
            "resolution_risks": [],
            "blockers": [],
        },
        {
            **common,
            "finding_id": f"finding-{run_scope}-{evidence_pack['evidence_pack_id']}-risk_reviewer",
            "agent_role": "risk_reviewer",
            "confidence": 0.6,
            "recommendation": "shadow_signal" if edge > 0 else "no_trade",
            "thesis": "Mock risk reviewer keeps Phase 1 paper-only.",
            "evidence_ids": primary_evidence_ids,
            "counter_evidence_ids": [],
            "resolution_risks": [],
            "blockers": [],
        },
    ]
    for finding in findings:
        validate_agent_finding(finding, evidence_pack)
    return findings


def _validate_evidence_pack(evidence_pack: dict[str, Any]) -> None:
    for field_name in _REQUIRED_EVIDENCE_PACK_FIELDS:
        if field_name not in evidence_pack:
            raise ValueError(f"evidence_pack {field_name} is required")
        if field_name != "document_ids" and not evidence_pack[field_name]:
            raise ValueError(f"evidence_pack {field_name} is required")
    if not isinstance(evidence_pack["document_ids"], list):
        raise ValueError("evidence_pack document_ids must be a list")


def _validate_document_id_subset(
    field_name: str,
    document_ids: Any,
    allowed_document_ids: set[str],
) -> None:
    if not isinstance(document_ids, list):
        raise ValueError(f"{field_name} must be a list")
    outside_pack_ids = [
        document_id
        for document_id in document_ids
        if document_id not in allowed_document_ids
    ]
    if outside_pack_ids:
        raise ValueError(
            f"{field_name} must be a subset of evidence pack document_ids: "
            f"{outside_pack_ids[0]}"
        )
