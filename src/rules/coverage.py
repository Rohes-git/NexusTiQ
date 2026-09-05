"""Coverage evaluation rules for ClaimLens (Milestone 5).

Deterministic evaluation of policy coverage conditions including coverage period,
vehicle eligibility, incident type, and IDV valuation limits.
"""

from __future__ import annotations

from typing import Any, Optional, Union
from src.models import ExtractedFact, ClaimFacts
from src.rules.policy_rules import (
    PolicyFinding,
    RuleFindingStatus,
    check_coverage_period,
    check_covered_vehicle,
    check_accident_coverage,
    check_theft_coverage,
    check_idv_valuation,
    extract_fact_dict,
)


def evaluate_coverage(
    facts: Union[list[ExtractedFact], dict[str, Any], ClaimFacts, None],
    clauses: Optional[list[Any]] = None,
) -> list[PolicyFinding]:
    """Evaluate core coverage rules against submitted claim facts.

    Args:
        facts: Claim facts in extracted or structured format.
        clauses: Optional list of policy clauses (for backward-compatibility).

    Returns:
        List of PolicyFinding objects for coverage clauses.
    """
    if isinstance(facts, ClaimFacts):
        facts = facts.model_dump()

    fact_dict, fact_objs = extract_fact_dict(facts)
    findings: list[PolicyFinding] = []

    # Clause 1.1: Coverage Period
    findings.append(check_coverage_period(fact_dict, fact_objs))

    # Clause 1.2: Covered Vehicle
    findings.append(check_covered_vehicle(fact_dict, fact_objs))

    # Clause 2.1: Accidental Damage Coverage
    findings.append(check_accident_coverage(fact_dict, fact_objs))

    # Clause 3.1: Theft Coverage
    findings.append(check_theft_coverage(fact_dict, fact_objs))

    # Clauses 5.1 & 5.2: IDV & Valuation
    findings.append(check_idv_valuation(fact_dict, fact_objs))

    return findings
