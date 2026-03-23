const ATTEMPT_KEY = "lti_shell_current_attempt_id";

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "-";
}

function setMessage(message, isError = false) {
  const el = document.getElementById("message");
  if (!el) return;
  el.style.color = isError ? "red" : "#2c3e50";
  el.textContent = message || "";
}

function setError(message) {
  const el = document.getElementById("error");
  if (!el) return;
  if (!message) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.style.display = "block";
  el.textContent = message;
}

function setButtons(hasAttempt) {
  document.getElementById("start-btn").disabled = hasAttempt;
  document.getElementById("reset-btn").disabled = !hasAttempt;
  document.getElementById("terminate-btn").disabled = !hasAttempt;
  document.getElementById("refresh-btn").disabled = !hasAttempt;
}

function renderAttempt(data) {
  setText("attempt-id", data?.attempt_id || "-");
  setText("attempt-status", data?.status || "-");
  setText("docker-status", data?.docker_status || data?.status || "-");
  setText("container-id", data?.container_id || "-");
  setText("created-at", data?.created_at || "-");
  setText("expires-at", data?.expires_at || "-");
}

function saveAttemptId(attemptId) {
  if (attemptId) {
    sessionStorage.setItem(ATTEMPT_KEY, attemptId);
  } else {
    sessionStorage.removeItem(ATTEMPT_KEY);
  }
}

function getAttemptId() {
  return sessionStorage.getItem(ATTEMPT_KEY);
}

async function refreshAttempt() {
  const attemptId = getAttemptId();
  if (!attemptId) return;

  const data = await API.getAttempt(attemptId);
  renderAttempt(data);

  if (data.status === "terminated") {
    saveAttemptId(null);
    setButtons(false);
  } else {
    setButtons(true);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await API.getUserInfo();
  if (!user) {
    setError("Not authenticated. Launch from Moodle.");
    setButtons(false);
    return;
  }

  document.getElementById("user-summary").innerHTML =
    "<table>" +
    "<tr><th>Name</th><td>" +
    escapeHtml(user.name) +
    "</td></tr>" +
    "<tr><th>Role</th><td>" +
    escapeHtml(user.role) +
    "</td></tr>" +
    "<tr><th>Course</th><td>" +
    escapeHtml(user.course_title) +
    " (" +
    escapeHtml(user.course_label) +
    ")</td></tr>" +
    "<tr><th>Activity</th><td>" +
    escapeHtml(user.resource_link_title) +
    "</td></tr>" +
    "</table>";

  const startBtn = document.getElementById("start-btn");
  const resetBtn = document.getElementById("reset-btn");
  const terminateBtn = document.getElementById("terminate-btn");
  const refreshBtn = document.getElementById("refresh-btn");

  startBtn.addEventListener("click", async () => {
    try {
      setMessage("Creating attempt...");
      const data = await API.createAttempt();
      saveAttemptId(data.attempt_id);
      renderAttempt(data);
      setButtons(true);
      setMessage("Attempt created.");
    } catch (err) {
      setMessage(err.message || "Failed to create attempt.", true);
    }
  });

  resetBtn.addEventListener("click", async () => {
    const attemptId = getAttemptId();
    if (!attemptId) return;

    try {
      setMessage("Resetting attempt...");
      const data = await API.resetAttempt(attemptId);
      renderAttempt(data);
      setButtons(true);
      setMessage("Attempt reset.");
    } catch (err) {
      setMessage(err.message || "Failed to reset attempt.", true);
    }
  });

  terminateBtn.addEventListener("click", async () => {
    const attemptId = getAttemptId();
    if (!attemptId) return;

    try {
      setMessage("Terminating attempt...");
      const data = await API.terminateAttempt(attemptId);
      renderAttempt(data);
      saveAttemptId(null);
      setButtons(false);
      setMessage("Attempt terminated.");
    } catch (err) {
      setMessage(err.message || "Failed to terminate attempt.", true);
    }
  });

  refreshBtn.addEventListener("click", async () => {
    try {
      setMessage("Refreshing status...");
      await refreshAttempt();
      setMessage("Status refreshed.");
    } catch (err) {
      setMessage(err.message || "Failed to refresh status.", true);
    }
  });

  const savedAttempt = getAttemptId();
  if (savedAttempt) {
    try {
      await refreshAttempt();
      setButtons(true);
    } catch (_) {
      saveAttemptId(null);
      renderAttempt(null);
      setButtons(false);
    }
  } else {
    renderAttempt(null);
    setButtons(false);
  }
});
