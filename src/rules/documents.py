"""Document completeness rules for ClaimLens (Milestone 5).

Deterministic evaluation of required document inventories against policy requirements
(Clauses 3.2, 7.1, 7.2).
"""

from __future__ import annotations

from typing import Any, Optional, Union
from src.models import ExtractedFact, Document
from src.rules.policy_rules import (
    PolicyFinding,
    check_fir_requirement,
    check_repair_settlement,
    check_required_documents,
    extract_fact_dict,
)


def check_document_completeness(
    documents: Optional[list[Union[Document, str]]] = None,
    facts: Union[list[ExtractedFact], dict[str, Any], None] = None,
) -> list[PolicyFinding]:
    """Verify submitted claim document completeness against policy clauses.

    Args:
        documents: List of Document objects or document filenames/types.
        facts: Optional extracted claim facts.

    Returns:
        List of PolicyFinding objects for document requirements.
    """
    doc_names: list[str] = []
    if documents:
        for d in documents:
            if isinstance(d, Document):
                doc_names.append(d.filename or str(d.document_type.value))
            elif isinstance(d, str):
                doc_names.append(d)

    fact_dict, fact_objs = extract_fact_dict(facts)
    findings: list[PolicyFinding] = []

    # Clause 2.2: Repair settlement / estimate document
    findings.append(check_repair_settlement(fact_dict, fact_objs, documents=doc_names))

    # Clause 3.2: Mandatory FIR for theft claims
    findings.append(check_fir_requirement(fact_dict, fact_objs, documents=doc_names))

    # Clause 7.1 / 7.2: Required document checklist
    findings.append(check_required_documents(fact_dict, fact_objs, documents=doc_names))

    return findings
