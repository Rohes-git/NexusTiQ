/* ================================================================
   ClaimLens — app.js
   Handles:
   - Canonical Demo Claims loading (CLM-001, CLM-002, CLM-003)
   - Document fact extraction via Gemini (Milestone 3)
   - Semantic policy retrieval & clause grounding (Milestone 4)
   - Deterministic policy rule evaluation (Milestone 5)
   - Cross-document contradiction & completeness analysis (Milestone 6)
   - Structured audit report & review recommendation (Milestone 7)
   - Unified 6-step review pipeline execution
   No external JS libraries.
   ================================================================ */

(function () {
  "use strict";

  // ── DOM References ──────────────────────────────────────────────
  var form = document.getElementById("claim-form");
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

  var finalReviewCard = document.getElementById("final-review-card");

  var statusClaimForm = document.getElementById("status-claim-form");
  var statusRepairEstimate = document.getElementById("status-repair-estimate");
  var statusDescription = document.getElementById("status-description");
  var policyStatus = document.getElementById("policy-status");
  var consistencyStatus = document.getElementById("consistency-status");
  var recommendationStatus = document.getElementById("recommendation-status");

  // In-memory state
  var currentExtractedFacts = [];
  var extractedDocsMap = {};
  var uploadedDocumentNames = [];

  // ── Helper: Feedback Banner ─────────────────────────────────────
  function showFeedback(type, message) {
    if (!feedback) return;
    feedback.className = "feedback " + type;
    feedback.textContent = message;
    feedback.classList.remove("hidden");
  }

  function hideFeedback() {
    if (feedback) feedback.classList.add("hidden");
  }

  // ── Helper: Format Values ───────────────────────────────────────
  function formatFactValue(fieldName, value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    if (String(fieldName).includes("amount") && !isNaN(Number(value))) {
      return "₹" + Number(value).toLocaleString();
    }
    return String(value);
  }

  // ── Helper: Get Facts Payload ───────────────────────────────────
  function getPayloadFacts() {
    var docKeys = Object.keys(extractedDocsMap);
    if (docKeys.length > 1) {
      return Object.values(extractedDocsMap);
    }
    if (docKeys.length === 1) {
      return extractedDocsMap[docKeys[0]].facts || [];
    }
    if (currentExtractedFacts && currentExtractedFacts.length > 0) {
      return currentExtractedFacts;
    }
    return null;
  }

  function getDocumentList() {
    var docList = uploadedDocumentNames.slice();
    Object.keys(extractedDocsMap).forEach(function (k) {
      if (docList.indexOf(k) === -1) docList.push(k);
    });
    return docList;
  }

  // ── Stepper UI ──────────────────────────────────────────────────
  function updateStepNode(step) {
    for (var i = 1; i <= 6; i++) {
      var node = document.getElementById("step-node-" + i);
      var line = document.getElementById("step-line-" + i);
      if (node) {
        if (i < step) {
          node.classList.add("completed");
          node.classList.remove("active");
          if (line) line.classList.add("completed");
        } else if (i === step) {
          node.classList.add("active");
          node.classList.remove("completed");
          if (line) line.classList.remove("completed");
        } else {
          node.classList.remove("active");
          node.classList.remove("completed");
          if (line) line.classList.remove("completed");
        }
      }
    }
  }

  // ── File-name and Button State Binding ──────────────────────────
  function bindFileInput(input, nameEl, btnEl) {
    if (!input) return;
    input.addEventListener("change", function () {
      if (input.files.length) {
        var fname = input.files[0].name;
        if (nameEl) nameEl.textContent = fname;
        if (btnEl) btnEl.disabled = false;
        if (uploadedDocumentNames.indexOf(fname) === -1) {
          uploadedDocumentNames.push(fname);
        }
      } else {
        if (nameEl) nameEl.textContent = "";
        if (btnEl) btnEl.disabled = true;
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

  // ── Live Review Preview Updates ─────────────────────────────────
  function updateReviewPreview() {
    var hasClaimForm = (claimFormInput && claimFormInput.files && claimFormInput.files.length > 0) ||
      uploadedDocumentNames.some(function (d) { return d.indexOf("claim_form") !== -1; });

    var hasRepairEstimate = (repairInput && repairInput.files && repairInput.files.length > 0) ||
      uploadedDocumentNames.some(function (d) { return d.indexOf("repair_estimate") !== -1 || d.indexOf("fir") !== -1; });

    var hasDesc = (descriptionInput && descriptionInput.value.trim().length > 0);

    if (statusClaimForm) {
      statusClaimForm.textContent = hasClaimForm ? "Received" : "Not submitted";
      statusClaimForm.className = "badge " + (hasClaimForm ? "badge-received" : "badge-empty");
    }

    if (statusRepairEstimate) {
      statusRepairEstimate.textContent = hasRepairEstimate ? "Received" : "Not submitted";
      statusRepairEstimate.className = "badge " + (hasRepairEstimate ? "badge-received" : "badge-empty");
    }

    if (statusDescription) {
      statusDescription.textContent = hasDesc ? "Provided" : "Not submitted";
      statusDescription.className = "badge " + (hasDesc ? "badge-received" : "badge-empty");
    }

    // Reset downstream cards if user modifies inputs manually
    if (finalReviewCard) finalReviewCard.classList.add("hidden");
    if (recommendationStatus) {
      recommendationStatus.textContent = "Complete the review pipeline to generate the final report.";
      recommendationStatus.className = "muted";
    }
    if (policyStatus) {
      policyStatus.textContent = "Awaiting deterministic policy evaluation";
      policyStatus.className = "muted";
    }
    if (consistencyStatus) {
      consistencyStatus.textContent = "Awaiting multi-document cross-check";
      consistencyStatus.className = "muted";
    }
  }

  // ── Canonical Demo Claims Loader ─────────────────────────────────
  async function applyDemoClaim(claimId) {
    hideFeedback();
    showFeedback("info", "Loading canonical data for " + claimId + "…");

    try {
      var response = await fetch("/api/demo-claim/" + encodeURIComponent(claimId));
      if (!response.ok) {
        throw new Error("Failed to load demo claim (" + response.status + ")");
      }
      var data = await response.json();

      // 1. Populate metadata & form inputs
      if (claimIdInput) claimIdInput.value = data.claim_id || claimId;
      if (descriptionInput) descriptionInput.value = data.incident_description || "";

      // 2. Set document names
      uploadedDocumentNames = (data.documents || []).slice();

      // 3. Populate extracted facts map
      extractedDocsMap = {};
      (data.extracted_documents || []).forEach(function (doc) {
        var dName = doc.filename || doc.document_name || "document.pdf";
        extractedDocsMap[dName] = {
          filename: dName,
          document_type: doc.document_type || "claim_form",
          page_count: doc.page_count || 1,
          facts: doc.facts || [],
        };
      });

      currentExtractedFacts = (data.all_facts || []).slice();

      // 4. Update file labels and status badges
      var hasCf = uploadedDocumentNames.some(function (d) { return d.indexOf("claim_form") !== -1; });
      var hasRe = uploadedDocumentNames.some(function (d) { return d.indexOf("repair_estimate") !== -1; });
      var hasFir = uploadedDocumentNames.some(function (d) { return d.indexOf("fir") !== -1; });

      if (claimFormName) {
        claimFormName.textContent = hasCf ? "claim_form.pdf (Canonical Demo)" : "";
      }
      if (btnExtractClaimForm) {
        btnExtractClaimForm.disabled = !hasCf;
      }
      if (statusClaimForm) {
        statusClaimForm.textContent = hasCf ? "Received" : "Not submitted";
        statusClaimForm.className = "badge " + (hasCf ? "badge-received" : "badge-empty");
      }

      if (repairEstimateName) {
        if (hasRe) {
          repairEstimateName.textContent = "repair_estimate.pdf (Canonical Demo)";
        } else if (hasFir) {
          repairEstimateName.textContent = "fir.pdf (Canonical Demo)";
        } else {
          repairEstimateName.textContent = "";
        }
      }
      if (btnExtractRepair) {
        btnExtractRepair.disabled = !(hasRe || hasFir);
      }
      if (statusRepairEstimate) {
        statusRepairEstimate.textContent = (hasRe || hasFir) ? "Received" : "Not submitted";
        statusRepairEstimate.className = "badge " + ((hasRe || hasFir) ? "badge-received" : "badge-empty");
      }

      if (statusDescription) {
        statusDescription.textContent = data.incident_description ? "Provided" : "Not submitted";
        statusDescription.className = "badge " + (data.incident_description ? "badge-received" : "badge-empty");
      }

      // 5. Hide downstream cards for fresh execution
      if (policyResultsCard) policyResultsCard.classList.add("hidden");
      if (ruleEvaluationCard) ruleEvaluationCard.classList.add("hidden");
      if (evidenceAnalysisCard) evidenceAnalysisCard.classList.add("hidden");
      if (finalReviewCard) finalReviewCard.classList.add("hidden");

      if (policyStatus) {
        policyStatus.textContent = "Awaiting deterministic policy evaluation";
        policyStatus.className = "muted";
      }
      if (consistencyStatus) {
        consistencyStatus.textContent = "Awaiting multi-document cross-check";
        consistencyStatus.className = "muted";
      }
      if (recommendationStatus) {
        recommendationStatus.textContent = "Click 'Run Full Review Pipeline' or step through review.";
        recommendationStatus.className = "muted";
      }

      // 6. Render Step 2 Extraction Preview from canonical data
      if (data.primary_extraction) {
        renderExtractionResults(data.primary_extraction);
        updateStepNode(2);
      }

      showFeedback(
        "info",
        "⚡ Preloaded canonical demo claim " + claimId + " (" + data.description + "). Ready for review."
      );

    } catch (err) {
      showFeedback("error", "Failed to load demo claim data: " + err.message);
    }
  }

  // Bind Demo Buttons
  var btnDemo1 = document.getElementById("btn-demo-clm-001");
  var btnDemo2 = document.getElementById("btn-demo-clm-002");
  var btnDemo3 = document.getElementById("btn-demo-clm-003");

  if (btnDemo1) btnDemo1.addEventListener("click", function () { applyDemoClaim("CLM-001"); });
  if (btnDemo2) btnDemo2.addEventListener("click", function () { applyDemoClaim("CLM-002"); });
  if (btnDemo3) btnDemo3.addEventListener("click", function () { applyDemoClaim("CLM-003"); });

  // ── Extract Document Facts via API (Milestone 3) ────────────────
  async function extractDocumentFacts(file, triggerBtn) {
    if (!file) return;

    if (triggerBtn) triggerBtn.disabled = true;
    var originalText = triggerBtn ? triggerBtn.textContent : "";
    if (triggerBtn) triggerBtn.textContent = "Extracting…";
    hideFeedback();

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
        if (extractionCard) extractionCard.classList.add("hidden");
      } else {
        renderExtractionResults(data);
        updateStepNode(2);
      }
    } catch (err) {
      showFeedback("error", "Failed to connect to extraction service. " + err.message);
      if (extractionCard) extractionCard.classList.add("hidden");
    } finally {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.textContent = originalText;
      }
    }
  }

  if (btnExtractClaimForm) {
    btnExtractClaimForm.addEventListener("click", function () {
      if (claimFormInput && claimFormInput.files && claimFormInput.files.length > 0) {
        extractDocumentFacts(claimFormInput.files[0], btnExtractClaimForm);
      } else if (extractedDocsMap["claim_form.pdf"]) {
        renderExtractionResults({
          document: extractedDocsMap["claim_form.pdf"],
          facts: extractedDocsMap["claim_form.pdf"].facts,
        });
        updateStepNode(2);
      }
    });
  }

  if (btnExtractRepair) {
    btnExtractRepair.addEventListener("click", function () {
      if (repairInput && repairInput.files && repairInput.files.length > 0) {
        extractDocumentFacts(repairInput.files[0], btnExtractRepair);
      } else if (extractedDocsMap["repair_estimate.pdf"]) {
        renderExtractionResults({
          document: extractedDocsMap["repair_estimate.pdf"],
          facts: extractedDocsMap["repair_estimate.pdf"].facts,
        });
        updateStepNode(2);
      } else if (extractedDocsMap["fir.pdf"]) {
        renderExtractionResults({
          document: extractedDocsMap["fir.pdf"],
          facts: extractedDocsMap["fir.pdf"].facts,
        });
        updateStepNode(2);
      }
    });
  }

  // ── Render Structured Facts & Evidence ──────────────────────────
  function renderExtractionResults(data) {
    if (!data || !data.document) return;
    currentExtractedFacts = data.facts || [];

    if (metaFilename) metaFilename.textContent = data.document.filename || "document.pdf";
    if (metaPages) metaPages.textContent = data.document.page_count || 1;

    var fname = data.document.filename || "document.pdf";
    extractedDocsMap[fname] = {
      filename: fname,
      document_type: data.document.document_type || "claim_form",
      page_count: data.document.page_count || 1,
      facts: data.facts || [],
    };
    if (uploadedDocumentNames.indexOf(fname) === -1) {
      uploadedDocumentNames.push(fname);
    }

    var typeLabels = {
      claim_form: "Claim Form",
      repair_estimate: "Repair Estimate",
      fir: "First Information Report (FIR)",
      unknown: "Unknown Document",
    };
    if (extractDocTypeBadge) {
      extractDocTypeBadge.textContent = typeLabels[data.document.document_type] || data.document.document_type;
    }

    // Render Summary Grid
    if (summaryGrid) {
      summaryGrid.innerHTML = "";
      (data.facts || []).forEach(function (fact) {
        var card = document.createElement("div");
        card.className = "fact-card";

        var label = document.createElement("div");
        label.className = "fact-label";
        label.textContent = (fact.field_name || "field").replace(/_/g, " ");

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
    }

    // Render Evidence Provenance List
    if (evidenceList) {
      evidenceList.innerHTML = "";
      (data.facts || []).forEach(function (fact) {
        var item = document.createElement("div");
        item.className = "evidence-card" + (fact.evidence_valid ? "" : " unverified");

        var header = document.createElement("div");
        header.className = "evidence-card-header";

        var title = document.createElement("span");
        title.className = "evidence-field-name";
        title.textContent = (fact.field_name || "field").replace(/_/g, " ");

        var pills = document.createElement("div");
        pills.className = "evidence-meta-pills";

        var pagePill = document.createElement("span");
        pagePill.className = "page-pill";
        pagePill.textContent = "Page " + (fact.page_number || 1);
        pills.appendChild(pagePill);

        var conf = fact.confidence !== undefined ? Math.round(fact.confidence * 100) : 95;
        var confPill = document.createElement("span");
        confPill.className = "conf-pill";
        confPill.textContent = conf + "% confidence";
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
    }

    if (extractionCard) {
      extractionCard.classList.remove("hidden");
    }
  }

  // ── Policy Retrieval (Milestone 4 / Step 3) ─────────────────────
  async function runPolicyRetrieval() {
    var payloadFacts = getPayloadFacts();
    var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";

    if (!payloadFacts && !claimIdVal) {
      showFeedback("error", "Please extract facts from a document first before retrieving policy clauses.");
      return null;
    }

    if (btnRetrievePolicy) {
      btnRetrievePolicy.disabled = true;
      btnRetrievePolicy.textContent = "Retrieving Policy…";
    }
    hideFeedback();

    try {
      var response = await fetch("/api/retrieve-policy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          facts: payloadFacts,
          claim_id: claimIdVal || undefined,
          top_k: 5,
        }),
      });

      var data = await response.json();

      if (!data.success) {
        showFeedback("error", data.error || "Failed to retrieve relevant policy clauses.");
        if (policyResultsCard) policyResultsCard.classList.add("hidden");
        return null;
      } else {
        renderPolicyResults(data);
        updateStepNode(3);
        return data;
      }
    } catch (err) {
      showFeedback("error", "Error connecting to policy retrieval service: " + err.message);
      if (policyResultsCard) policyResultsCard.classList.add("hidden");
      return null;
    } finally {
      if (btnRetrievePolicy) {
        btnRetrievePolicy.disabled = false;
        btnRetrievePolicy.textContent = "🔍 STEP 3: Ground Policy Clauses";
      }
    }
  }

  if (btnRetrievePolicy) {
    btnRetrievePolicy.addEventListener("click", runPolicyRetrieval);
  }

  function renderPolicyResults(data) {
    if (policyQueryText) policyQueryText.textContent = data.query || "(No query text)";
    if (groundedClausesList) {
      groundedClausesList.innerHTML = "";

      (data.clauses || []).forEach(function (clause) {
        var card = document.createElement("div");
        card.className = "grounded-clause-card";

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
        var pct = Math.round((clause.similarity_score || 0.8) * 100);
        relevancePill.textContent = pct + "% Relevance";

        header.appendChild(leftMeta);
        header.appendChild(relevancePill);

        var title = document.createElement("div");
        title.className = "clause-title-text";
        title.textContent = clause.title;

        var quoteBox = document.createElement("div");
        quoteBox.className = "policy-quote-box";
        quoteBox.textContent = clause.text;

        var reasonBox = document.createElement("div");
        reasonBox.className = "grounding-reason-box";
        reasonBox.innerHTML = "<strong>Factual Rationale:</strong>&nbsp;" + (clause.reason || "");

        card.appendChild(header);
        card.appendChild(title);
        card.appendChild(quoteBox);
        card.appendChild(reasonBox);

        groundedClausesList.appendChild(card);
      });
    }

    if (policyResultsCard) {
      policyResultsCard.classList.remove("hidden");
    }

    if (policyStatus) {
      policyStatus.textContent = (data.clauses ? data.clauses.length : 0) + " policy clauses grounded via vector retrieval";
      policyStatus.className = "text-success font-medium";
    }
  }

  // ── Policy Rules Evaluation (Milestone 5 / Step 4) ──────────────
  async function runRuleEvaluation() {
    var payloadFacts = getPayloadFacts();
    var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";
    var docList = getDocumentList();

    if (!payloadFacts && !claimIdVal) {
      showFeedback("error", "Please extract facts from a document first before running policy rule evaluation.");
      return null;
    }

    if (btnEvaluateRules) {
      btnEvaluateRules.disabled = true;
      btnEvaluateRules.textContent = "Evaluating Rules…";
    }
    hideFeedback();

    try {
      var response = await fetch("/api/evaluate-policy", {
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
        showFeedback("error", data.error || "Failed to evaluate policy rules.");
        if (ruleEvaluationCard) ruleEvaluationCard.classList.add("hidden");
        return null;
      } else {
        renderRuleEvaluationResults(data);
        updateStepNode(4);
        return data;
      }
    } catch (err) {
      showFeedback("error", "Error connecting to policy rule engine: " + err.message);
      if (ruleEvaluationCard) ruleEvaluationCard.classList.add("hidden");
      return null;
    } finally {
      if (btnEvaluateRules) {
        btnEvaluateRules.disabled = false;
        btnEvaluateRules.textContent = "⚖️ STEP 4: Evaluate Policy Rules";
      }
    }
  }

  if (btnEvaluateRules) {
    btnEvaluateRules.addEventListener("click", runRuleEvaluation);
  }

  function renderRuleEvaluationResults(data) {
    var summary = data.summary || {};
    if (ruleMetricsBanner) {
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
    }

    if (ruleFindingsList) {
      ruleFindingsList.innerHTML = "";
      (data.findings || []).forEach(function (finding) {
        var card = document.createElement("div");
        var statusClass = "status-" + String(finding.status).toLowerCase();
        card.className = "rule-finding-card " + statusClass;

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

        var title = document.createElement("div");
        title.className = "finding-title-text";
        title.textContent = finding.title;

        var msg = document.createElement("div");
        msg.className = "finding-message-text";
        msg.textContent = finding.message;

        card.appendChild(header);
        card.appendChild(title);
        card.appendChild(msg);

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
    }

    if (ruleEvaluationCard) {
      ruleEvaluationCard.classList.remove("hidden");
    }

    if (policyStatus) {
      policyStatus.textContent = `${summary.total_rules_checked || 0} deterministic policy rules evaluated (${summary.pass_count || 0} PASS, ${summary.fail_count || 0} FAIL, ${summary.warning_count || 0} WARNING)`;
      policyStatus.className = "text-success font-medium";
    }
  }

  // ── Evidence Analysis (Milestone 6 / Step 5) ────────────────────
  async function runEvidenceAnalysis() {
    var payloadFacts = getPayloadFacts();
    var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";
    var docList = getDocumentList();

    if (!payloadFacts && !claimIdVal) {
      showFeedback("error", "Please extract facts from at least one document first before running evidence analysis.");
      return null;
    }

    if (btnAnalyzeEvidence) {
      btnAnalyzeEvidence.disabled = true;
      btnAnalyzeEvidence.textContent = "Analyzing Evidence…";
    }
    hideFeedback();

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
        if (evidenceAnalysisCard) evidenceAnalysisCard.classList.add("hidden");
        return null;
      } else {
        renderEvidenceAnalysisResults(data);
        updateStepNode(5);
        return data;
      }
    } catch (err) {
      showFeedback("error", "Error connecting to evidence review engine: " + err.message);
      if (evidenceAnalysisCard) evidenceAnalysisCard.classList.add("hidden");
      return null;
    } finally {
      if (btnAnalyzeEvidence) {
        btnAnalyzeEvidence.disabled = false;
        btnAnalyzeEvidence.textContent = "🔎 STEP 5: Analyze Evidence Contradictions";
      }
    }
  }

  if (btnAnalyzeEvidence) {
    btnAnalyzeEvidence.addEventListener("click", runEvidenceAnalysis);
  }

  function renderEvidenceAnalysisResults(data) {
    var summary = data.summary || {};
    var contradictions = data.contradictions || [];
    var completeness = data.completeness || [];
    var consistentFields = data.consistent_fields || [];

    var cCount = contradictions.length;
    var cBadgeClass = cCount > 0 ? "badge-fail" : "badge-pass";
    var compPresent = summary.present_documents_count || 0;
    var compTotal = summary.total_required_documents || completeness.length;

    if (evidenceMetricsBanner) {
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
    }

    if (contradictionsCountBadge) {
      contradictionsCountBadge.textContent = `${cCount} detected`;
    }
    if (contradictionsList) {
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

          var compGrid = document.createElement("div");
          compGrid.className = "comparison-grid";

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
    }

    if (completenessCountBadge) {
      completenessCountBadge.textContent = `${completeness.length} requirements`;
    }
    if (completenessList) {
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
    }

    if (consistentCountBadge) {
      consistentCountBadge.textContent = `${consistentFields.length} matching`;
    }
    if (consistentList) {
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
          chip.innerHTML = `<strong>${(item.field_name || "field").replace(/_/g, " ")}:</strong> ${valStr} <span style="opacity:0.75; font-size:0.75rem;">(${item.documents ? item.documents.join(" & ") : "Dossier"})</span>`;
          consistentList.appendChild(chip);
        });
      }
    }

    if (evidenceAnalysisCard) {
      evidenceAnalysisCard.classList.remove("hidden");
    }

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

  // ── Final Review Generation (Milestone 7 / Step 6) ──────────────
  async function runReviewGeneration() {
    var payloadFacts = getPayloadFacts();
    var claimIdVal = claimIdInput ? claimIdInput.value.trim() : "";
    var docList = getDocumentList();

    if (btnGenerateReview) {
      btnGenerateReview.disabled = true;
      btnGenerateReview.textContent = "Generating Audit Report…";
    }
    hideFeedback();

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
        return null;
      } else {
        renderFinalReview(data.report);
        updateStepNode(6);
        return data.report;
      }
    } catch (err) {
      showFeedback("error", "Error connecting to review generator: " + err.message);
      if (finalReviewCard) finalReviewCard.classList.add("hidden");
      return null;
    } finally {
      if (btnGenerateReview) {
        btnGenerateReview.disabled = false;
        btnGenerateReview.textContent = "📋 STEP 6: Generate Final Review";
      }
    }
  }

  if (btnGenerateReview) {
    btnGenerateReview.addEventListener("click", runReviewGeneration);
  }

  function renderFinalReview(report) {
    if (!report) return;
    var statusContainer = document.getElementById("review-status-container");
    var statusBadge = document.getElementById("review-status-badge");
    var statusReason = document.getElementById("review-status-reason");
    var rec = report.recommendation || {};
    var rawStatus = rec.status || "READY_FOR_REVIEW";

    if (statusContainer) {
      statusContainer.className = "review-status-container status-" + String(rawStatus).toLowerCase();
    }
    if (statusBadge) {
      statusBadge.textContent = String(rawStatus).replace(/_/g, " ");
    }
    if (statusReason) {
      statusReason.textContent = rec.reason || "";
    }
    var tsEl = document.getElementById("report-timestamp");
    if (tsEl) {
      tsEl.textContent = "Generated: " + new Date(report.generated_at).toLocaleString();
    }

    // 1. Claim Review Summary Grid
    var repSummaryGrid = document.getElementById("report-summary-grid");
    if (repSummaryGrid) {
      var summary = report.claim_summary || {};
      var claimedStr = summary.claimed_amount ? "₹" + Number(summary.claimed_amount).toLocaleString() : "—";
      var docCount = summary.document_count || (report.document_inventory || []).length;
      var docNamesStr = (report.document_inventory || []).join(", ");

      repSummaryGrid.innerHTML = `
        <div class="fact-card"><div class="fact-label">Claim Reference</div><div class="fact-value">${report.claim_id || "N/A"}</div></div>
        <div class="fact-card"><div class="fact-label">Claim Type</div><div class="fact-value">${report.claim_type || summary.claim_type || "UNKNOWN"}</div></div>
        <div class="fact-card"><div class="fact-label">Vehicle Registration</div><div class="fact-value">${summary.vehicle_registration || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Vehicle Make & Model</div><div class="fact-value">${summary.vehicle_make_model || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Incident Date</div><div class="fact-value">${summary.incident_date || "—"}</div></div>
        <div class="fact-card"><div class="fact-label">Claimed Amount</div><div class="fact-value">${claimedStr}</div></div>
        <div class="fact-card"><div class="fact-label">Documents Reviewed</div><div class="fact-value">${docCount} file(s)${docNamesStr ? " (" + docNamesStr + ")" : ""}</div></div>
      `;
    }

    // 2. WHY THIS STATUS? (Triggering Findings)
    var triggerList = document.getElementById("triggering-findings-list");
    if (triggerList) {
      triggerList.innerHTML = "";
      var tFindings = rec.triggering_findings || [];
      if (tFindings.length > 0) {
        tFindings.forEach(function (f) {
          var item = document.createElement("div");
          var ftype = String(f.finding_type).toLowerCase();
          var styleClass = ftype.includes("missing") ? "missing" : (ftype.includes("contradiction") ? "contradiction" : "policy_failure");
          item.className = "triggering-finding-item " + styleClass;
          var badgeColor = ftype.includes("missing") ? "badge-missing" : "badge-fail";
          item.innerHTML = `
            <div class="trigger-title">
              <span>${f.title || "Finding"}</span>
              <span class="badge ${badgeColor}">${f.severity || ""}</span>
            </div>
            <div class="trigger-detail">${f.detail || ""}</div>
            <div class="fact-raw" style="margin-top:4px;">Source: ${f.source || "Policy Evaluation"}</div>
          `;
          triggerList.appendChild(item);
        });
      } else {
        triggerList.innerHTML = `<div class="triggering-finding-item" style="border-left-color: #059669; background: #ecfdf5;"><div class="trigger-title"><span style="color: #065f46;">✓ Evidence Package Verified Complete & Consistent</span></div></div>`;
      }
    }

    // 3. Policy Findings Summary
    var policyMetrics = document.getElementById("report-policy-metrics");
    if (policyMetrics) {
      var pFindings = report.policy_findings || [];
      var passCount = pFindings.filter(function (f) { return String(f.status).toUpperCase() === "PASS"; }).length;
      var failCount = pFindings.filter(function (f) { return String(f.status).toUpperCase() === "FAIL"; }).length;
      var warnCount = pFindings.filter(function (f) { return String(f.status).toUpperCase() === "WARNING"; }).length;
      var insufCount = pFindings.filter(function (f) { return String(f.status).toUpperCase() === "INSUFFICIENT_EVIDENCE"; }).length;
      var naCount = pFindings.filter(function (f) { return String(f.status).toUpperCase() === "NOT_APPLICABLE"; }).length;

      policyMetrics.innerHTML = `
        <div class="rule-metric-item"><span class="badge badge-pass">✓ ${passCount} PASS</span></div>
        <div class="rule-metric-item"><span class="badge badge-fail">✗ ${failCount} FAIL</span></div>
        <div class="rule-metric-item"><span class="badge badge-warning">⚠ ${warnCount} WARNING</span></div>
        <div class="rule-metric-item"><span class="badge badge-insufficient">? ${insufCount} INSUFFICIENT</span></div>
        <div class="rule-metric-item"><span class="badge badge-na">— ${naCount} N/A</span></div>
        <div class="rule-metric-item" style="color: #64748b; font-size: 0.8rem; margin-left:auto;">${pFindings.length} deterministic rules evaluated</div>
      `;
    }

    // 4. Evidence Issues Breakdown
    var evIssues = document.getElementById("report-evidence-issues");
    if (evIssues) {
      var cCount = (report.contradictions || []).length;
      var mCount = (report.completeness_findings || []).filter(function (f) { return String(f.status).toUpperCase() === "MISSING"; }).length;
      var incompCount = (report.completeness_findings || []).filter(function (f) { return String(f.status).toUpperCase() === "INCOMPLETE"; }).length;

      evIssues.innerHTML = `
        <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
          <div class="rule-metric-item"><span class="badge ${cCount > 0 ? "badge-fail" : "badge-pass"}">⚡ ${cCount} Contradiction${cCount === 1 ? "" : "s"}</span></div>
          <div class="rule-metric-item"><span class="badge ${mCount > 0 ? "badge-missing" : "badge-pass"}">📋 ${mCount} Missing Required Document${mCount === 1 ? "" : "s"}</span></div>
          <div class="rule-metric-item"><span class="badge ${incompCount > 0 ? "badge-warning" : "badge-pass"}">⚠ ${incompCount} Incomplete Document${incompCount === 1 ? "" : "s"}</span></div>
        </div>
      `;
    }

    // 5. Policy References
    var clausesList = document.getElementById("report-clauses-list");
    if (clausesList) {
      clausesList.innerHTML = "";
      var clauses = report.policy_clauses || [];
      if (clauses.length > 0) {
        clauses.forEach(function (c) {
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
      } else {
        clausesList.innerHTML = `<div class="section-subtext">No grounded clauses attached.</div>`;
      }
    }

    // 6. Evidence Provenance
    var repEvList = document.getElementById("report-evidence-list");
    if (repEvList) {
      repEvList.innerHTML = "";
      var refs = report.evidence_references || [];
      if (refs.length > 0) {
        refs.forEach(function (e) {
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
          repEvList.appendChild(item);
        });
      } else {
        repEvList.innerHTML = `<div class="section-subtext">No direct quotations attached.</div>`;
      }
    }

    // 7. Recommended Action
    var actionText = document.getElementById("report-action-text");
    if (actionText) {
      actionText.textContent = rec.recommended_action || "Evidence package is sufficiently complete and internally consistent for standard human review.";
    }

    // 8. Disclaimer
    var discEl = document.getElementById("report-disclaimer-text");
    if (discEl && report.disclaimer) {
      discEl.textContent = report.disclaimer;
    }

    if (finalReviewCard) {
      finalReviewCard.classList.remove("hidden");
      finalReviewCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (recommendationStatus) {
      recommendationStatus.textContent = String(rawStatus).replace(/_/g, " ");
      recommendationStatus.className = "font-medium " + (rawStatus === "READY_FOR_REVIEW" ? "text-success" : (rawStatus.includes("ESCALATE") ? "text-error" : "text-warning"));
    }
  }

  // ── Run Full Review Pipeline (Steps 2–6) ─────────────────────────
  async function runFullPipeline() {
    if (!btnPipelineStart) return;

    btnPipelineStart.disabled = true;
    var originalText = btnPipelineStart.textContent;
    btnPipelineStart.textContent = "⚙️ Running Review Pipeline (Steps 2–6)…";
    hideFeedback();

    try {
      // 1. If files are in input elements and not extracted, extract them
      if (claimFormInput && claimFormInput.files && claimFormInput.files.length > 0 && !extractedDocsMap[claimFormInput.files[0].name]) {
        updateStepNode(2);
        await extractDocumentFacts(claimFormInput.files[0], btnExtractClaimForm);
      }
      if (repairInput && repairInput.files && repairInput.files.length > 0 && !extractedDocsMap[repairInput.files[0].name]) {
        updateStepNode(2);
        await extractDocumentFacts(repairInput.files[0], btnExtractRepair);
      }

      // 2. Step 3: Ground Policy
      updateStepNode(3);
      await runPolicyRetrieval();

      // 3. Step 4: Evaluate Rules
      updateStepNode(4);
      await runRuleEvaluation();

      // 4. Step 5: Analyze Evidence
      updateStepNode(5);
      await runEvidenceAnalysis();

      // 5. Step 6: Generate Final Review
      updateStepNode(6);
      await runReviewGeneration();

    } catch (err) {
      showFeedback("error", "Pipeline execution encountered an error: " + err.message);
    } finally {
      btnPipelineStart.disabled = false;
      btnPipelineStart.textContent = originalText;
    }
  }

  if (btnPipelineStart) {
    btnPipelineStart.addEventListener("click", runFullPipeline);
  }

})();
