"""Coverage evaluation rules.

Deterministic checks: does the policy cover the claimed incident type,
vehicle category, and claimed amount?
NOT implemented in Milestone 1.
"""

from src.models import ClaimFacts, PolicyClause, Finding


def evaluate_coverage(facts: ClaimFacts, clauses: list[PolicyClause]) -> list[Finding]:
    """Check whether the policy covers the claimed incident.

    Raises:
        NotImplementedError: Always, until Milestone 5.
    """
    raise NotImplementedError(
        "Coverage evaluation will be implemented in Milestone 5."
    )
