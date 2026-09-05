"""Generate synthetic PDF documents for ClaimLens demo policy and claims.

Produces clean, text-based, searchable PDFs using ReportLab:
- data/policy/ClaimLens_Motor_Policy.pdf
- data/demo_claims/claim_001_clean_accident/claim_form.pdf
- data/demo_claims/claim_001_clean_accident/repair_estimate.pdf
- data/demo_claims/claim_002_contradiction/claim_form.pdf
- data/demo_claims/claim_002_contradiction/repair_estimate.pdf
- data/demo_claims/claim_003_missing_fir/claim_form.pdf
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BASE_DIR / "data" / "policy"
DEMO_DIR = BASE_DIR / "data" / "demo_claims"


# ── Numbered Canvas for Page X of Y ───────────────────────────────────────

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#dc2626"))

        # Top banner
        disclaimer = "SYNTHETIC DEMONSTRATION DOCUMENT — NOT A REAL INSURANCE POLICY / CLAIM"
        self.drawCentredString(letter[0] / 2.0, letter[1] - 25, disclaimer)

        # Top rule
        self.setStrokeColor(colors.HexColor("#e5e7eb"))
        self.setLineWidth(0.5)
        self.line(40, letter[1] - 32, letter[0] - 40, letter[1] - 32)

        # Bottom footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6b7280"))
        self.drawString(40, 25, "ClaimLens — Motor Insurance Evidence Review Assistant (PS02)")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 25, page_text)
        self.line(40, 37, letter[0] - 40, 37)

        self.restoreState()


# ── Styles ────────────────────────────────────────────────────────────────

def get_doc_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e2330"),
        alignment=0,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        alignment=0,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ClauseHeader",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e2330"),
        spaceBefore=6,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="ClauseBody",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="TableLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#1e2330"),
    ))
    styles.add(ParagraphStyle(
        name="TableValue",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        name="NoticeBox",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#92400e"),
        alignment=1,
    ))
    return styles


# ── PDF Generators ────────────────────────────────────────────────────────

def generate_policy_pdf():
    """Generate the 2-4 page ClaimLens Motor Secure Policy PDF."""
    pdf_path = POLICY_DIR / "ClaimLens_Motor_Policy.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )

    with open(POLICY_DIR / "motor_policy.json", "r", encoding="utf-8") as f:
        policy_data = json.load(f)

    styles = get_doc_styles()
    story = []

    # Title & Subtitle
    story.append(Paragraph(policy_data["policy_name"], styles["DocTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Synthetic Demonstration Policy — Policy ID: " + policy_data["policy_id"], styles["DocSubtitle"]))
    story.append(Spacer(1, 8))

    # Notice box
    notice_data = [[
        Paragraph(
            "<b>NOTICE:</b> " + policy_data["disclaimer"] +
            ". Created strictly for demonstration and testing of evidence review systems.",
            styles["NoticeBox"]
        )
    ]]
    notice_table = Table(notice_data, colWidths=[doc.width])
    notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(notice_table)
    story.append(Spacer(1, 10))

    # Policy Schedule Table
    schedule_data = [
        [Paragraph("Policy ID", styles["TableLabel"]), Paragraph(policy_data["policy_id"], styles["TableValue"]),
         Paragraph("Version", styles["TableLabel"]), Paragraph(policy_data["version"], styles["TableValue"])],
        [Paragraph("Effective Date", styles["TableLabel"]), Paragraph(policy_data["effective_date"], styles["TableValue"]),
         Paragraph("Expiry Date", styles["TableLabel"]), Paragraph(policy_data["expiry_date"], styles["TableValue"])],
        [Paragraph("Coverage Category", styles["TableLabel"]), Paragraph("Private Motor Vehicles (Cars & Two-Wheelers)", styles["TableValue"]),
         Paragraph("Applicable Jurisdiction", styles["TableLabel"]), Paragraph("Motor Vehicles Regulatory Scope (Synthetic)", styles["TableValue"])],
    ]
    schedule_table = Table(schedule_data, colWidths=[110, 155, 110, 155])
    schedule_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(schedule_table)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1d4ed8"), spaceAfter=10))

    # Clauses grouped by section
    sections = {}
    for clause in policy_data["clauses"]:
        sec = clause["section"]
        sections.setdefault(sec, []).append(clause)

    for sec_title, clauses in sections.items():
        story.append(Paragraph(sec_title, styles["SectionHeader"]))
        for c in clauses:
            clause_elements = []
            clause_heading = f"Clause {c['clause_id']} — {c['title']}"
            clause_elements.append(Paragraph(clause_heading, styles["ClauseHeader"]))
            clause_elements.append(Paragraph(c["text"], styles["ClauseBody"]))
            story.append(KeepTogether(clause_elements))
        story.append(Spacer(1, 6))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


def _build_key_value_table(styles, fields, doc_width):
    table_data = []
    for row in fields:
        if len(row) == 2:
            table_data.append([
                Paragraph(row[0], styles["TableLabel"]),
                Paragraph(str(row[1]), styles["TableValue"]),
            ])
        elif len(row) == 4:
            table_data.append([
                Paragraph(row[0], styles["TableLabel"]),
                Paragraph(str(row[1]), styles["TableValue"]),
                Paragraph(row[2], styles["TableLabel"]),
                Paragraph(str(row[3]), styles["TableValue"]),
            ])
    col_w = [140, doc_width - 140] if len(fields[0]) == 2 else [110, (doc_width - 220) / 2, 110, (doc_width - 220) / 2]
    t = Table(table_data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def generate_claim_form_pdf(output_path: Path, claim_data: dict):
    """Generate a clean claim form PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )
    styles = get_doc_styles()
    story = []

    story.append(Paragraph("MOTOR INSURANCE CLAIM FORM", styles["DocTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Claim Reference: {claim_data['claim_id']} · Policy: {claim_data['policy_number']}", styles["DocSubtitle"]))
    story.append(Spacer(1, 10))

    # General Info
    story.append(Paragraph("1. Policy & Insured Details", styles["SectionHeader"]))
    fields_1 = [
        ["Claim ID", claim_data["claim_id"], "Policy Number", claim_data["policy_number"]],
        ["Insured Name", claim_data.get("insured_name", "Rajesh Kumar"), "Contact Number", "+91 98765 43210"],
        ["Vehicle Registration", claim_data["vehicle_registration"], "Vehicle Make/Model", claim_data["vehicle"]],
        ["Vehicle Category", claim_data.get("vehicle_category", "Private Four-Wheeler"), "Policy Status", "Active / In-Force"],
    ]
    story.append(_build_key_value_table(styles, fields_1, doc.width))
    story.append(Spacer(1, 10))

    # Incident Details
    story.append(Paragraph("2. Incident & Loss Details", styles["SectionHeader"]))
    fields_2 = [
        ["Incident Type", claim_data["claim_type"].title(), "Incident Date", claim_data["incident_date"]],
        ["Notification Date", claim_data["notification_date"], "Incident Location", claim_data.get("incident_location", "Anna Salai, Chennai")],
        ["Total Claimed Amount", f"₹{claim_data['claimed_amount']:,}", "Driver at Incident", claim_data.get("driver", "Self (Insured)")],
    ]
    story.append(_build_key_value_table(styles, fields_2, doc.width))
    story.append(Spacer(1, 10))

    # Incident Description
    story.append(Paragraph("3. Detailed Incident Description", styles["SectionHeader"]))
    desc_data = [[Paragraph(f"<b>Insured Statement:</b><br/>{claim_data['incident_description']}", styles["ClauseBody"])]]
    desc_table = Table(desc_data, colWidths=[doc.width])
    desc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdfdfd")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(desc_table)
    story.append(Spacer(1, 12))

    # Declaration
    story.append(Paragraph("4. Insured Declaration", styles["SectionHeader"]))
    decl_text = (
        "I hereby declare that the particulars given above are true and complete in all respects. "
        "I understand this document is a synthetic demonstration record for the ClaimLens project."
    )
    story.append(Paragraph(decl_text, styles["ClauseBody"]))
    story.append(Spacer(1, 8))

    sig_data = [
        [Paragraph("<b>Signature of Insured:</b> <i>[Signed Electronically]</i>", styles["TableValue"]),
         Paragraph(f"<b>Date of Submission:</b> {claim_data['notification_date']}", styles["TableValue"])]
    ]
    sig_table = Table(sig_data, colWidths=[doc.width / 2.0, doc.width / 2.0])
    sig_table.setStyle(TableStyle([
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {output_path}")


def generate_repair_estimate_pdf(output_path: Path, estimate_data: dict):
    """Generate an itemized repair estimate PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )
    styles = get_doc_styles()
    story = []

    story.append(Paragraph("AUTHORIZED WORKSHOP REPAIR ESTIMATE", styles["DocTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Estimate Ref: EST-{estimate_data['claim_id']} · Claim Reference: {estimate_data['claim_id']}", styles["DocSubtitle"]))
    story.append(Spacer(1, 10))

    # Garage & Vehicle Details
    story.append(Paragraph("1. Workshop & Vehicle Assessment Details", styles["SectionHeader"]))
    fields = [
        ["Workshop Name", estimate_data.get("workshop_name", "Apex Motor Works & Bodycraft"), "GSTIN / Reg No.", "33AABCA1234F1Z5"],
        ["Claim ID", estimate_data["claim_id"], "Vehicle Registration", estimate_data["vehicle_registration"]],
        ["Vehicle Make/Model", estimate_data["vehicle"], "Estimate Date", estimate_data["estimate_date"]],
        ["Incident Date (Assessed)", estimate_data["incident_date"], "Assessor Name", estimate_data.get("assessor", "V. Sundaram (Chief Surveyor)")],
    ]
    story.append(_build_key_value_table(styles, fields, doc.width))
    story.append(Spacer(1, 12))

    # Itemized Breakdown
    story.append(Paragraph("2. Itemized Parts & Labour Breakdown", styles["SectionHeader"]))

    item_rows = [
        [
            Paragraph("<b>#</b>", styles["TableLabel"]),
            Paragraph("<b>Description of Damage / Work</b>", styles["TableLabel"]),
            Paragraph("<b>Operation</b>", styles["TableLabel"]),
            Paragraph("<b>Parts (₹)</b>", styles["TableLabel"]),
            Paragraph("<b>Labour (₹)</b>", styles["TableLabel"]),
            Paragraph("<b>Subtotal (₹)</b>", styles["TableLabel"]),
        ]
    ]

    items = estimate_data["items"]
    total_parts = 0
    total_labour = 0

    for idx, it in enumerate(items, 1):
        p_cost = it["parts_cost"]
        l_cost = it["labour_cost"]
        sub = p_cost + l_cost
        total_parts += p_cost
        total_labour += l_cost
        item_rows.append([
            Paragraph(str(idx), styles["TableValue"]),
            Paragraph(it["description"], styles["TableValue"]),
            Paragraph(it["operation"], styles["TableValue"]),
            Paragraph(f"{p_cost:,}", styles["TableValue"]),
            Paragraph(f"{l_cost:,}", styles["TableValue"]),
            Paragraph(f"{sub:,}", styles["TableValue"]),
        ])

    grand_total = estimate_data["estimated_repair_amount"]

    item_rows.append([
        Paragraph("<b>Total</b>", styles["TableLabel"]),
        Paragraph("<b>Grand Total Estimated Repair Cost</b>", styles["TableLabel"]),
        Paragraph("", styles["TableValue"]),
        Paragraph(f"<b>₹{total_parts:,}</b>", styles["TableLabel"]),
        Paragraph(f"<b>₹{total_labour:,}</b>", styles["TableLabel"]),
        Paragraph(f"<b>₹{grand_total:,}</b>", styles["TableLabel"]),
    ])

    item_table = Table(item_rows, colWidths=[25, 185, 90, 75, 75, 82])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 14))

    # Notes & Certification
    story.append(Paragraph("3. Workshop Certification", styles["SectionHeader"]))
    cert_text = (
        "We certify that the above estimate covers only the accidental damage inspected on the vehicle. "
        "All replacement parts quoted are OEM standard. This is a synthetic demonstration estimate for ClaimLens."
    )
    story.append(Paragraph(cert_text, styles["ClauseBody"]))
    story.append(Spacer(1, 8))

    sig_data = [
        [Paragraph("<b>Authorized Signature:</b> <i>[Apex Motor Works]</i>", styles["TableValue"]),
         Paragraph(f"<b>Date:</b> {estimate_data['estimate_date']}", styles["TableValue"])]
    ]
    sig_table = Table(sig_data, colWidths=[doc.width / 2.0, doc.width / 2.0])
    sig_table.setStyle(TableStyle([
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {output_path}")


def main():
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Policy PDF
    generate_policy_pdf()

    # 2. Case 001 — Clean Accident
    c1_dir = DEMO_DIR / "claim_001_clean_accident"
    c1_dir.mkdir(exist_ok=True)

    c1_claim_data = {
        "claim_id": "CLM-001",
        "policy_number": "POL-001",
        "vehicle_registration": "TN01AB1234",
        "vehicle": "Hyundai i20",
        "vehicle_category": "Private Four-Wheeler (Hatchback)",
        "claim_type": "accident",
        "incident_date": "20 August 2026",
        "notification_date": "22 August 2026",
        "claimed_amount": 78000,
        "incident_location": "Mount Road, Chennai",
        "incident_description": (
            "The insured vehicle was travelling on a city road when another vehicle collided "
            "with its front-left side. The insured vehicle sustained damage to the front bumper, "
            "left headlamp and front fender."
        ),
    }
    generate_claim_form_pdf(c1_dir / "claim_form.pdf", c1_claim_data)

    c1_estimate_data = {
        "claim_id": "CLM-001",
        "vehicle_registration": "TN01AB1234",
        "vehicle": "Hyundai i20",
        "estimate_date": "23 August 2026",
        "incident_date": "20 August 2026",
        "estimated_repair_amount": 78000,
        "items": [
            {"description": "Front Bumper Assembly", "operation": "Replacement", "parts_cost": 28000, "labour_cost": 6000},
            {"description": "Left Headlamp Unit (LED)", "operation": "Replacement", "parts_cost": 24000, "labour_cost": 4000},
            {"description": "Front Left Fender", "operation": "Repair & Painting", "parts_cost": 6000, "labour_cost": 10000},
        ]
    }
    generate_repair_estimate_pdf(c1_dir / "repair_estimate.pdf", c1_estimate_data)

    # 3. Case 002 — Contradictory Accident
    c2_dir = DEMO_DIR / "claim_002_contradiction"
    c2_dir.mkdir(exist_ok=True)

    c2_claim_data = {
        "claim_id": "CLM-002",
        "policy_number": "POL-002",
        "vehicle_registration": "TN02CD5678",
        "vehicle": "Maruti Baleno",
        "vehicle_category": "Private Four-Wheeler (Hatchback)",
        "claim_type": "accident",
        "incident_date": "10 August 2026",
        "notification_date": "15 August 2026",
        "claimed_amount": 85000,
        "incident_location": "GST Road, Tambaram, Chennai",
        "incident_description": "The vehicle was involved in a collision on 10 August 2026.",
    }
    generate_claim_form_pdf(c2_dir / "claim_form.pdf", c2_claim_data)

    c2_estimate_data = {
        "claim_id": "CLM-002",
        "vehicle_registration": "TN02CD5678",
        "vehicle": "Maruti Baleno",
        "estimate_date": "16 August 2026",
        "incident_date": "14 August 2026",  # Contradiction: 14 Aug vs 10 Aug
        "estimated_repair_amount": 92000,   # Contradiction: ₹92,000 vs ₹85,000
        "items": [
            {"description": "Front Bumper Assembly", "operation": "Replacement", "parts_cost": 26000, "labour_cost": 7000},
            {"description": "Right Headlamp Unit", "operation": "Replacement", "parts_cost": 22000, "labour_cost": 4000},
            {"description": "Bonnet & Grille Panel", "operation": "Repair & Painting", "parts_cost": 18000, "labour_cost": 15000},
        ]
    }
    generate_repair_estimate_pdf(c2_dir / "repair_estimate.pdf", c2_estimate_data)

    # 4. Case 003 — Theft with Missing FIR
    c3_dir = DEMO_DIR / "claim_003_missing_fir"
    c3_dir.mkdir(exist_ok=True)

    c3_claim_data = {
        "claim_id": "CLM-003",
        "policy_number": "POL-003",
        "vehicle_registration": "TN03EF9012",
        "vehicle": "Honda Activa 6G",
        "vehicle_category": "Two-Wheeler (Scooter)",
        "claim_type": "theft",
        "incident_date": "25 August 2026",
        "notification_date": "26 August 2026",
        "claimed_amount": 72000,
        "incident_location": "Residential Parking, T. Nagar, Chennai",
        "incident_description": (
            "The insured two-wheeler was parked in the designated parking area outside "
            "the insured's residence at approximately 9:00 PM. The vehicle was discovered "
            "missing at approximately 7:00 AM the following morning. The insured states "
            "that the vehicle was not recovered."
        ),
    }
    generate_claim_form_pdf(c3_dir / "claim_form.pdf", c3_claim_data)
    # FIR is INTENTIONALLY NOT CREATED FOR CASE 003


if __name__ == "__main__":
    main()
