"""Clause grounding layer for policy retrieval.

Associates retrieved clauses with factual, deterministic grounding reasons
without making coverage determinations, approval decisions, or fraud findings.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.retrieval.vector_index import RetrievedClause


# Deterministic factual descriptions mapped to policy clause IDs
CLAUSE_FACTUAL_REASONS: dict[str, str] = {
    "1.1": "Relevant to policy period validity and incident date verification.",
    "1.2": "Relevant to covered vehicle identification and registration verification.",
    "2.1": "Relevant to accidental damage, collision, and external impact coverage.",
    "2.2": "Relevant to repair estimate requirements and reasonable repair cost settlement.",
    "3.1": "Relevant to vehicle theft loss coverage and conditions.",
    "3.2": "Relevant to mandatory First Information Report (FIR) submission for theft claims.",
    "4.1": "Relevant to policy exclusions concerning deliberate or intentional damage.",
    "4.2": "Relevant to policy exclusions concerning unauthorized or commercial vehicle use.",
    "4.3": "Relevant to policy standards regarding truthful information and escalation requirements.",
    "5.1": "Relevant to Insured Declared Value (IDV) limits for total loss or theft.",
    "5.2": "Relevant to independent repair cost evaluation relative to IDV and depreciation.",
    "6.1": "Relevant to standard 7-day claim notification timeline compliance.",
    "6.2": "Relevant to investigator review procedures for notifications outside the 7-day window.",
    "7.1": "Relevant to mandatory document submission requirements for accidental damage claims.",
    "7.2": "Relevant to mandatory document submission requirements for theft claims.",
    "7.3": "Relevant to evidence quality standards and clarification of document contradictions.",
}


class GroundedClause(BaseModel):
    """A policy clause grounded to the claim with a factual relevance rationale."""
    clause_id: str = Field(..., description="Unique clause identifier e.g. '2.1'")
    section: str = Field(..., description="Section title")
    title: str = Field(..., description="Clause title")
    text: str = Field(..., description="Exact verbatim policy clause text")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    reason: str = Field(..., description="Deterministic factual explanation of relevance")


class PolicyRetrievalResponse(BaseModel):
    """API response schema for /api/retrieve-policy."""
    success: bool
    query: str = ""
    clauses: list[GroundedClause] = Field(default_factory=list)
    error: Optional[str] = None


class GroundingService:
    """Grounds retrieved clauses by attaching deterministic factual explanations."""

    @staticmethod
    def ground_clause(retrieved: RetrievedClause) -> GroundedClause:
        """Attach a deterministic factual rationale to a retrieved clause.

        Args:
            retrieved: RetrievedClause from vector index.

        Returns:
            GroundedClause with exact text, similarity score, and factual reason.
        """
        # Look up factual explanation or generate safe fallback from section/title
        reason = CLAUSE_FACTUAL_REASONS.get(
            retrieved.clause_id,
            f"Relevant to {retrieved.title.lower()} under {retrieved.section.lower()}."
        )

        return GroundedClause(
            clause_id=retrieved.clause_id,
            section=retrieved.section,
            title=retrieved.title,
            text=retrieved.text,
            similarity_score=retrieved.similarity_score,
            reason=reason,
        )

    @staticmethod
    def ground_results(retrieved_list: list[RetrievedClause]) -> list[GroundedClause]:
        """Ground a list of retrieved clauses."""
        return [GroundingService.ground_clause(c) for c in retrieved_list]
