/* ================================================================
   ClaimLens — app.js
   Handles:
   - Document fact extraction via Gemini (Milestone 3)
   - Semantic policy retrieval & clause grounding (Milestone 4)
   - Deterministic policy rule evaluation (Milestone 5)
   - Claim submission pipeline tracking
   No external JS libraries.
   ================================================================ */

(function () {
  // ── Demo Actions ────────────────────────────────────────────────
  function applyDemoClaim(claimId) {
    if (claimIdInput) claimIdInput.value = claimId;
    showFeedback("info", "Preloaded Demo Claim: " + claimId + ". (Note: Extraction requires PDF upload for this demo context)");
  }
  if (document.getElementById("btn-demo-clm-001")) document.getElementById("btn-demo-clm-001").addEventListener("click", () => applyDemoClaim("CLM-001"));
  if (document.getElementById("btn-demo-clm-002")) document.getElementById("btn-demo-clm-002").addEventListener("click", () => applyDemoClaim("CLM-002"));
  if (document.getElementById("btn-demo-clm-003")) document.getElementById("btn-demo-clm-003").addEventListener("click", () => applyDemoClaim("CLM-003"));

  "use strict";

  // ── DOM References ──────────────────────────────────────────────
  var form = document.getElementById("claim-form");
  var reviewBtn = document.getElementById("review-btn");
  var feedback = document.getElementById("submit-feedback");

  var claimFormInput = document.getElementById("claim-form-file");
  var repairInput = document.getElementById("repair-estimate-file");
  var descriptionInput = document.getElementById("incident-description");
  var claimIdInput = document.getElementById("claim-id");

  var claimFormName = document.getElementById("claim-form-name");
  var repairEstimateName = document.getElementById("repair-estimate-name");

  var btnExtractClaimForm = document.getElementById("btn-extract-claim-form");
  var btnExtractRepair = document.getElementById("btn-extract-repair-estimate");
  var btnRetrievePolicy = document.getElementById("btn-retrieve-policy");
  var btnEvaluateRules = document.getElementById("btn-evaluate-rules");
  var btnAnalyzeEvidence = document.getElementById("btn-analyze-evidence");
  var btnGenerateReview = document.getElementById("btn-generate-review-card");
  var finalReviewCard = document.getElementById("final-review-card");
  var recommendationStatus = document.getElementById("recommendation-status");
  var btnPipelineStart = document.getElementById("btn-pipeline-start");


  var extractionCard = document.getElementById("extraction-results-card");
  var extractDocTypeBadge = document.getElementById("extract-doc-type-badge");
  var metaFilename = document.getElementById("meta-filename");
  var metaPages = document.getElementById("meta-pages");
  var summaryGrid = document.getElementById("summary-grid");
  var evidenceList = document.getElementById("evidence-list");

  var policyResultsCard = document.getElementById("policy-results-card");
  var policyQueryText = document.getElementById("policy-query-text");
  var groundedClausesList = document.getElementById("grounded-clauses-list");

  var ruleEvaluationCard = document.getElementById("rule-evaluation-card");
  var ruleMetricsBanner = document.getElementById("rule-metrics-banner");
  var ruleFindingsList = document.getElementById("rule-findings-list");

  var evidenceAnalysisCard = document.getElementById("evidence-analysis-card");
  var evidenceMetricsBanner = document.getElementById("evidence-metrics-banner");
  var contradictionsList = document.getElementById("contradictions-list");
  var completenessList = document.getElementById("completeness-list");
  var consistentList = document.getElementById("consistent-list");
  var contradictionsCountBadge = document.getElementById("contradictions-count-badge");
  var completenessCountBadge = document.getElementById("completeness-count-badge");
  var consistentCountBadge = document.getElementById("consistent-count-badge");

  var statusClaimForm = document.getElementById("status-claim-form");
  var statusRepairEstimate = document.getElementById("status-repair-estimate");
  var statusDescription = document.getElementById("status-description");
  var policyStatus = document.getElementById("policy-status");
  var consistencyStatus = document.getElementById("consistency-status");

  var currentExtractedFacts = [];
  var extractedDocsMap = {};
  var uploadedDocumentNames = [];

  // ── File-name and Button State Binding ──────────────────────────
  function bindFileInput(input, nameEl, btnEl) {
    input.addEventListener("change", function () {
      if (input.files.length) {
        var fname = input.files[0].name;
        nameEl.textContent = fname;
        btnEl.disabled = false;
        if (uploadedDocumentNames.indexOf(fname) === -1) {
          uploadedDocumentNames.push(fname);
        }
      } else {
        nameEl.textContent = "";
        btnEl.disabled = true;
      }
      updateReviewPreview();
    });
  }

  bindFileInput(claimFormInput, claimFormName, btnExtractClaimForm);
  bindFileInput(repairInput, repairEstimateName, btnExtractRepair);
  if (descriptionInput) {
    descriptionInput.addEventListener("input", updateReviewPreview);
  }

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

  
  // ── Stepper UI ──────────────────────────────────────────────────
  function updateStepNode(step) {
    for (var i = 1; i <= 6; i++) {
        var node = document.getElementById("step-node-" + i);
        var line = document.getElementById("step-line-" + i);
        if (node) {
            if (i < step) { node.classList.add("completed"); node.classList.remove("active"); if (line) line.classList.add("completed"); }
            else if (i === step) { node.classList.add("active"); node.classList.remove("completed"); if (line) line.classList.remove("completed"); }
            else { node.classList.remove("active"); node.classList.remove("completed"); if (line) line.classList.remove("completed"); }
        }
    }
  }

  // Bind step updates
  if (btnExtractClaimForm) btnExtractClaimForm.addEventListener("click", () => updateStepNode(2));
  if (btnRetrievePolicy) btnRetrievePolicy.addEventListener("click", () => updateStepNode(3));
  if (btnEvaluateRules) btnEvaluateRules.addEventListener("click", () => updateStepNode(4));
  if (btnAnalyzeEvidence) btnAnalyzeEvidence.addEventListener("click", () => updateStepNode(5));

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

    if (descriptionInput && descriptionInput.value.trim()) {
      statusDescription.textContent = "Provided";
      statusDescription.className = "badge badge-received";
    } else {
      statusDescription.textContent = "Not submitted";
      statusDescription.className = "badge badge-empty";
    }
  }

  // ── Extract Document Facts via API (Milestone 3) ────────────────
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

    if (data.document && data.document.filename) {
      extractedDocsMap[data.document.filename] = {
        filename: data.document.filename,
        document_type: data.document.document_type,
        facts: data.facts || [],
      };
      if (uploadedDocumentNames.indexOf(data.document.filename) === -1) {
        uploadedDocumentNames.push(data.document.filename);
      }
    }

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

  // ── Policy Rules Evaluation (Milestone 5) ───────────────────────
  if (btnEvaluateRules) {
    btnEvaluateRules.addEventListener("click", async function () {
      if (!currentExtractedFacts || currentExtractedFacts.length === 0) {
        showFeedback("error", "Please extract facts from a document first before running policy rule evaluation.");
        return;
      }

      btnEvaluateRules.disabled = true;
      var originalText = btnEvaluateRules.textContent;
      btnEvaluateRules.textContent = "Evaluating Rules…";
      feedback.classList.add("hidden");

      var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";

      try {
        var response = await fetch("/api/evaluate-policy", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            facts: currentExtractedFacts,
            documents: uploadedDocumentNames,
            claim_id: claimIdVal || undefined,
          }),
        });

        var data = await response.json();

        if (!data.success) {
          showFeedback("error", data.error || "Failed to evaluate policy rules.");
          ruleEvaluationCard.classList.add("hidden");
        } else {
          renderRuleEvaluationResults(data);
        }
      } catch (err) {
        showFeedback("error", "Error connecting to policy rule engine: " + err.message);
        ruleEvaluationCard.classList.add("hidden");
      } finally {
        btnEvaluateRules.disabled = false;
        btnEvaluateRules.textContent = originalText;
      }
    });
  }

  function renderRuleEvaluationResults(data) {
    var summary = data.summary || {};
    ruleMetricsBanner.innerHTML = `
      <div class="rule-metric-item"><span class="badge badge-pass">✓ ${summary.pass_count || 0} PASS</span></div>
      <div class="rule-metric-item"><span class="badge badge-fail">✗ ${summary.fail_count || 0} FAIL</span></div>
      <div class="rule-metric-item"><span class="badge badge-warning">⚠ ${summary.warning_count || 0} WARNING</span></div>
      <div class="rule-metric-item"><span class="badge badge-insufficient">? ${summary.insufficient_evidence_count || 0} INSUFFICIENT</span></div>
      <div class="rule-metric-item"><span class="badge badge-na">— ${summary.not_applicable_count || 0} N/A</span></div>
      <div class="rule-metric-item" style="margin-left: auto; color: #64748b; font-size: 0.8rem;">
        Total Rules: <strong>${summary.total_rules_checked || 0}</strong>
      </div>
    `;

    ruleFindingsList.innerHTML = "";
    (data.findings || []).forEach(function (finding) {
      var card = document.createElement("div");
      var statusClass = "status-" + String(finding.status).toLowerCase();
      card.className = "rule-finding-card " + statusClass;

      // Header row
      var header = document.createElement("div");
      header.className = "finding-header-row";

      var leftMeta = document.createElement("div");
      leftMeta.className = "finding-left-meta";

      var clauseBadge = document.createElement("span");
      clauseBadge.className = "finding-clause-badge";
      clauseBadge.textContent = "Clause " + finding.clause_id;

      var catSpan = document.createElement("span");
      catSpan.className = "finding-category";
      catSpan.textContent = finding.category;

      leftMeta.appendChild(clauseBadge);
      leftMeta.appendChild(catSpan);

      var statusBadge = document.createElement("span");
      var badgeClassMap = {
        PASS: "badge-pass",
        FAIL: "badge-fail",
        WARNING: "badge-warning",
        INSUFFICIENT_EVIDENCE: "badge-insufficient",
        NOT_APPLICABLE: "badge-na",
      };
      statusBadge.className = "badge " + (badgeClassMap[finding.status] || "badge-empty");
      statusBadge.textContent = finding.status;

      header.appendChild(leftMeta);
      header.appendChild(statusBadge);

      // Title & Message
      var title = document.createElement("div");
      title.className = "finding-title-text";
      title.textContent = finding.title;

      var msg = document.createElement("div");
      msg.className = "finding-message-text";
      msg.textContent = finding.message;

      card.appendChild(header);
      card.appendChild(title);
      card.appendChild(msg);

      // Facts Used details (if any)
      if (finding.facts_used && finding.facts_used.length > 0) {
        var factsBox = document.createElement("div");
        factsBox.className = "finding-facts-used";
        var factDetails = finding.facts_used.map(function (f) {
          return f.field_name + ": " + (f.value !== null ? f.value : f.raw_value);
        }).join(" | ");
        factsBox.innerHTML = "<strong>Facts Evaluated:</strong> " + factDetails;
        card.appendChild(factsBox);
      }

      ruleFindingsList.appendChild(card);
    });

    ruleEvaluationCard.classList.remove("hidden");
    ruleEvaluationCard.scrollIntoView({ behavior: "smooth", block: "start" });

    if (policyStatus) {
      policyStatus.textContent = `${summary.total_rules_checked || 0} deterministic policy rules evaluated (${summary.pass_count || 0} PASS, ${summary.fail_count || 0} FAIL, ${summary.warning_count || 0} WARNING)`;
      policyStatus.className = "text-success font-medium";
    }
  }

  // ── Evidence Analysis (Milestone 6) ──────────────────────────────
  if (btnAnalyzeEvidence) {
    btnAnalyzeEvidence.addEventListener("click", async function () {
      var docKeys = Object.keys(extractedDocsMap);
      var payloadFacts = null;

      if (docKeys.length > 1) {
        payloadFacts = Object.values(extractedDocsMap);
      } else if (docKeys.length === 1) {
        payloadFacts = extractedDocsMap[docKeys[0]].facts;
      } else if (currentExtractedFacts && currentExtractedFacts.length > 0) {
        payloadFacts = currentExtractedFacts;
      } else {
        showFeedback("error", "Please extract facts from at least one document first before running evidence analysis.");
        return;
      }

      btnAnalyzeEvidence.disabled = true;
      var originalText = btnAnalyzeEvidence.textContent;
      btnAnalyzeEvidence.textContent = "Analyzing Evidence…";
      feedback.classList.add("hidden");

      var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";
      var docList = uploadedDocumentNames.slice();
      docKeys.forEach(function (k) {
        if (docList.indexOf(k) === -1) docList.push(k);
      });

      try {
        var response = await fetch("/api/analyze-evidence", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            facts: payloadFacts,
            documents: docList,
            claim_id: claimIdVal || undefined,
          }),
        });

        var data = await response.json();

        if (!data.success) {
          showFeedback("error", data.error || "Failed to analyze evidence.");
          evidenceAnalysisCard.classList.add("hidden");
        } else {
          renderEvidenceAnalysisResults(data);
        }
      } catch (err) {
        showFeedback("error", "Error connecting to evidence review engine: " + err.message);
        evidenceAnalysisCard.classList.add("hidden");
      } finally {
        btnAnalyzeEvidence.disabled = false;
        btnAnalyzeEvidence.textContent = originalText;
      }
    });
  }

  function renderEvidenceAnalysisResults(data) {
    var summary = data.summary || {};
    var contradictions = data.contradictions || [];
    var completeness = data.completeness || [];
    var consistentFields = data.consistent_fields || [];

    // Summary banner
    var cCount = contradictions.length;
    var cBadgeClass = cCount > 0 ? "badge-fail" : "badge-pass";
    var compPresent = summary.present_documents_count || 0;
    var compTotal = summary.total_required_documents || completeness.length;

    evidenceMetricsBanner.innerHTML = `
      <div class="evidence-metric-item">
        <span class="badge" style="background: #334155; color: #fff; font-weight: 700;">Claim Type: ${data.claim_type || "UNKNOWN"}</span>
      </div>
      <div class="evidence-metric-item">
        <span class="badge ${cBadgeClass}">⚡ ${cCount} Contradiction${cCount === 1 ? "" : "s"}</span>
      </div>
      <div class="evidence-metric-item">
        <span class="badge badge-pass">📋 ${compPresent} / ${compTotal} Required Docs</span>
      </div>
      <div class="evidence-metric-item">
        <span class="badge badge-insufficient">✓ ${consistentFields.length} Verified Match${consistentFields.length === 1 ? "" : "es"}</span>
      </div>
    `;

    // 1. Contradictions Section
    if (contradictionsCountBadge) {
      contradictionsCountBadge.textContent = `${cCount} detected`;
    }
    contradictionsList.innerHTML = "";

    if (cCount === 0) {
      var noContra = document.createElement("div");
      noContra.className = "finding-facts-used";
      noContra.style.color = "#166534";
      noContra.style.background = "#f0fdf4";
      noContra.style.borderColor = "#bbf7d0";
      noContra.innerHTML = "<strong>✓ Consistency Verified:</strong> No factual contradictions detected across submitted documents.";
      contradictionsList.appendChild(noContra);
    } else {
      contradictions.forEach(function (contra) {
        var card = document.createElement("div");
        var sev = (contra.severity || "MEDIUM").toLowerCase();
        card.className = "contradiction-card severity-" + sev;

        var header = document.createElement("div");
        header.className = "contradiction-header-row";

        var leftMeta = document.createElement("div");
        leftMeta.className = "contradiction-left-meta";

        var idBadge = document.createElement("span");
        idBadge.className = "contradiction-id-badge";
        idBadge.textContent = contra.contradiction_id || "MISMATCH";

        var catText = document.createElement("span");
        catText.className = "contradiction-category-text";
        catText.textContent = (contra.field_name || "Field").replace(/_/g, " ").toUpperCase() + " MISMATCH";

        leftMeta.appendChild(idBadge);
        leftMeta.appendChild(catText);

        var sevBadge = document.createElement("span");
        sevBadge.className = "badge badge-" + sev;
        sevBadge.textContent = (contra.severity || "MEDIUM") + " SEVERITY";

        header.appendChild(leftMeta);
        header.appendChild(sevBadge);

        // Comparison Grid
        var compGrid = document.createElement("div");
        compGrid.className = "comparison-grid";

        // Side A
        var sideA = document.createElement("div");
        sideA.className = "comparison-side";
        var valA = contra.value_a !== null && contra.value_a !== undefined ? contra.value_a : (contra.raw_value_a || "—");
        if (typeof valA === "number" && String(contra.field_name).includes("amount")) {
          valA = "₹" + Number(valA).toLocaleString();
        }
        sideA.innerHTML = `
          <div class="doc-label">
            <span>Doc A: ${contra.document_a || "Document 1"}</span>
            <span>Page ${contra.page_a || 1}</span>
          </div>
          <div class="doc-val">${valA}</div>
          <div class="doc-quote">"${contra.evidence_a || "(No direct quote)"}"</div>
        `;

        // Side B
        var sideB = document.createElement("div");
        sideB.className = "comparison-side";
        var valB = contra.value_b !== null && contra.value_b !== undefined ? contra.value_b : (contra.raw_value_b || "—");
        if (typeof valB === "number" && String(contra.field_name).includes("amount")) {
          valB = "₹" + Number(valB).toLocaleString();
        }
        sideB.innerHTML = `
          <div class="doc-label">
            <span>Doc B: ${contra.document_b || "Document 2"}</span>
            <span>Page ${contra.page_b || 1}</span>
          </div>
          <div class="doc-val">${valB}</div>
          <div class="doc-quote">"${contra.evidence_b || "(No direct quote)"}"</div>
        `;

        compGrid.appendChild(sideA);
        compGrid.appendChild(sideB);

        var msg = document.createElement("div");
        msg.className = "contradiction-message-text";
        msg.textContent = contra.message;

        card.appendChild(header);
        card.appendChild(compGrid);
        card.appendChild(msg);

        contradictionsList.appendChild(card);
      });
    }

    // 2. Completeness Section
    if (completenessCountBadge) {
      completenessCountBadge.textContent = `${completeness.length} requirements`;
    }
    completenessList.innerHTML = "";

    completeness.forEach(function (comp) {
      var card = document.createElement("div");
      var st = (comp.status || "MISSING").toLowerCase();
      card.className = "completeness-card status-" + st;

      var leftDiv = document.createElement("div");
      leftDiv.className = "completeness-left";

      var header = document.createElement("div");
      header.className = "completeness-header";

      var clauseBadge = document.createElement("span");
      clauseBadge.className = "finding-clause-badge";
      clauseBadge.textContent = "Clause " + comp.clause_id;

      var docName = document.createElement("span");
      docName.className = "completeness-doc-name";
      docName.textContent = comp.required_document;

      header.appendChild(clauseBadge);
      header.appendChild(docName);

      var msg = document.createElement("div");
      msg.className = "completeness-msg";
      msg.textContent = comp.message;

      leftDiv.appendChild(header);
      leftDiv.appendChild(msg);

      var statusBadge = document.createElement("span");
      statusBadge.className = "badge badge-" + st;
      statusBadge.textContent = comp.status;

      card.appendChild(leftDiv);
      card.appendChild(statusBadge);

      completenessList.appendChild(card);
    });

    // 3. Consistent Fields Section
    if (consistentCountBadge) {
      consistentCountBadge.textContent = `${consistentFields.length} matching`;
    }
    consistentList.innerHTML = "";

    if (consistentFields.length === 0) {
      var emptyMsg = document.createElement("div");
      emptyMsg.className = "section-subtext";
      emptyMsg.textContent = "No multi-document matching fields available for cross-verification.";
      consistentList.appendChild(emptyMsg);
    } else {
      consistentFields.forEach(function (item) {
        var chip = document.createElement("div");
        chip.className = "consistent-chip";
        var valStr = formatFactValue(item.field_name, item.value);
        chip.innerHTML = `<strong>${item.field_name.replace(/_/g, " ")}:</strong> ${valStr} <span style="opacity:0.75; font-size:0.75rem;">(${item.documents.join(" & ")})</span>`;
        consistentList.appendChild(chip);
      });
    }

    evidenceAnalysisCard.classList.remove("hidden");
    evidenceAnalysisCard.scrollIntoView({ behavior: "smooth", block: "start" });

    if (consistencyStatus) {
      if (cCount > 0) {
        consistencyStatus.textContent = `${cCount} contradiction${cCount === 1 ? "" : "s"} detected across evidence (${compPresent}/${compTotal} required documents present)`;
        consistencyStatus.className = "text-warning font-medium";
      } else {
        consistencyStatus.textContent = `All facts consistent across evidence (${compPresent}/${compTotal} required documents present)`;
        consistencyStatus.className = "text-success font-medium";
      }
    }
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

  // ── Final Review Generation (Milestone 7 / Step 6) ──────────────
  if (btnGenerateReview) {
    btnGenerateReview.addEventListener("click", async function () {
      btnGenerateReview.disabled = true;
      var originalText = btnGenerateReview.textContent;
      btnGenerateReview.textContent = "Generating Audit Report…";
      feedback.classList.add("hidden");

      var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";
      var docKeys = Object.keys(extractedDocsMap);
      var payloadFacts = null;

      if (docKeys.length > 1) {
        payloadFacts = Object.values(extractedDocsMap);
      } else if (docKeys.length === 1) {
        payloadFacts = extractedDocsMap[docKeys[0]].facts;
      } else if (currentExtractedFacts && currentExtractedFacts.length > 0) {
        payloadFacts = currentExtractedFacts;
      }

      var docList = uploadedDocumentNames.slice();
      docKeys.forEach(function (k) {
        if (docList.indexOf(k) === -1) docList.push(k);
      });

      try {
        var response = await fetch("/api/generate-review", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            facts: payloadFacts,
            documents: docList,
            claim_id: claimIdVal || undefined,
          }),
        });

        var data = await response.json();
        if (!data.success) {
          showFeedback("error", data.error || "Failed to generate audit report.");
          if (finalReviewCard) finalReviewCard.classList.add("hidden");
        } else {
          renderFinalReview(data.report);
        }
      } catch (err) {
        showFeedback("error", "Error connecting to review generator: " + err.message);
        if (finalReviewCard) finalReviewCard.classList.add("hidden");
      } finally {
        btnGenerateReview.disabled = false;
        btnGenerateReview.textContent = originalText;
      }
    });
  }

  function renderFinalReview(report) {
    updateStepNode(6);
    var statusContainer = document.getElementById("review-status-container");
    var statusBadge = document.getElementById("review-status-badge");
    var statusReason = document.getElementById("review-status-reason");
    var rec = report.recommendation || {};
    var rawStatus = rec.status || "READY_FOR_REVIEW";

    if (statusContainer) statusContainer.className = "review-status-container status-" + String(rawStatus).toLowerCase();
    if (statusBadge) statusBadge.textContent = String(rawStatus).replace(/_/g, " ");
    if (statusReason) statusReason.textContent = rec.reason || "";
    var tsEl = document.getElementById("report-timestamp");
    if (tsEl) tsEl.textContent = "Generated: " + new Date(report.generated_at).toLocaleString();

    // 1. Claim Review Summary Grid
    var summaryGrid = document.getElementById("report-summary-grid");
    if (summaryGrid) {
      summaryGrid.innerHTML = `
        <div class="fact-card"><div class="fact-label">Claim Reference</div><div class="fact-value">${report.claim_id || "N/A"}</div></div>
        <div class="fact-card"><div class="fact-label">Claim Type</div><div class="fact-value">${report.claim_type || "UNKNOWN"}</div></div>
        <div class="fact-card"><div class="fact-label">Vehicle Registration</div><div class="fact-value">${(report.claim_summary||{}).vehicle_registration || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Vehicle Make & Model</div><div class="fact-value">${(report.claim_summary||{}).vehicle_make_model || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Incident Date</div><div class="fact-value">${(report.claim_summary||{}).incident_date || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Claimed Amount</div><div class="fact-value">${(report.claim_summary||{}).claimed_amount ? '₹' + Number((report.claim_summary||{}).claimed_amount).toLocaleString() : '—'}</div></div>
        <div class="fact-card"><div class="fact-label">Documents Reviewed</div><div class="fact-value">${(report.claim_summary||{}).document_count || 0} file(s) (${(report.document_inventory||[]).join(', ')})</div></div>
      `;
    }

    // 2. WHY THIS STATUS? (1-3 Triggering Findings)
    var triggerList = document.getElementById("triggering-findings-list");
    if (triggerList) {
      triggerList.innerHTML = "";
      (rec.triggering_findings || []).forEach(function(f) {
        var item = document.createElement("div");
        var ftype = String(f.finding_type).toLowerCase();
        var styleClass = ftype.includes("missing") ? "missing" : ftype.includes("contradiction") ? "contradiction" : "policy_failure";
        item.className = "triggering-finding-item " + styleClass;
        var badgeColor = ftype.includes("missing") ? 'badge-missing' : ftype.includes("contradiction") ? 'badge-fail' : 'badge-fail';
        item.innerHTML = `
          <div class="trigger-title">
            <span>${f.title || 'Finding'}</span>
            <span class="badge ${badgeColor}">${f.severity || ''}</span>
          </div>
          <div class="trigger-detail">${f.detail || ''}</div>
          <div class="fact-raw" style="margin-top:4px;">Source: ${f.source || 'N/A'}</div>
        `;
        triggerList.appendChild(item);
      });
      if ((rec.triggering_findings || []).length === 0) {
        triggerList.innerHTML = `<div class="triggering-finding-item" style="border-left-color: #059669; background: #ecfdf5;"><div class="trigger-title"><span style="color: #065f46;">✓ Evidence Package Verified Complete & Consistent</span></div></div>`;
      }
    }

    // 3. Policy Findings Summary
    var policyMetrics = document.getElementById("report-policy-metrics");
    if (policyMetrics) {
      var pCount = report.policy_findings ? report.policy_findings.length : 0;
      var passCount = (report.policy_findings || []).filter(f => String(f.status).toUpperCase() === 'PASS').length;
      var failCount = (report.policy_findings || []).filter(f => String(f.status).toUpperCase() === 'FAIL').length;
      var warnCount = (report.policy_findings || []).filter(f => String(f.status).toUpperCase() === 'WARNING').length;
      var insufCount = (report.policy_findings || []).filter(f => String(f.status).toUpperCase() === 'INSUFFICIENT_EVIDENCE').length;
      var naCount = (report.policy_findings || []).filter(f => String(f.status).toUpperCase() === 'NOT_APPLICABLE').length;

      policyMetrics.innerHTML = `
        <div class="rule-metric-item"><span class="badge badge-pass">✓ ${passCount} PASS</span></div>
        <div class="rule-metric-item"><span class="badge badge-fail">✗ ${failCount} FAIL</span></div>
        <div class="rule-metric-item"><span class="badge badge-warning">⚠ ${warnCount} WARNING</span></div>
        <div class="rule-metric-item"><span class="badge badge-insufficient">? ${insufCount} INSUFFICIENT</span></div>
        <div class="rule-metric-item"><span class="badge badge-na">— ${naCount} N/A</span></div>
        <div class="rule-metric-item" style="color: #64748b; font-size: 0.8rem; margin-left:auto;">${pCount} deterministic rules evaluated</div>
      `;
    }

    // 4. Evidence Issues Breakdown
    var evIssues = document.getElementById("report-evidence-issues");
    if (evIssues) {
      var cCount = report.contradictions ? report.contradictions.length : 0;
      var mCount = (report.completeness_findings || []).filter(f => String(f.status).toUpperCase() === 'MISSING').length;
      var incompCount = (report.completeness_findings || []).filter(f => String(f.status).toUpperCase() === 'INCOMPLETE').length;

      evIssues.innerHTML = `
        <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
          <div class="rule-metric-item"><span class="badge ${cCount > 0 ? 'badge-fail' : 'badge-pass'}">⚡ ${cCount} Contradiction${cCount === 1 ? '' : 's'}</span></div>
          <div class="rule-metric-item"><span class="badge ${mCount > 0 ? 'badge-missing' : 'badge-pass'}">📋 ${mCount} Missing Required Document${mCount === 1 ? '' : 's'}</span></div>
          <div class="rule-metric-item"><span class="badge ${incompCount > 0 ? 'badge-warning' : 'badge-pass'}">⚠ ${incompCount} Incomplete Document${incompCount === 1 ? '' : 's'}</span></div>
        </div>
      `;
    }

    // 5. Policy References
    var clausesList = document.getElementById("report-clauses-list");
    if (clausesList) {
      clausesList.innerHTML = "";
      (report.policy_clauses || []).forEach(function(c) {
        var item = document.createElement("div");
        item.className = "report-clause-mini-card";
        item.innerHTML = `
          <div class="report-clause-mini-header">
            <span class="clause-id-badge" style="font-size:0.7rem; padding:2px 6px;">Clause ${c.clause_id}</span>
            <span>${c.title}</span>
          </div>
          <div style="color: #475569; font-size:0.8rem; line-height:1.4;">${c.text}</div>
        `;
        clausesList.appendChild(item);
      });
      if ((report.policy_clauses || []).length === 0) {
        clausesList.innerHTML = `<div class="section-subtext">No grounded clauses attached.</div>`;
      }
    }

    // 6. Evidence Provenance
    var evList = document.getElementById("report-evidence-list");
    if (evList) {
      evList.innerHTML = "";
      (report.evidence_references || []).forEach(function(e) {
        var item = document.createElement("div");
        item.className = "report-clause-mini-card";
        item.innerHTML = `
          <div class="report-clause-mini-header">
            <span class="page-pill">Page ${e.page_number}</span>
            <span style="color:#0f172a; font-weight:600;">${e.document_name}</span>
            <span style="font-weight:400; color:#64748b;">(${e.field_name ? e.field_name.replace(/_/g, " ") : "Evidence"})</span>
          </div>
          <div class="quote-box" style="margin-top:6px; font-size:0.78rem;">${e.evidence_text}</div>
        `;
        evList.appendChild(item);
      });
      if ((report.evidence_references || []).length === 0) {
        evList.innerHTML = `<div class="section-subtext">No direct quotations attached.</div>`;
      }
    }

    // 7. Recommended Action
    var actionText = document.getElementById("report-action-text");
    if (actionText) actionText.textContent = rec.recommended_action || "Evidence package is sufficiently complete and internally consistent for standard human review.";

    // 8. Disclaimer
    var discEl = document.getElementById("report-disclaimer-text");
    if (discEl && report.disclaimer) discEl.textContent = report.disclaimer;

    if (finalReviewCard) {
      finalReviewCard.classList.remove("hidden");
      finalReviewCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (recommendationStatus) {
      recommendationStatus.textContent = String(rawStatus).replace(/_/g, " ");
      recommendationStatus.className = "font-medium " + (rawStatus === "READY_FOR_REVIEW" ? "text-success" : (rawStatus.includes("ESCALATE") ? "text-error" : "text-warning"));
    }
  }

  // ── Run Full Pipeline Handler ───────────────────────────────────
  if (btnPipelineStart) {
    btnPipelineStart.addEventListener("click", function () {
      if (claimFormInput.files.length) {
        btnExtractClaimForm.click();
      }
      if (repairInput.files.length) {
        btnExtractRepair.click();
      }
      setTimeout(function() {
        if (btnGenerateReview) btnGenerateReview.click();
      }, 600);
    });
  }

})();

