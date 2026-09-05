"""Report writer.

Will use Gemini to turn structured ReviewResult into a human-readable
narrative report for the claims investigator.
NOT implemented in Milestone 1.
"""

from src.models import ReviewResult


class ReportWriter:
    """Generates a readable review report from structured findings."""

    def write_report(self, result: ReviewResult) -> str:
        """Turn a ReviewResult into a narrative report.

        Raises:
            NotImplementedError: Always, until Milestone 7.
        """
        raise NotImplementedError(
            "Report generation requires Gemini integration (Milestone 7)."
        )
