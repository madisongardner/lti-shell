const API = {
  async request(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      payload = null;
    }
    if (!response.ok) {
      const error = new Error(payload?.message || "HTTP " + response.status);
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
};
