const ATTEMPT_KEY = "lti_shell_current_attempt_id";

// Shared client-side state for the terminal session and active websocket.
let term = null;
let fitAddon = null;
let ws = null;
let exitTerminationSent = false;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "-";
}

function formatDateDisplay(isoValue) {
  if (!isoValue) return "-";
  const dt = new Date(isoValue);
  if (Number.isNaN(dt.getTime())) return "-";
  return dt.toLocaleString();
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

function setWsStatus(text, color = "#666") {
  const el = document.getElementById("ws-status");
  if (!el) return;
  el.textContent = text;
  el.style.color = color;
}

function setButtons(hasAttempt) {
  document.getElementById("start-btn").disabled = hasAttempt;
  document.getElementById("reset-btn").disabled = !hasAttempt;
  document.getElementById("terminate-btn").disabled = !hasAttempt;
  document.getElementById("refresh-btn").disabled = !hasAttempt;
  const submitBtn = document.getElementById("submit-btn");
  if (submitBtn) {
    submitBtn.disabled = !hasAttempt;
  }
}

function renderAttempt(data) {
  setText("attempt-id", data?.attempt_id || "-");
  setText("attempt-status", data?.status || "-");
  setText("docker-status", data?.docker_status || data?.status || "-");
  setText("container-id", data?.container_id || "-");
  setText("created-at", data?.created_at || "-");
  setText("expires-at", data?.expires_at || "-");
}

function renderAssignment(data) {
  setText("assignment-title", data?.title || "-");
  setText("assignment-instructions", data?.instructions || "-");
  setText("assignment-due-at", formatDateDisplay(data?.due_at));
  setText("assignment-max-points", data?.max_points ?? "-");
  setText("assignment-configured", data?.is_configured ? "Yes" : "No");
}

function renderSubmission(data) {
  setText("submission-id", data?.submission_id || "-");
  setText("submission-status", data?.status || "-");

  if (data && data.score !== undefined && data.max_points !== undefined) {
    setText("submission-score", `${data.score}/${data.max_points}`);
  } else {
    setText("submission-score", "-");
  }

  setText("submission-completed-at", formatDateDisplay(data?.completed_at));
  setText("submission-passback-status", data?.passback_status || "-");
  setText(
    "submission-passback-attempts",
    data?.passback_attempts !== undefined ? String(data.passback_attempts) : "-",
  );
  setText("submission-passback-error", data?.passback_last_error || "-");

  const stdoutEl = document.getElementById("submission-stdout");
  const stderrEl = document.getElementById("submission-stderr");
  if (stdoutEl) stdoutEl.textContent = data?.feedback_stdout || "-";
  if (stderrEl) stderrEl.textContent = data?.feedback_stderr || "-";
}

function saveAttemptId(attemptId) {
  // Keep active attempt across refreshes within the same browser tab/session.
  if (attemptId) {
    sessionStorage.setItem(ATTEMPT_KEY, attemptId);
  } else {
    sessionStorage.removeItem(ATTEMPT_KEY);
  }
}

function getAttemptId() {
  return sessionStorage.getItem(ATTEMPT_KEY);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForRunningAttempt(
  attemptId,
  timeoutMs = 8000,
  pollMs = 300,
) {
  const startedAt = Date.now();
  let latest = null;

  while (Date.now() - startedAt < timeoutMs) {
    latest = await API.getAttempt(attemptId);
    renderAttempt(latest);

    if (["terminated", "submitted", "expired"].includes(latest.status)) {
      throw new Error("Attempt is no longer active.");
    }
    if (latest.container_id && latest.docker_status === "running") {
      return latest;
    }

    await sleep(pollMs);
  }

  throw new Error(
    "Container is not ready yet. Try Refresh Status and reconnect.",
  );
}

function initTerminal() {
  // xterm.js instance rendered inside #terminal.
  term = new window.Terminal({
    cursorBlink: true,
    convertEol: true,
    fontSize: 13,
    theme: {
      background: "#111111",
      foreground: "#e7e7e7",
    },
  });

  fitAddon = new window.FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById("terminal"));
  fitAddon.fit();
  term.writeln("LTI-Shell terminal ready.");

  // Forward keyboard input to backend websocket terminal bridge.
  term.onData((data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "input", data }));
    }
  });

  window.addEventListener("resize", () => {
    if (!fitAddon || !term) return;
    fitAddon.fit();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "resize",
          cols: term.cols,
          rows: term.rows,
        }),
      );
    }
  });

  document.getElementById("clear-terminal").addEventListener("click", () => {
    term.clear();
  });
}

