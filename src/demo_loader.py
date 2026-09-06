"""Canonical Demo Claim Data Loader for ClaimLens (PS02).

Provides pre-loaded canonical ground truth documents and structured facts
for the synthetic demo claims (CLM-001, CLM-002, CLM-003).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo_claims"

CLAIM_MAP = {
    "CLM-001": ("claim_001_clean_accident", "Clean Accident Claim (Supported)"),
    "CLM-002": ("claim_002_contradiction", "Contradictory Claim (Date & Amount Mismatch)"),
    "CLM-003": ("claim_003_missing_fir", "Theft Claim (Missing Mandatory FIR)"),
}


def load_demo_claim(claim_id: str) -> dict[str, Any]:
    """Load canonical demo claim data including metadata, document list, and structured facts."""
    cid = claim_id.upper().strip()
    if cid not in CLAIM_MAP:
        raise KeyError(f"Demo claim '{claim_id}' not found. Available: {list(CLAIM_MAP.keys())}")

    folder_name, description = CLAIM_MAP[cid]
    claim_path = DEMO_DIR / folder_name
    meta_path = claim_path / "metadata.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Documents available on disk
    pdf_docs = sorted([p.name for p in claim_path.glob("*.pdf")])

    extracted_docs: list[dict[str, Any]] = []

    if cid == "CLM-001":
        cf_facts = [
            {"field_name": "claim_id", "value": "CLM-001", "raw_value": "CLM-001", "evidence_text": "Claim ID: CLM-001", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "policy_number", "value": "POL-001", "raw_value": "POL-001", "evidence_text": "Policy Number: POL-001", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "TN01AB1234", "raw_value": "TN01AB1234", "evidence_text": "Registration: TN01AB1234", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_make", "value": "Hyundai", "raw_value": "Hyundai", "evidence_text": "Vehicle: Hyundai i20", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle_model", "value": "i20", "raw_value": "i20", "evidence_text": "Vehicle: Hyundai i20", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle", "value": "Hyundai i20", "raw_value": "Hyundai i20", "evidence_text": "Vehicle: Hyundai i20", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "incident_type", "value": "Accident", "raw_value": "Accident", "evidence_text": "Incident Type: Accident", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date of Incident: 20 August 2026", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "notification_date", "value": "2026-08-22", "raw_value": "22 August 2026", "evidence_text": "Notification Date: 22 August 2026", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "claimed_amount", "value": 78000.0, "raw_value": "78000", "evidence_text": "Total Claimed Amount: Rs. 78,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "incident_description", "value": metadata.get("incident_description"), "raw_value": metadata.get("incident_description"), "evidence_text": "The insured vehicle was travelling on a city road when another vehicle collided with its front-left side.", "page_number": 1, "confidence": 0.96, "evidence_valid": True},
        ]
        re_facts = [
            {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date of Loss: 20 August 2026", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "TN01AB1234", "raw_value": "TN01AB1234", "evidence_text": "Vehicle Reg: TN01AB1234", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "repair_estimate_amount", "value": 78000.0, "raw_value": "78000", "evidence_text": "Total Estimate: Rs. 78,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "estimated_repair_amount", "value": 78000.0, "raw_value": "78000", "evidence_text": "Total Estimate: Rs. 78,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
        ]
        extracted_docs = [
            {
                "document_name": "claim_form.pdf",
                "document_type": "claim_form",
                "filename": "claim_form.pdf",
                "page_count": 1,
                "facts": cf_facts,
            },
            {
                "document_name": "repair_estimate.pdf",
                "document_type": "repair_estimate",
                "filename": "repair_estimate.pdf",
                "page_count": 1,
                "facts": re_facts,
            },
        ]
        inc_desc = metadata.get("incident_description", "")

    elif cid == "CLM-002":
        cf_meta = metadata.get("claim_form", {})
        re_meta = metadata.get("repair_estimate", {})
        cf_facts = [
            {"field_name": "claim_id", "value": "CLM-002", "raw_value": "CLM-002", "evidence_text": "Claim ID: CLM-002", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "policy_number", "value": "POL-002", "raw_value": "POL-002", "evidence_text": "Policy Number: POL-002", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "TN02CD5678", "raw_value": "TN02CD5678", "evidence_text": "Registration: TN02CD5678", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_make", "value": "Maruti", "raw_value": "Maruti", "evidence_text": "Vehicle: Maruti Baleno", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle_model", "value": "Baleno", "raw_value": "Baleno", "evidence_text": "Vehicle: Maruti Baleno", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle", "value": "Maruti Baleno", "raw_value": "Maruti Baleno", "evidence_text": "Vehicle: Maruti Baleno", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "incident_type", "value": "Accident", "raw_value": "Accident", "evidence_text": "Incident Type: Accident", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "incident_date", "value": "2026-08-10", "raw_value": cf_meta.get("incident_date", "10 August 2026"), "evidence_text": "Date of Accident: 10 August 2026", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "notification_date", "value": "2026-08-15", "raw_value": cf_meta.get("notification_date", "15 August 2026"), "evidence_text": "Notification Date: 15 August 2026", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "claimed_amount", "value": float(cf_meta.get("claimed_amount", 85000)), "raw_value": "85000", "evidence_text": "Claimed Amount: Rs. 85,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "incident_description", "value": cf_meta.get("incident_description"), "raw_value": cf_meta.get("incident_description"), "evidence_text": "The vehicle was involved in a collision on 10 August 2026.", "page_number": 1, "confidence": 0.96, "evidence_valid": True},
        ]
        re_facts = [
            {"field_name": "incident_date", "value": "2026-08-14", "raw_value": re_meta.get("incident_date", "14 August 2026"), "evidence_text": "Date of Loss: 14 August 2026", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "TN02CD5678", "raw_value": "TN02CD5678", "evidence_text": "Vehicle Reg: TN02CD5678", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "repair_estimate_amount", "value": float(re_meta.get("estimated_repair_amount", 92000)), "raw_value": "92000", "evidence_text": "Total Estimate: Rs. 92,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "estimated_repair_amount", "value": float(re_meta.get("estimated_repair_amount", 92000)), "raw_value": "92000", "evidence_text": "Total Estimate: Rs. 92,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
        ]
        extracted_docs = [
            {
                "document_name": "claim_form.pdf",
                "document_type": "claim_form",
                "filename": "claim_form.pdf",
                "page_count": 1,
                "facts": cf_facts,
            },
            {
                "document_name": "repair_estimate.pdf",
                "document_type": "repair_estimate",
                "filename": "repair_estimate.pdf",
                "page_count": 1,
                "facts": re_facts,
            },
        ]
        inc_desc = cf_meta.get("incident_description", "")

    elif cid == "CLM-003":
        cf_facts = [
            {"field_name": "claim_id", "value": "CLM-003", "raw_value": "CLM-003", "evidence_text": "Claim ID: CLM-003", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "policy_number", "value": "POL-003", "raw_value": "POL-003", "evidence_text": "Policy Number: POL-003", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "TN03EF9012", "raw_value": "TN03EF9012", "evidence_text": "Registration: TN03EF9012", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "vehicle_make", "value": "Honda", "raw_value": "Honda", "evidence_text": "Vehicle: Honda Activa 6G", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle_model", "value": "Activa 6G", "raw_value": "Activa 6G", "evidence_text": "Vehicle: Honda Activa 6G", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "vehicle", "value": "Honda Activa 6G", "raw_value": "Honda Activa 6G", "evidence_text": "Vehicle: Honda Activa 6G", "page_number": 1, "confidence": 0.95, "evidence_valid": True},
            {"field_name": "incident_type", "value": "Theft", "raw_value": "Theft", "evidence_text": "Incident Type: Theft", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "incident_date", "value": "2026-08-25", "raw_value": "25 August 2026", "evidence_text": "Date of Theft: 25 August 2026", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "notification_date", "value": "2026-08-26", "raw_value": "26 August 2026", "evidence_text": "Notification Date: 26 August 2026", "page_number": 1, "confidence": 0.98, "evidence_valid": True},
            {"field_name": "claimed_amount", "value": float(metadata.get("claimed_amount", 72000)), "raw_value": "72000", "evidence_text": "IDV Claimed: Rs. 72,000", "page_number": 1, "confidence": 0.99, "evidence_valid": True},
            {"field_name": "incident_description", "value": metadata.get("incident_description"), "raw_value": metadata.get("incident_description"), "evidence_text": "The insured two-wheeler was parked in the designated parking area outside the insured's residence at approximately 9:00 PM. The vehicle was discovered missing at approximately 7:00 AM the following morning. The insured states that the vehicle was not recovered.", "page_number": 1, "confidence": 0.96, "evidence_valid": True},
        ]
        extracted_docs = [
            {
                "document_name": "claim_form.pdf",
                "document_type": "claim_form",
                "filename": "claim_form.pdf",
                "page_count": 1,
                "facts": cf_facts,
            }
        ]
        inc_desc = metadata.get("incident_description", "")

    all_facts: list[dict[str, Any]] = []
    for doc in extracted_docs:
        all_facts.extend(doc["facts"])

    return {
        "success": True,
        "claim_id": cid,
        "description": description,
        "documents": pdf_docs,
        "incident_description": inc_desc,
        "metadata": metadata,
        "extracted_documents": extracted_docs,
        "all_facts": all_facts,
        "primary_extraction": {
            "document": {
                "filename": extracted_docs[0]["filename"],
                "document_type": extracted_docs[0]["document_type"],
                "page_count": extracted_docs[0]["page_count"],
            },
            "facts": extracted_docs[0]["facts"],
        } if extracted_docs else None,
    }
