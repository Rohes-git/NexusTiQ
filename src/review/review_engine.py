"""Review engine — orchestrates the full claim review pipeline.

Pipeline (future):
    document extraction → policy retrieval → deterministic rules
    → contradiction detection → evidence aggregation → recommendation

Returns a placeholder ReviewResult in Milestone 1.
"""

from src.models import Claim, ReviewResult, Recommendation


class ReviewEngine:
    """Orchestrates the end-to-end claim evidence review."""

    def review(self, claim: Claim) -> ReviewResult:
        """Run the full review pipeline on a claim.

        Returns a placeholder result in Milestone 1.
        """
        return ReviewResult(
            recommendation=Recommendation.NEED_MORE_INFO,
            findings=[],
            contradictions=[],
            missing_information=[
                "Review engine not yet connected — Milestone 1 placeholder."
            ],
            escalation_required=False,
            summary="Review engine will be connected in the next milestone.",
        )
