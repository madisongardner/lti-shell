const API = {
  async request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      payload = null;
    }
    if (!response.ok) {
      const detailText = Array.isArray(payload?.details) ? `: ${payload.details.join("; ")}` : "";
      const error = new Error((payload?.error || payload?.message || "HTTP " + response.status) + detailText);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  },

  async getUserInfo() {
    try {
      return await this.request("/api/user-info", { method: "GET" });
    } catch (error) {
      if (error.status === 401) return null;
      console.error("Failed to fetch user info:", error);
      return null;
    }
  },
  async createAttempt() {
    return this.request("/api/attempts", { method: "POST" });
  },
  async resetAttempt(attemptId) {
    return this.request(
      `/api/attempts/${encodeURIComponent(attemptId)}/reset`,
      {
        method: "POST",
      },
    );
  },
  async terminateAttempt(attemptId) {
    return this.request(
      `/api/attempts/${encodeURIComponent(attemptId)}/terminate`,
      {
        method: "POST",
      },
    );
  },

  async getAttempt(attemptId) {
    return this.request(`/api/attempts/${encodeURIComponent(attemptId)}`, {
      method: "GET",
    });
  },

  async createAssignment(payload) {
    return this.request("/api/assignments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listAssignments() {
    return this.request("/api/assignments", { method: "GET" });
  },

  async getCurrentAssignment() {
    return this.request("/api/assignments/current", { method: "GET" });
  },

  async updateAssignment(assignmentId, payload) {
    return this.request(`/api/assignments/${encodeURIComponent(assignmentId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async uploadStarterZip(assignmentId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request(`/api/assignments/${encodeURIComponent(assignmentId)}/starter-upload`, {
      method: "POST",
      body: formData,
    });
  },

  async uploadTestsZip(assignmentId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request(`/api/assignments/${encodeURIComponent(assignmentId)}/tests-upload`, {
      method: "POST",
      body: formData,
    });
  },

  async getAssignmentArtifactsStatus(assignmentId) {
    return this.request(`/api/assignments/${encodeURIComponent(assignmentId)}/artifacts-status`, {
      method: "GET",
    });
  },
};
