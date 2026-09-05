"""Query builder for policy retrieval.

Converts extracted claim facts into a concise, policy-relevant semantic query
for embedding similarity search without fabricating facts or making policy conclusions.
"""

from __future__ import annotations

from typing import Any, Union
from src.models import ExtractedFact, ClaimFacts


class QueryBuilder:
    """Constructs semantic search queries from structured claim facts."""

    @staticmethod
    def build_query(facts: Union[list[ExtractedFact], dict[str, Any], ClaimFacts, None]) -> str:
        """Construct a clean, semantic search query from claim facts.

        Args:
            facts: Extracted facts as a list of ExtractedFact, a dict of field-value pairs,
                   or a ClaimFacts domain object.

        Returns:
            Concise, factual search query string highlighting key policy dimensions.
        """
        fact_dict: dict[str, Any] = {}

        if facts is None:
            return "motor insurance claim coverage requirements policy terms"

        if isinstance(facts, list):
            for item in facts:
                if isinstance(item, ExtractedFact) and item.value is not None:
                    fact_dict[item.field_name] = item.value
                elif isinstance(item, dict) and "field_name" in item and "value" in item:
                    if item["value"] is not None:
                        fact_dict[item["field_name"]] = item["value"]
        elif isinstance(facts, dict):
            fact_dict = {k: v for k, v in facts.items() if v is not None}
        elif isinstance(facts, ClaimFacts):
            fact_dict = {k: v for k, v in facts.model_dump().items() if v is not None}

        # Extract specific semantic dimensions
        query_segments: list[str] = []

        # 1. Incident Type / Core Event
        incident_type = str(fact_dict.get("incident_type", "")).strip().lower()
        if incident_type:
            if "theft" in incident_type or "stolen" in incident_type:
                query_segments.append("Theft loss and stolen vehicle claim with police FIR report requirements")
            elif "accident" in incident_type or "collision" in incident_type or "damage" in incident_type:
                query_segments.append("Accidental damage collision repair claim and vehicle estimate coverage")
            else:
                query_segments.append(f"Claim incident type {incident_type} coverage and policy terms")
        else:
            # Check incident description if incident_type not explicitly given
            desc = str(fact_dict.get("incident_description", "")).strip().lower()
            if "stolen" in desc or "theft" in desc:
                query_segments.append("Theft loss and stolen vehicle claim with police FIR report requirements")
            elif "accident" in desc or "hit" in desc or "collid" in desc or "damage" in desc:
                query_segments.append("Accidental damage collision repair claim and vehicle estimate coverage")
            else:
                query_segments.append("Motor insurance claim coverage, required documents, and policy conditions")

        # 2. Vehicle Identification
        vehicle_parts = []
        if fact_dict.get("vehicle_make"):
            vehicle_parts.append(str(fact_dict["vehicle_make"]))
        if fact_dict.get("vehicle_model"):
            vehicle_parts.append(str(fact_dict["vehicle_model"]))
        if fact_dict.get("vehicle_registration"):
            vehicle_parts.append(f"Reg: {fact_dict['vehicle_registration']}")
        if vehicle_parts:
            query_segments.append(f"Vehicle: {' '.join(vehicle_parts)}")

        # 3. Dates & Notification Window
        date_parts = []
        if fact_dict.get("incident_date"):
            date_parts.append(f"incident date {fact_dict['incident_date']}")
        if fact_dict.get("notification_date"):
            date_parts.append(f"notification date {fact_dict['notification_date']}")
        if date_parts:
            query_segments.append(f"Timeline: {', '.join(date_parts)} within notification window")

        # 4. Financial & Repair Amounts
        amounts = []
        if fact_dict.get("claimed_amount"):
            amounts.append(f"claimed amount {fact_dict['claimed_amount']}")
        if fact_dict.get("repair_estimate_amount"):
            amounts.append(f"repair estimate amount {fact_dict['repair_estimate_amount']}")
        if amounts:
            query_segments.append(f"Financials: {', '.join(amounts)} settlement and IDV evaluation")

        # 5. Incident Description snippet (factual)
        desc = str(fact_dict.get("incident_description", "")).strip()
        if desc:
            # Truncate description to keep query focused
            short_desc = desc[:150]
            query_segments.append(f"Particulars: {short_desc}")

        query_str = ". ".join(query_segments).strip()
        if not query_str:
            return "Motor insurance claim coverage, accidental damage, theft, required documents, and policy schedule."

        return query_str
