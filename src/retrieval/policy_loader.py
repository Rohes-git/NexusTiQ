"""Policy clause loader and validation for ClaimLens.

Loads the canonical synthetic motor policy from JSON, validates clause
integrity and uniqueness, and provides deterministic clause representations
and policy content hashing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "policy" / "motor_policy.json"


class PolicyClause(BaseModel):
    """Structured representation of a single motor policy clause."""
    clause_id: str = Field(..., description="Unique clause identifier e.g. '2.1'")
    section: str = Field(..., description="Section title e.g. 'SECTION 2 — ACCIDENTAL DAMAGE'")
    title: str = Field(..., description="Clause title e.g. 'Accidental Damage Coverage'")
    text: str = Field(..., description="Verbatim clause text")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class PolicyClauseLoaderError(Exception):
    """Base exception for policy loading errors."""
    pass


class PolicyNotFoundError(PolicyClauseLoaderError):
    """Raised when the policy file cannot be found."""
    pass


class InvalidPolicyError(PolicyClauseLoaderError):
    """Raised when the policy structure or content is invalid."""
    pass


class DuplicateClauseError(PolicyClauseLoaderError):
    """Raised when duplicate clause IDs are encountered."""
    pass


class PolicyClauseLoader:
    """Loads and validates policy clauses from structured JSON."""

    def __init__(self, policy_path: Optional[Path | str] = None):
        self.policy_path = Path(policy_path) if policy_path else DEFAULT_POLICY_PATH

    def load_clauses(self) -> list[PolicyClause]:
        """Load and validate all clauses from the policy JSON file.

        Returns:
            Deterministic list of validated PolicyClause objects.

        Raises:
            PolicyNotFoundError: If policy file does not exist.
            InvalidPolicyError: If JSON is malformed or missing required fields.
            DuplicateClauseError: If duplicate clause_ids exist.
        """
        if not self.policy_path.exists():
            raise PolicyNotFoundError(f"Policy file not found at: {self.policy_path}")

        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidPolicyError(f"Malformed JSON in policy file: {e}") from e
        except Exception as e:
            raise InvalidPolicyError(f"Failed to read policy file: {e}") from e

        if not isinstance(data, dict):
            raise InvalidPolicyError("Policy root must be a JSON object.")

        raw_clauses = data.get("clauses")
        if not isinstance(raw_clauses, list) or len(raw_clauses) == 0:
            raise InvalidPolicyError("Policy must contain a non-empty 'clauses' array.")

        clauses: list[PolicyClause] = []
        seen_ids: set[str] = set()

        for idx, item in enumerate(raw_clauses):
            if not isinstance(item, dict):
                raise InvalidPolicyError(f"Clause at index {idx} must be an object.")

            clause_id = str(item.get("clause_id", "")).strip()
            section = str(item.get("section", "")).strip()
            title = str(item.get("title", "")).strip()
            text = str(item.get("text", "")).strip()
            tags = item.get("tags", [])

            if not clause_id:
                raise InvalidPolicyError(f"Clause at index {idx} missing 'clause_id'.")
            if not section:
                raise InvalidPolicyError(f"Clause '{clause_id}' missing 'section'.")
            if not title:
                raise InvalidPolicyError(f"Clause '{clause_id}' missing 'title'.")
            if not text:
                raise InvalidPolicyError(f"Clause '{clause_id}' has empty 'text'.")

            if clause_id in seen_ids:
                raise DuplicateClauseError(f"Duplicate clause_id found: '{clause_id}'.")

            seen_ids.add(clause_id)
            clauses.append(PolicyClause(
                clause_id=clause_id,
                section=section,
                title=title,
                text=text,
                tags=tags if isinstance(tags, list) else [],
            ))

        return clauses

    def compute_policy_hash(self) -> str:
        """Compute SHA-256 hash of canonical policy clause content.

        Ensures cache invalidation when clauses, titles, sections, or wording change.
        """
        clauses = self.load_clauses()
        # Create canonical representation sorted by clause_id
        canonical_items = [
            {
                "clause_id": c.clause_id,
                "section": c.section,
                "title": c.title,
                "text": c.text,
                "tags": sorted(c.tags),
            }
            for c in sorted(clauses, key=lambda x: x.clause_id)
        ]
        canonical_str = json.dumps(canonical_items, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
