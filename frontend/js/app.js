function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function setAssignmentMessage(message, isError = false) {
  const el = document.getElementById("assignment-message");
  if (!el) return;
  el.classList.toggle("is-error", Boolean(isError));
  el.setAttribute("role", isError ? "alert" : "status");
  el.textContent = message || "";
}

function toIsoFromLocalDatetime(value) {
  if (!value) return null;
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return null;
  return dt.toISOString();
}

function toLocalDatetimeInputValue(isoValue) {
  if (!isoValue) return "";
  const dt = new Date(isoValue);
  if (Number.isNaN(dt.getTime())) return "";
  const offsetMs = dt.getTimezoneOffset() * 60000;
  return new Date(dt.getTime() - offsetMs).toISOString().slice(0, 16);
}

function formatDateDisplay(isoValue) {
  if (!isoValue) return "-";
  const dt = new Date(isoValue);
  if (Number.isNaN(dt.getTime())) return "-";
  return dt.toLocaleString();
}

function renderUserContext(user) {
  const course = [
    user?.course_title,
    user?.course_label ? `(${user.course_label})` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const navUserName = document.getElementById("nav-user-name");
  if (navUserName) navUserName.textContent = user?.name || "-";
  const activityCourse = document.getElementById("activity-course");
  if (activityCourse) activityCourse.textContent = course || "-";
  const activityName = document.getElementById("activity-name");
  if (activityName) activityName.textContent = user?.resource_link_title || "-";
}

function wireTeacherAssignmentManager(user) {
  const form = document.getElementById("assignment-form");
  const formSection = document.getElementById("assignment-form-section");
  const selectSection = document.getElementById("assignment-select-section");
  const createAssignmentToggle = document.getElementById(
    "create-assignment-toggle",
  );
  const selectAssignmentToggle = document.getElementById(
    "select-assignment-toggle",
  );
  const currentAssignmentSummary = document.getElementById(
    "current-assignment-summary",
  );
  const assignmentDetailsToggle = document.getElementById(
    "assignment-details-toggle",
  );
  const submitBtn = document.getElementById("assignment-submit");
  const detachBtn = document.getElementById("assignment-detach");
  const empty = document.getElementById("assignments-empty");
  const table = document.getElementById("assignments-table");
  const tbody = document.getElementById("assignments-tbody");

  if (!form || !submitBtn || !empty || !table || !tbody) return;

  let selectedAssignmentId = null;
  let currentAssignment = null;
  let assignmentsCache = [];
  let currentArtifactStatus = null;
  let assignmentDetailsVisibilityInitialized = false;

  const titleInput = document.getElementById("assignment-title");
  const instructionsInput = document.getElementById("assignment-instructions");
  const dueAtInput = document.getElementById("assignment-due-at");
  const maxPointsInput = document.getElementById("assignment-max-points");
  const starterZipInput = document.getElementById("starter-zip");
  const testsZipInput = document.getElementById("tests-zip");
  const starterRemoveBtn = document.getElementById("starter-remove-btn");
  const testsRemoveBtn = document.getElementById("tests-remove-btn");
  const artifactStatusEl = document.getElementById("artifact-status");
  const starterFileStatus = document.getElementById("starter-file-status");
  const testsFileStatus = document.getElementById("tests-file-status");
  const currentResourceLinkId = (user.resource_link_id || "").trim();
  const artifactFileNames = new Map();
  const showPanel = (panel, shouldShow, toggleButton) => {
    if (!panel) return;
    panel.classList.toggle("dashboard-panel-hidden", !shouldShow);
    panel.setAttribute("aria-hidden", shouldShow ? "false" : "true");
    if (toggleButton) {
      toggleButton.setAttribute("aria-expanded", shouldShow ? "true" : "false");
    }
  };

  const isAssignmentDetailsVisible = () =>
    formSection && !formSection.classList.contains("dashboard-panel-hidden");

  const setAssignmentDetailsVisible = (shouldShow) => {
    showPanel(formSection, shouldShow, assignmentDetailsToggle);
    if (createAssignmentToggle) {
      createAssignmentToggle.setAttribute(
        "aria-expanded",
        shouldShow ? "true" : "false",
      );
    }
    renderActivityActions();
  };

  const makeInstructionsPreview = (value) => {
    const text = String(value || "").trim();
    if (!text) return "-";
    return text.length > 140 ? text.slice(0, 137) + "..." : text;
  };

  const renderInstructionsCaption = (item, index) => {
    const instructions = String(item.instructions || "").trim();
    const captionId = "assignment-instructions-caption-" + index;
    const captionText = instructions || "No instructions provided.";

    return (
      '<span class="instructions-caption-wrap">' +
      '<button type="button" class="instructions-preview" aria-label="Instructions: ' +
      escapeHtml(captionText) +
      '" aria-describedby="' +
      captionId +
      '">' +
      escapeHtml(makeInstructionsPreview(instructions)) +
      "</button>" +
      '<span id="' +
      captionId +
      '" class="instructions-caption" role="tooltip">' +
      escapeHtml(captionText) +
      "</span>" +
      "</span>"
    );
  };

  const getCurrentAssignmentFromItems = (items) => {
    const attachedItems = items.filter(
      (item) => item.resource_link_id === currentResourceLinkId,
    );
    return (
      attachedItems.find((item) => item.is_configured) ||
      attachedItems[0] ||
      null
    );
  };

  const clearRowSelection = () => {
    tbody.querySelectorAll("tr").forEach((row) => {
      row.classList.remove("assignment-row-selected");
      row.removeAttribute("aria-current");
      const button = row.querySelector(".table-row-select");
      if (button) {
        button.setAttribute("aria-pressed", "false");
      }
    });
  };

  const renderActivityActions = () => {
    const detailsVisible = Boolean(isAssignmentDetailsVisible());
    const canToggleDetails = Boolean(currentAssignment);
    if (assignmentDetailsToggle) {
      assignmentDetailsToggle.disabled = !canToggleDetails;
      assignmentDetailsToggle.textContent = canToggleDetails && detailsVisible
        ? "Hide Assignment Details"
        : "Configure Assignment Details";
      assignmentDetailsToggle.setAttribute(
        "aria-expanded",
        canToggleDetails && detailsVisible ? "true" : "false",
      );
    }
    if (createAssignmentToggle) {
      createAssignmentToggle.disabled = Boolean(currentAssignment);
      createAssignmentToggle.title = currentAssignment
        ? "Remove the attached assignment before creating a new one."
        : "";
    }
    if (detachBtn) {
      detachBtn.disabled = !currentAssignment;
    }
  };

  const renderCurrentAssignment = () => {
    if (!currentAssignmentSummary) return;
    if (!currentAssignment) {
      currentAssignmentSummary.innerHTML =
        '<div class="assignment-status-card assignment-status-empty">' +
        '<div><strong>No assignment attached</strong>' +
        "<span>Create a new assignment or choose an existing one for this Moodle activity.</span></div>" +
        "</div>";
      renderActivityActions();
      return;
    }

    currentAssignmentSummary.innerHTML =
      '<div class="assignment-status-card">' +
      '<div><strong>' +
      escapeHtml(currentAssignment.title || "Untitled assignment") +
      "</strong><span>Attached to this Moodle activity</span></div>" +
      '<div class="assignment-status-meta">' +
      '<span>Due: ' +
      escapeHtml(formatDateDisplay(currentAssignment.due_at)) +
      "</span>" +
      '<span>Points: ' +
      escapeHtml(String(currentAssignment.max_points || "-")) +
      "</span>" +
      '<span>Artifacts: ' +
      escapeHtml(
        currentAssignment.is_configured ? "Configured" : "Not configured",
      ) +
      "</span></div>" +
      "</div>";
    renderActivityActions();
  };

  const resetSelection = () => {
    selectedAssignmentId = null;
    currentArtifactStatus = null;
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Assignment";
    if (detachBtn) detachBtn.disabled = !currentAssignment;
    clearRowSelection();
    renderArtifactFileCards(null);
    if (artifactStatusEl)
      artifactStatusEl.textContent = "No assignment is attached.";
  };

  const applySelectedAssignment = (assignment, rows, selectedRow) => {
    selectedAssignmentId = assignment.assignment_id;
    submitBtn.disabled = false;
    submitBtn.textContent = "Save Changes";
    if (detachBtn) {
      detachBtn.disabled = !(
        currentAssignment &&
        assignment.assignment_id === currentAssignment.assignment_id
      );
    }
    fillForm(assignment);
    renderArtifactFileCards(assignment);
    if (rows && selectedRow) {
      rows.forEach((r) => {
        r.classList.remove("assignment-row-selected");
        r.removeAttribute("aria-current");
        const button = r.querySelector(".table-row-select");
        if (button) {
          button.setAttribute("aria-pressed", "false");
        }
      });
      selectedRow.classList.add("assignment-row-selected");
      selectedRow.setAttribute("aria-current", "true");
      const selectedButton = selectedRow.querySelector(".table-row-select");
      if (selectedButton) {
        selectedButton.setAttribute("aria-pressed", "true");
      }
    }
  };

  const fillForm = (assignment) => {
    titleInput.value = assignment.title || "";
    instructionsInput.value = assignment.instructions || "";
    dueAtInput.value = toLocalDatetimeInputValue(assignment.due_at);
    maxPointsInput.value = assignment.max_points || 100;
  };

  const buildPayloadFromForm = () => ({
    title: titleInput.value,
    instructions: instructionsInput.value,
    due_at: toIsoFromLocalDatetime(dueAtInput.value),
    max_points: Number(maxPointsInput.value),
  });

  const getArtifactFileName = (assignmentId, kind) =>
    artifactFileNames.get(assignmentId + ":" + kind) || "";

  const setArtifactFileName = (assignmentId, kind, fileName) => {
    if (!assignmentId || !fileName) return;
    artifactFileNames.set(assignmentId + ":" + kind, fileName);
  };

  const clearArtifactFileName = (assignmentId, kind) => {
    if (!assignmentId) return;
    artifactFileNames.delete(assignmentId + ":" + kind);
  };

  const getSelectedFileName = (input) =>
    input && input.files && input.files[0] ? input.files[0].name : "";

  const updateArtifactRemoveControls = (status = currentArtifactStatus) => {
    const hasAssignment = Boolean(selectedAssignmentId);
    const hasStarter =
      Boolean(status?.starter_zip_uploaded) ||
      Boolean(getArtifactFileName(selectedAssignmentId, "starter"));
    const hasTests =
      Boolean(status?.tests_zip_uploaded) ||
      Boolean(getArtifactFileName(selectedAssignmentId, "tests"));
    if (starterRemoveBtn) starterRemoveBtn.disabled = !(hasAssignment && hasStarter);
    if (testsRemoveBtn) testsRemoveBtn.disabled = !(hasAssignment && hasTests);
  };

  const renderArtifactFileCards = (status = null) => {
    const starterSelected = getSelectedFileName(starterZipInput);
    const testsSelected = getSelectedFileName(testsZipInput);
    const starterAttached = selectedAssignmentId
      ? getArtifactFileName(selectedAssignmentId, "starter")
      : "";
    const testsAttached = selectedAssignmentId
      ? getArtifactFileName(selectedAssignmentId, "tests")
      : "";

    if (starterFileStatus) {
      starterFileStatus.textContent = starterSelected
        ? "Selected: " + starterSelected + " (save changes to upload)"
        : !selectedAssignmentId
          ? "No starter ZIP selected."
          : starterAttached
            ? "Attached: " + starterAttached
            : status?.starter_zip_uploaded
              ? "Starter ZIP attached."
              : "No starter ZIP attached.";
    }

    if (testsFileStatus) {
      testsFileStatus.textContent = testsSelected
        ? "Selected: " + testsSelected + " (save changes to upload)"
        : !selectedAssignmentId
          ? "No tests ZIP selected."
          : testsAttached
            ? "Attached: " + testsAttached
            : status?.tests_zip_uploaded
              ? "Tests ZIP attached."
              : "No tests ZIP attached.";
    }

    updateArtifactRemoveControls(status);
  };

  const renderArtifactStatus = (status) => {
    currentArtifactStatus = status || null;
    if (!artifactStatusEl) return;
    if (!status) {
      artifactStatusEl.textContent = "";
      renderArtifactFileCards(null);
      return;
    }
    renderArtifactFileCards(status);

    const needs = [];
    if (!status.starter_zip_uploaded) needs.push("Starter ZIP");
    if (!status.tests_zip_uploaded) needs.push("Tests ZIP");
    if (status.tests_zip_uploaded && !status.has_required_test_runner)
      needs.push("run_tests.sh");
    if (
      status.starter_zip_uploaded &&
      status.tests_zip_uploaded &&
      status.has_required_test_runner &&
      !status.artifacts_validated
    ) {
      needs.push("Validation");
    }

    const chips = needs
      .map(
        (item) => '<span class="artifact-chip">' + escapeHtml(item) + "</span>",
      )
      .join("");
    const validationError = status.artifact_validation_error
      ? '<div class="artifact-status-error">' +
        escapeHtml(status.artifact_validation_error) +
        "</div>"
      : "";

    artifactStatusEl.innerHTML =
      '<div class="artifact-status-row">' +
      "<strong>" +
      (status.is_configured ? "Ready" : "Needs setup") +
      "</strong>" +
      (needs.length
        ? '<div class="artifact-chip-row">' + chips + "</div>"
        : '<span class="artifact-ready-text">Starter and tests are uploaded.</span>') +
      "</div>" +
      validationError;
  };

  const refreshArtifactStatus = async () => {
    if (!selectedAssignmentId) {
      renderArtifactStatus(null);
      return;
    }
    try {
      const status =
        await API.getAssignmentArtifactsStatus(selectedAssignmentId);
      renderArtifactStatus(status);
    } catch (error) {
      setAssignmentMessage(
        error.message || "Failed to load artifact status.",
        true,
      );
    }
  };

  const uploadSelectedArtifacts = async (assignmentId) => {
    const uploaded = [];

    if (starterZipInput?.files?.[0]) {
      const file = starterZipInput.files[0];
      await API.uploadStarterZip(assignmentId, file);
      setArtifactFileName(assignmentId, "starter", file.name);
      starterZipInput.value = "";
      uploaded.push("starter files");
    }

    if (testsZipInput?.files?.[0]) {
      const file = testsZipInput.files[0];
      await API.uploadTestsZip(assignmentId, file);
      setArtifactFileName(assignmentId, "tests", file.name);
      testsZipInput.value = "";
      uploaded.push("grading scripts");
    }

    return uploaded;
  };

  const attachAssignment = async (assignment) => {
    if (!assignment) return;
    const selectedTitle = assignment.title || "this assignment";
    const shouldAttach = window.confirm(
      'Attach "' +
        selectedTitle +
        '" to this LTI activity?\n\n' +
        "Any assignment currently attached to this activity will be removed.",
    );
    if (!shouldAttach) return;
    try {
      await API.attachAssignmentToCurrentActivity(assignment.assignment_id);
      selectedAssignmentId = assignment.assignment_id;
      setAssignmentMessage("Assignment attached to this LTI activity.");
      await loadAssignments();
      await refreshArtifactStatus();
      showPanel(selectSection, false, selectAssignmentToggle);
      setAssignmentDetailsVisible(true);
    } catch (error) {
      setAssignmentMessage(
        error.message || "Failed to attach assignment to this activity.",
        true,
      );
    }
  };

  const loadAssignments = async () => {
    try {
      const data = await API.listAssignments();
      const items = data.items || [];
      assignmentsCache = items;
      currentAssignment = getCurrentAssignmentFromItems(items);
      if (!assignmentDetailsVisibilityInitialized) {
        showPanel(
          formSection,
          !currentAssignment,
          assignmentDetailsToggle || createAssignmentToggle,
        );
        assignmentDetailsVisibilityInitialized = true;
      }
      renderCurrentAssignment();

      if (!items.length) {
        empty.style.display = "block";
        table.style.display = "none";
        tbody.innerHTML = "";
        resetSelection();
        setAssignmentDetailsVisible(true);
        return;
      }

      empty.style.display = "none";
      table.style.display = "table";
      tbody.innerHTML = items
        .map(
          (item, index) =>
            '<tr data-assignment-id="' +
            escapeHtml(item.assignment_id) +
            '">' +
            '<td><button type="button" class="table-row-select" aria-pressed="false"><span class="visually-hidden">Select </span>' +
            escapeHtml(item.title || "Untitled assignment") +
            "</button></td>" +
            "<td>" +
            renderInstructionsCaption(item, index) +
            "</td>" +
            "<td>" +
            escapeHtml(formatDateDisplay(item.due_at)) +
            "</td>" +
            "<td>" +
            escapeHtml(String(item.max_points)) +
            "</td>" +
            "<td>" +
            escapeHtml(item.is_configured ? "Yes" : "No") +
            "</td>" +
            "<td>" +
            (currentAssignment &&
            item.assignment_id === currentAssignment.assignment_id
              ? "Yes"
              : "No") +
            "</td>" +
            '<td><button type="button" class="table-row-attach" data-assignment-id="' +
            escapeHtml(item.assignment_id) +
            '"' +
            (currentAssignment &&
            item.assignment_id === currentAssignment.assignment_id
              ? " disabled"
              : "") +
            ">" +
            (currentAssignment &&
            item.assignment_id === currentAssignment.assignment_id
              ? "Attached"
              : "Attach") +
            "</button>" +
            "</td>" +
            "</tr>",
        )
        .join("");

      const rows = Array.from(tbody.querySelectorAll("tr"));
      rows.forEach((row) => {
        const selectRow = () => {
          const assignmentId = row.getAttribute("data-assignment-id");
          const assignment = items.find(
            (item) => item.assignment_id === assignmentId,
          );
          if (!assignment) return;

          applySelectedAssignment(assignment, rows, row);
          setAssignmentMessage(
            'Selected "' +
              (assignment.title || "Untitled assignment") +
              '". Review the title and instructions, then attach it to this activity if needed.',
          );
          refreshArtifactStatus();
        };

        row.addEventListener("click", (event) => {
          if (
            event.target instanceof Element &&
            (event.target.closest(".instructions-preview") ||
              event.target.closest(".table-row-attach"))
          ) {
            return;
          }
          selectRow();
        });

        const attachButton = row.querySelector(".table-row-attach");
        if (attachButton) {
          attachButton.addEventListener("click", () => {
            const assignmentId = row.getAttribute("data-assignment-id");
            const assignment = items.find(
              (item) => item.assignment_id === assignmentId,
            );
            attachAssignment(assignment);
          });
        }
      });

      if (selectedAssignmentId) {
        const selectedAssignment = items.find(
          (item) => item.assignment_id === selectedAssignmentId,
        );
        const selectedRow = rows.find(
          (row) =>
            row.getAttribute("data-assignment-id") === selectedAssignmentId,
        );
        if (selectedAssignment && selectedRow) {
          applySelectedAssignment(selectedAssignment, rows, selectedRow);
          await refreshArtifactStatus();
        } else {
          resetSelection();
        }
      } else {
        if (currentAssignment) {
          const attachedRow = rows.find(
            (row) =>
              row.getAttribute("data-assignment-id") ===
              currentAssignment.assignment_id,
          );
          if (attachedRow) {
            applySelectedAssignment(currentAssignment, rows, attachedRow);
            await refreshArtifactStatus();
          }
        } else {
          resetSelection();
        }
      }
    } catch (error) {
      setAssignmentMessage(
        error.message || "Failed to load assignments.",
        true,
      );
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = buildPayloadFromForm();
      let assignmentId = selectedAssignmentId;
      let baseMessage = "Assignment saved.";
      if (selectedAssignmentId) {
        await API.updateAssignment(selectedAssignmentId, payload);
      } else {
        const created = await API.createAssignment(payload);
        assignmentId = created.assignment_id;
        selectedAssignmentId = assignmentId;
        baseMessage =
          "Assignment created for activity " +
          (user.resource_link_title || user.resource_link_id) +
          ".";
      }
      const uploaded = await uploadSelectedArtifacts(assignmentId);
      setAssignmentMessage(
        uploaded.length
          ? baseMessage + " Uploaded " + uploaded.join(" and ") + "."
          : baseMessage,
      );
      await loadAssignments();
      await refreshArtifactStatus();
      setAssignmentDetailsVisible(true);
    } catch (error) {
      setAssignmentMessage(
        error.message || "Failed to save assignment.",
        true,
      );
    }
  });

  if (detachBtn) {
    detachBtn.addEventListener("click", async () => {
      if (!currentAssignment) return;
      const shouldDetach = window.confirm(
        'Remove "' +
          (currentAssignment.title || "this assignment") +
          '" from this Moodle activity?\n\n' +
          "The assignment will remain in the course list, but students launching this activity will not see it until an assignment is attached again.",
      );
      if (!shouldDetach) return;
      try {
        await API.detachAssignmentFromCurrentActivity(
          currentAssignment.assignment_id,
        );
        setAssignmentMessage("Assignment removed from this Moodle activity.");
        currentAssignment = null;
        selectedAssignmentId = null;
        await loadAssignments();
        renderArtifactStatus(null);
        setAssignmentDetailsVisible(true);
      } catch (error) {
        setAssignmentMessage(
          error.message || "Failed to remove assignment from this activity.",
          true,
        );
      }
    });
  }

  if (createAssignmentToggle) {
    createAssignmentToggle.addEventListener("click", () => {
      if (currentAssignment) {
        setAssignmentMessage(
          "Remove the current assignment before creating a new one for this Moodle activity.",
          true,
        );
        return;
      }
      setAssignmentDetailsVisible(true);
      currentAssignment = null;
      resetSelection();
      renderCurrentAssignment();
      titleInput.value = "";
      instructionsInput.value = "";
      dueAtInput.value = "";
      maxPointsInput.value = 100;
    });
  }

  if (selectAssignmentToggle) {
    selectAssignmentToggle.addEventListener("click", () => {
      const shouldShow =
        selectSection &&
        selectSection.classList.contains("dashboard-panel-hidden");
      showPanel(selectSection, shouldShow, selectAssignmentToggle);
    });
  }

  if (assignmentDetailsToggle) {
    assignmentDetailsToggle.addEventListener("click", () => {
      if (!currentAssignment) return;
      setAssignmentDetailsVisible(!isAssignmentDetailsVisible());
    });
  }

  if (starterZipInput) {
    starterZipInput.addEventListener("change", () => {
      renderArtifactFileCards(currentArtifactStatus);
    });
  }

  if (testsZipInput) {
    testsZipInput.addEventListener("change", () => {
      renderArtifactFileCards(currentArtifactStatus);
    });
  }

  const removeArtifact = async (artifactKind) => {
    if (!selectedAssignmentId) return;
    const label = artifactKind === "starter" ? "starter files" : "grading scripts";
    const shouldRemove = window.confirm(
      "Remove the attached " + label + " from this assignment?",
    );
    if (!shouldRemove) return;
    try {
      await API.deleteAssignmentArtifact(selectedAssignmentId, artifactKind);
      clearArtifactFileName(selectedAssignmentId, artifactKind);
      if (artifactKind === "starter" && starterZipInput) {
        starterZipInput.value = "";
      }
      if (artifactKind === "tests" && testsZipInput) {
        testsZipInput.value = "";
      }
      setAssignmentMessage("Removed attached " + label + ".");
      await loadAssignments();
      await refreshArtifactStatus();
    } catch (error) {
      setAssignmentMessage(
        error.message || "Failed to remove attached " + label + ".",
        true,
      );
      await refreshArtifactStatus();
    }
  };

  if (starterRemoveBtn) {
    starterRemoveBtn.addEventListener("click", () => {
      removeArtifact("starter");
    });
  }

  if (testsRemoveBtn) {
    testsRemoveBtn.addEventListener("click", () => {
      removeArtifact("tests");
    });
  }

  loadAssignments();
}