function closeSocket() {
  if (ws) {
    try {
      ws.close();
    } catch (_) {}
    ws = null;
  }
  setWsStatus("Disconnected", "#666");
}

function terminateAttemptOnPageExit() {
  // Best-effort cleanup: terminate running attempt if user leaves page without clicking Terminate.
  if (exitTerminationSent) return;

  const attemptId = getAttemptId();
  if (!attemptId) return;

  exitTerminationSent = true;
  closeSocket();
  saveAttemptId(null);

  const path = `/api/attempts/${encodeURIComponent(attemptId)}/terminate`;

  if (navigator.sendBeacon) {
    const body = new Blob(["page_exit"], { type: "text/plain;charset=UTF-8" });
    const queued = navigator.sendBeacon(path, body);
    if (queued) return;
  }

  // Fallback for browsers where sendBeacon is unavailable or queueing fails.
  fetch(path, {
    method: "POST",
    credentials: "same-origin",
    keepalive: true,
  }).catch(() => {});
}

function openSocket(attemptId) {
  return new Promise((resolve, reject) => {
    let opened = false;
    let settled = false;

    const rejectOnce = (error) => {
      if (settled) return;
      settled = true;
      reject(error);
    };

    const resolveOnce = () => {
      if (settled) return;
      settled = true;
      resolve();
    };

    // One active socket at a time to avoid duplicate streams.
    closeSocket();

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/terminal?attempt_id=${encodeURIComponent(attemptId)}`;

    const socket = new WebSocket(url);
    ws = socket;
    setWsStatus("Connecting...", "#c58a00");

    socket.onopen = () => {
      if (ws !== socket) {
        return;
      }
      opened = true;
      setWsStatus("Connected", "#167c2f");
      if (fitAddon && term) {
        fitAddon.fit();
        socket.send(
          JSON.stringify({
            type: "resize",
            cols: term.cols,
            rows: term.rows,
          }),
        );
      }
      term.focus();
      resolveOnce();
    };

    // Backend sends JSON envelopes: {type:"output"|"error", ...}
    socket.onmessage = (event) => {
      if (ws !== socket) return;

      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "output") {
          term.write(msg.data || "");
          return;
        }
        if (msg.type === "error") {
          const message = msg.message || "Terminal error";
          setMessage(message, true);
          term.writeln(`\r\n[error] ${message}\r\n`);
          if (!opened) rejectOnce(new Error(message));
          return;
        }
      } catch (_) {
        term.write(event.data || "");
      }
    };

    socket.onclose = () => {
      setWsStatus("Disconnected", "#666");
      if (ws === socket) {
        ws = null;
        setWsStatus("Disconnected", "#666");
      }
      if (!opened) {
        rejectOnce(new Error("Terminal connection closed before open."));
      }
    };

    socket.onerror = () => {
      if (ws === socket) {
        setWsStatus("Error", "red");
      }
      if (!opened) {
        rejectOnce(new Error("Terminal websocket error."));
      }
    };
  });
}

async function connectSocketWithRetry(attemptId, retries = 4, delayMs = 350) {
  let lastError = null;
  for (let i = 0; i < retries; i += 1) {
    try {
      await openSocket(attemptId);
      return;
    } catch (error) {
      lastError = error;
      await sleep(delayMs * (i + 1));
    }
  }
  throw lastError || new Error("Could not connect terminal websocket.");
}

async function refreshAttempt() {
  const attemptId = getAttemptId();
  if (!attemptId) return null;

  // Pull latest server truth and sync controls/socket state.
  const data = await API.getAttempt(attemptId);
  renderAttempt(data);

  const active = !["terminated", "submitted", "expired"].includes(data.status);
  if (!active) {
    saveAttemptId(null);
    setButtons(false);
    closeSocket();
  } else {
    setButtons(true);
  }

  return data;
}

document.addEventListener("DOMContentLoaded", async () => {
  initTerminal();
  // Fire termination on tab close/navigation away.
  window.addEventListener("beforeunload", terminateAttemptOnPageExit);
  window.addEventListener("pagehide", terminateAttemptOnPageExit);

  const user = await API.getUserInfo();
  if (!user) {
    setError("Not authenticated. Launch from Moodle.");
    setButtons(false);
    return;
  }

  let assignment = null;
  try {
    assignment = await API.getCurrentAssignment();
    renderAssignment(assignment);
  } catch (err) {
    renderAssignment(null);
    setError(err.message || "Assignment is not configured for this activity.");
    setButtons(false);
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
  const submitBtn = document.getElementById("submit-btn");

  renderSubmission(null);

  startBtn.addEventListener("click", async () => {
    if (!assignment || !assignment.is_configured) {
      setMessage("Assignment is not configured for this activity.", true);
      return;
    }

    try {
      setMessage("Creating attempt...");
      const data = await API.createAttempt();
      saveAttemptId(data.attempt_id);
      renderAttempt(data);
      setButtons(true);
      renderSubmission(null);
      const readyAttempt = await waitForRunningAttempt(data.attempt_id);
      await connectSocketWithRetry(readyAttempt.attempt_id);
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
      renderSubmission(null);
      const readyAttempt = await waitForRunningAttempt(attemptId);
      await connectSocketWithRetry(readyAttempt.attempt_id);
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
      closeSocket();
      exitTerminationSent = true;
      setMessage("Attempt terminated.");
      renderSubmission(null);
    } catch (err) {
      setMessage(err.message || "Failed to terminate attempt.", true);
    }
  });

  if (submitBtn) {
    submitBtn.addEventListener("click", async () => {
      const attemptId = getAttemptId();
      if (!attemptId) return;

      if (user.role === "teacher") {
        setMessage("Only students can submit assignments.", true);
        return;
      }

      try {
        setMessage("Submitting for grading...");
        const submission = await API.submitAttempt(attemptId);
        renderSubmission(submission);
        saveAttemptId(null);
        renderAttempt({ status: "submitted" });
        setButtons(false);
        closeSocket();
        exitTerminationSent = true;
        setMessage("Submission graded. See results below.");
      } catch (err) {
        if (err?.payload?.submission_id) {
          renderSubmission(err.payload);
        }
        setMessage(err.message || "Failed to submit assignment.", true);
      }
    });
  }

  refreshBtn.addEventListener("click", async () => {
    try {
      setMessage("Refreshing status...");
      const data = await refreshAttempt();
      if (
        data &&
        data.status !== "terminated" &&
        (!ws || ws.readyState !== WebSocket.OPEN)
      ) {
        const readyAttempt = await waitForRunningAttempt(data.attempt_id);
        await connectSocketWithRetry(readyAttempt.attempt_id);
      }
      setMessage("Status refreshed.");
    } catch (err) {
      setMessage(err.message || "Failed to refresh status.", true);
    }
  });

  const savedAttempt = getAttemptId();
  if (!assignment || !assignment.is_configured) {
    saveAttemptId(null);
    renderAttempt(null);
    closeSocket();
    return;
  }

  if (savedAttempt) {
    // Reconnect after refresh if attempt still active.
    try {
      const data = await refreshAttempt();
      if (data && data.status !== "terminated") {
        const readyAttempt = await waitForRunningAttempt(savedAttempt);
        await connectSocketWithRetry(readyAttempt.attempt_id);
      }
    } catch (_) {
      saveAttemptId(null);
      renderAttempt(null);
      setButtons(false);
      closeSocket();
    }
  } else {
    renderAttempt(null);
    setButtons(false);
  }

  if (user.role === "teacher" && submitBtn) {
    submitBtn.disabled = true;
  }
});
