/* ================================================================
   ClaimLens — app.js
   Handles form submission, file-name display, and preview updates.
   No external dependencies.
   ================================================================ */

(function () {
  "use strict";

  // ── DOM references ──────────────────────────────────────────────
  const form = document.getElementById("claim-form");
  const reviewBtn = document.getElementById("review-btn");
  const feedback = document.getElementById("submit-feedback");

  const claimFormInput = document.getElementById("claim-form-file");
  const repairInput = document.getElementById("repair-estimate-file");
  const descriptionInput = document.getElementById("incident-description");

  const claimFormName = document.getElementById("claim-form-name");
  const repairEstimateName = document.getElementById("repair-estimate-name");

  const statusClaimForm = document.getElementById("status-claim-form");
  const statusRepairEstimate = document.getElementById("status-repair-estimate");
  const statusDescription = document.getElementById("status-description");

  // ── File-name display ──────────────────────────────────────────
  function bindFileDisplay(input, nameEl) {
    input.addEventListener("change", function () {
      if (input.files.length) {
        nameEl.textContent = input.files[0].name;
      } else {
        nameEl.textContent = "";
      }
      updatePreview();
    });
  }

  bindFileDisplay(claimFormInput, claimFormName);
  bindFileDisplay(repairInput, repairEstimateName);

  descriptionInput.addEventListener("input", updatePreview);

  // ── Drag-and-drop visual cue ───────────────────────────────────
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

  // ── Live preview update ────────────────────────────────────────
  function updatePreview() {
    // Claim form
    if (claimFormInput.files.length) {
      statusClaimForm.textContent = "Received";
      statusClaimForm.className = "badge badge-received";
    } else {
      statusClaimForm.textContent = "Not submitted";
      statusClaimForm.className = "badge badge-empty";
    }

    // Repair estimate
    if (repairInput.files.length) {
      statusRepairEstimate.textContent = "Received";
      statusRepairEstimate.className = "badge badge-received";
    } else {
      statusRepairEstimate.textContent = "Not submitted";
      statusRepairEstimate.className = "badge badge-empty";
    }

    // Incident description
    if (descriptionInput.value.trim()) {
      statusDescription.textContent = "Provided";
      statusDescription.className = "badge badge-received";
    } else {
      statusDescription.textContent = "Not submitted";
      statusDescription.className = "badge badge-empty";
    }
  }

  // ── Form submission ────────────────────────────────────────────
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
        (data.documents_received.length
          ? "<br>Documents: " +
            data.documents_received.map(function (d) { return d.filename; }).join(", ")
          : "");
      feedback.classList.remove("hidden");
    } catch (err) {
      feedback.className = "feedback info";
      feedback.textContent =
        "Review engine will be connected in the next milestone.";
      feedback.classList.remove("hidden");
    }

    reviewBtn.disabled = false;
    reviewBtn.textContent = "Review Claim";
  });
})();