document.addEventListener("DOMContentLoaded", async () => {
  const userInfoDiv = document.getElementById("user-info");
  const userInfo = document.getElementById("error");

  const user = await API.getUserInfo();
  if (!user) {
    userInfoDiv.innerHTML = "";
    userInfo.style.display = "block";
    userInfo.textContent = "Not authenticated. Please log in through your LMS.";
    return;
  }
  renderUserContext(user);

  userInfoDiv.innerHTML =
    "<table>" +
    "<caption>Launch context details</caption>" +
    '<tr><th scope="row">Name</th><td>' +
    escapeHtml(user.name) +
    "</td></tr>" +
    '<tr><th scope="row">Email</th><td>' +
    escapeHtml(user.email) +
    "</td></tr>" +
    '<tr><th scope="row">Role</th><td>' +
    escapeHtml(user.role) +
    "</td></tr>" +
    '<tr><th scope="row">Course</th><td>' +
    escapeHtml(user.course_title) +
    " (" +
    escapeHtml(user.course_label) +
    ")</td></tr>" +
    '<tr><th scope="row">Activity</th><td>' +
    escapeHtml(user.resource_link_title) +
    "</td></tr>" +
    "</table>";

  if (user.role === "teacher") {
    wireTeacherAssignmentManager(user);
  }
});
