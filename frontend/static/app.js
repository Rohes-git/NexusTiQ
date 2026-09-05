/* ================================================================
   ClaimLens — app.js (Milestone 3)
   Handles single-document fact extraction via Gemini and claim submission.
   No external libraries.
   ================================================================ */

(function () {
  "use strict";

  // ── DOM References ──────────────────────────────────────────────
  const form = document.getElementById("claim-form");
  const reviewBtn = document.getElementById("review-btn");
  const feedback = document.getElementById("submit-feedback");

  const claimFormInput = document.getElementById("claim-form-file");
  const repairInput = document.getElementById("repair-estimate-file");
  const descriptionInput = document.getElementById("incident-description");

  const claimFormName = document.getElementById("claim-form-name");
  const repairEstimateName = document.getElementById("repair-estimate-name");

  const btnExtractClaimForm = document.getElementById("btn-extract-claim-form");
  const btnExtractRepair = document.getElementById("btn-extract-repair-estimate");
  const btnRetrievePolicy = document.getElementById("btn-retrieve-policy");

  const extractionCard = document.getElementById("extraction-results-card");
  const extractDocTypeBadge = document.getElementById("extract-doc-type-badge");
  const metaFilename = document.getElementById("meta-filename");
  const metaPages = document.getElementById("meta-pages");
  const summaryGrid = document.getElementById("summary-grid");
  const evidenceList = document.getElementById("evidence-list");

  const policyResultsCard = document.getElementById("policy-results-card");
  const policyQueryText = document.getElementById("policy-query-text");
  const groundedClausesList = document.getElementById("grounded-clauses-list");

  const statusClaimForm = document.getElementById("status-claim-form");
  const statusRepairEstimate = document.getElementById("status-repair-estimate");
  const statusDescription = document.getElementById("status-description");
  const policyStatus = document.getElementById("policy-status");

  var currentExtractedFacts = [];

  // ── File-name and Button State Binding ──────────────────────────
  function bindFileInput(input, nameEl, btnEl) {
    input.addEventListener("change", function () {
      if (input.files.length) {
        nameEl.textContent = input.files[0].name;
        btnEl.disabled = false;
      } else {
        nameEl.textContent = "";
        btnEl.disabled = true;
      }
      updateReviewPreview();
    });
  }

  bindFileInput(claimFormInput, claimFormName, btnExtractClaimForm);
  bindFileInput(repairInput, repairEstimateName, btnExtractRepair);
  descriptionInput.addEventListener("input", updateReviewPreview);

  // ── Drag & Drop UI ──────────────────────────────────────────────
  document.querySelectorAll(".file-upload").forEach(function (zone) {
    zone.addEventListener("dragover", function (e) {
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", function () {
      zone.classList.remove("dragover");
    });
    zone.addEventListener("drop", function () {
      zone.classList.remove("dragover");
    });
  });

  // ── Live Review Preview Updates ─────────────────────────────────
  function updateReviewPreview() {
    if (claimFormInput.files.length) {
      statusClaimForm.textContent = "Received";
      statusClaimForm.className = "badge badge-received";
    } else {
      statusClaimForm.textContent = "Not submitted";
      statusClaimForm.className = "badge badge-empty";
    }

    if (repairInput.files.length) {
      statusRepairEstimate.textContent = "Received";
      statusRepairEstimate.className = "badge badge-received";
    } else {
      statusRepairEstimate.textContent = "Not submitted";
      statusRepairEstimate.className = "badge badge-empty";
    }

    if (descriptionInput.value.trim()) {
      statusDescription.textContent = "Provided";
      statusDescription.className = "badge badge-received";
    } else {
      statusDescription.textContent = "Not submitted";
      statusDescription.className = "badge badge-empty";
    }
  }

  // ── Extract Document Facts via API ──────────────────────────────
  async function extractDocumentFacts(file, triggerBtn) {
    if (!file) return;

    triggerBtn.disabled = true;
    var originalText = triggerBtn.textContent;
    triggerBtn.textContent = "Extracting…";
    feedback.classList.add("hidden");

    var formData = new FormData();
    formData.append("file", file);

    try {
      var response = await fetch("/api/extract-document", {
        method: "POST",
        body: formData,
      });

      var data = await response.json();

      if (!data.success) {
        showFeedback("error", data.error ? data.error.message : "Extraction failed.");
        extractionCard.classList.add("hidden");
      } else {
        renderExtractionResults(data);
      }
    } catch (err) {
      showFeedback("error", "Failed to connect to extraction service. " + err.message);
      extractionCard.classList.add("hidden");
    } finally {
      triggerBtn.disabled = false;
      triggerBtn.textContent = originalText;
    }
  }

  btnExtractClaimForm.addEventListener("click", function () {
    if (claimFormInput.files.length) {
      extractDocumentFacts(claimFormInput.files[0], btnExtractClaimForm);
    }
  });

  btnExtractRepair.addEventListener("click", function () {
    if (repairInput.files.length) {
      extractDocumentFacts(repairInput.files[0], btnExtractRepair);
    }
  });

  // ── Render Structured Facts & Evidence ──────────────────────────
  function renderExtractionResults(data) {
    currentExtractedFacts = data.facts || [];
    metaFilename.textContent = data.document.filename;
    metaPages.textContent = data.document.page_count;

    var typeLabels = {
      claim_form: "Claim Form",
      repair_estimate: "Repair Estimate",
      fir: "First Information Report (FIR)",
      unknown: "Unknown Document",
    };
    extractDocTypeBadge.textContent = typeLabels[data.document.document_type] || data.document.document_type;

    // Render Summary Grid
    summaryGrid.innerHTML = "";
    data.facts.forEach(function (fact) {
      var card = document.createElement("div");
      card.className = "fact-card";

      var label = document.createElement("div");
      label.className = "fact-label";
      label.textContent = fact.field_name.replace(/_/g, " ");

      var val = document.createElement("div");
      val.className = "fact-value";
      val.textContent = formatFactValue(fact.field_name, fact.value);

      card.appendChild(label);
      card.appendChild(val);

      if (fact.raw_value && String(fact.raw_value) !== String(fact.value)) {
        var raw = document.createElement("div");
        raw.className = "fact-raw";
        raw.textContent = "Raw: " + fact.raw_value;
        card.appendChild(raw);
      }

      summaryGrid.appendChild(card);
    });

    // Render Evidence Provenance List
    evidenceList.innerHTML = "";
    data.facts.forEach(function (fact) {
      var item = document.createElement("div");
      item.className = "evidence-card" + (fact.evidence_valid ? "" : " unverified");

      var header = document.createElement("div");
      header.className = "evidence-card-header";

      var title = document.createElement("span");
      title.className = "evidence-field-name";
      title.textContent = fact.field_name.replace(/_/g, " ");

      var pills = document.createElement("div");
      pills.className = "evidence-meta-pills";

      var pagePill = document.createElement("span");
      pagePill.className = "page-pill";
      pagePill.textContent = "Page " + fact.page_number;
      pills.appendChild(pagePill);

      var confPill = document.createElement("span");
      confPill.className = "conf-pill";
      confPill.textContent = Math.round(fact.confidence * 100) + "% confidence";
      pills.appendChild(confPill);

      var validBadge = document.createElement("span");
      validBadge.className = "badge " + (fact.evidence_valid ? "badge-success" : "badge-error");
      validBadge.textContent = fact.evidence_valid ? "✓ Verified in source" : "✗ Unverified quote";
      pills.appendChild(validBadge);

      header.appendChild(title);
      header.appendChild(pills);

      var quoteBox = document.createElement("div");
      quoteBox.className = "quote-box";
      quoteBox.textContent = fact.evidence_text || "(No evidence quote provided)";

      item.appendChild(header);
      item.appendChild(quoteBox);
      evidenceList.appendChild(item);
    });

    extractionCard.classList.remove("hidden");
    extractionCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ── Policy Retrieval (Milestone 4) ──────────────────────────────
  if (btnRetrievePolicy) {
    btnRetrievePolicy.addEventListener("click", async function () {
      if (!currentExtractedFacts || currentExtractedFacts.length === 0) {
        showFeedback("error", "Please extract facts from a document first before retrieving policy clauses.");
        return;
      }

      btnRetrievePolicy.disabled = true;
      var originalText = btnRetrievePolicy.textContent;
      btnRetrievePolicy.textContent = "Retrieving Policy…";
      feedback.classList.add("hidden");

      try {
        var response = await fetch("/api/retrieve-policy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ facts: currentExtractedFacts, top_k: 5 }),
        });

        var data = await response.json();

        if (!data.success) {
          showFeedback("error", data.error || "Failed to retrieve relevant policy clauses.");
          policyResultsCard.classList.add("hidden");
        } else {
          renderPolicyResults(data);
        }
      } catch (err) {
        showFeedback("error", "Error connecting to policy retrieval service: " + err.message);
        policyResultsCard.classList.add("hidden");
      } finally {
        btnRetrievePolicy.disabled = false;
        btnRetrievePolicy.textContent = originalText;
      }
    });
  }

  function renderPolicyResults(data) {
    policyQueryText.textContent = data.query || "(No query text)";
    groundedClausesList.innerHTML = "";

    (data.clauses || []).forEach(function (clause) {
      var card = document.createElement("div");
      card.className = "grounded-clause-card";

      // Header row
      var header = document.createElement("div");
      header.className = "clause-header-row";

      var leftMeta = document.createElement("div");
      leftMeta.style.display = "flex";
      leftMeta.style.alignItems = "center";

      var idBadge = document.createElement("span");
      idBadge.className = "clause-id-badge";
      idBadge.textContent = "Clause " + clause.clause_id;

      var secSpan = document.createElement("span");
      secSpan.className = "clause-section";
      secSpan.textContent = clause.section;

      leftMeta.appendChild(idBadge);
      leftMeta.appendChild(secSpan);

      var relevancePill = document.createElement("span");
      relevancePill.className = "relevance-pill";
      var pct = Math.round(clause.similarity_score * 100);
      relevancePill.textContent = pct + "% Relevance";

      header.appendChild(leftMeta);
      header.appendChild(relevancePill);

      // Title
      var title = document.createElement("div");
      title.className = "clause-title-text";
      title.textContent = clause.title;

      // Policy Text
      var quoteBox = document.createElement("div");
      quoteBox.className = "policy-quote-box";
      quoteBox.textContent = clause.text;

      // Reason Box
      var reasonBox = document.createElement("div");
      reasonBox.className = "grounding-reason-box";
      reasonBox.innerHTML = "<strong>Factual Rationale:</strong>&nbsp;" + clause.reason;

      card.appendChild(header);
      card.appendChild(title);
      card.appendChild(quoteBox);
      card.appendChild(reasonBox);

      groundedClausesList.appendChild(card);
    });

    policyResultsCard.classList.remove("hidden");
    policyResultsCard.scrollIntoView({ behavior: "smooth", block: "start" });

    if (policyStatus) {
      policyStatus.textContent = (data.clauses ? data.clauses.length : 0) + " policy clauses grounded via vector retrieval";
      policyStatus.className = "text-success font-medium";
    }
  }

      var confPill = document.createElement("span");
      confPill.className = "conf-pill";
      confPill.textContent = Math.round(fact.confidence * 100) + "% confidence";
      pills.appendChild(confPill);

      var validBadge = document.createElement("span");
      validBadge.className = "badge " + (fact.evidence_valid ? "badge-success" : "badge-error");
      validBadge.textContent = fact.evidence_valid ? "✓ Verified in source" : "✗ Unverified quote";
      pills.appendChild(validBadge);

      header.appendChild(title);
      header.appendChild(pills);

      var quoteBox = document.createElement("div");
      quoteBox.className = "quote-box";
      quoteBox.textContent = fact.evidence_text || "(No evidence quote provided)";

      item.appendChild(header);
      item.appendChild(quoteBox);
      evidenceList.appendChild(item);
    });

    extractionCard.classList.remove("hidden");
    extractionCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function formatFactValue(fieldName, value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    if (fieldName.includes("amount")) {
      return "₹" + Number(value).toLocaleString();
    }
    return String(value);
  }

  function showFeedback(type, message) {
    feedback.className = "feedback " + type;
    feedback.textContent = message;
    feedback.classList.remove("hidden");
  }

  // ── Full Review Submission Handler ──────────────────────────────
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    reviewBtn.disabled = true;
    reviewBtn.textContent = "Submitting…";
    feedback.classList.add("hidden");

    var formData = new FormData(form);

    try {
      var response = await fetch("/api/claims/review", {
        method: "POST",
        body: formData,
      });

      var data = await response.json();

      feedback.className = "feedback info";
      feedback.innerHTML =
        "<strong>Received.</strong> " +
        data.message +
        (data.documents_received && data.documents_received.length
          ? "<br>Documents: " +
            data.documents_received.map(function (d) { return d.filename; }).join(", ")
          : "");
      feedback.classList.remove("hidden");
    } catch (err) {
      showFeedback("info", "Review engine will be connected in a later milestone.");
    } finally {
      reviewBtn.disabled = false;
      reviewBtn.textContent = "Submit for Full Review";
    }
  });
})();
