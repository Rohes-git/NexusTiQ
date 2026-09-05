"""Policy retriever.

Will retrieve relevant policy clauses based on claim facts.
NOT implemented in Milestone 1.
"""

from src.models import PolicyClause, ClaimFacts


class PolicyRetriever:
    """Retrieves relevant policy clauses for a given claim."""

    def retrieve_clauses(self, facts: ClaimFacts) -> list[PolicyClause]:
        """Find policy clauses relevant to the extracted claim facts.

        Raises:
            NotImplementedError: Always, until Milestone 4.
        """
        raise NotImplementedError(
            "Policy retrieval will be implemented in Milestone 4."
        )
