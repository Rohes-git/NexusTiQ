"""Recommendation logic.

Aggregates findings from coverage, document, and consistency checks
to produce a final recommendation (approve / deny / escalate / need more info).
NOT implemented in Milestone 1.
"""

from src.models import Finding, Recommendation


def compute_recommendation(findings: list[Finding]) -> Recommendation:
    """Derive a recommendation from the aggregated findings.

    Raises:
        NotImplementedError: Always, until Milestone 5.
    """
    raise NotImplementedError(
        "Recommendation logic will be implemented in Milestone 5."
    )
