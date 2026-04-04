const samplePath = String.raw`C:\Users\A\OneDrive\Documents\Codex hackathon\samples\demo_repo`;

const state = {
  runId: null,
  latestReport: null,
};

const els = {
  form: document.getElementById("orchestrate-form"),
  repositoryPath: document.getElementById("repository_path"),
  maxRetries: document.getElementById("max_retries"),
  runButton: document.getElementById("run-button"),
  sampleButton: document.getElementById("sample-button"),
  reportButton: document.getElementById("report-button"),
  status: document.getElementById("run-status"),
  metrics: document.getElementById("metrics"),
  timeline: document.getElementById("timeline"),
  summary: document.getElementById("summary"),
  logs: document.getElementById("logs"),
  json: document.getElementById("json-output"),
};

function setStatus(text, variant = "") {
  els.status.textContent = text;
  els.status.className = `status-pill ${variant}`.trim();
}

function setMetrics(report) {
  const execution = report.execution_history.at(-1);
  const cards = [
    { label: "Run ID", value: report.run_id, sublabel: report.status.toUpperCase() },
    { label: "Iterations", value: String(report.iterations), sublabel: "retry loop" },
    { label: "Tests", value: execution?.tests_collected != null ? String(execution.tests_collected) : "n/a", sublabel: "collected" },
  ];
  els.metrics.innerHTML = cards
    .map(
      (card) => `
        <div class="metric">
          <div class="metric-label">${card.label}</div>
          <strong>${card.value}</strong>
          <div class="metric-meta">${card.sublabel}</div>
        </div>
      `,
    )
    .join("");
}

function setTimeline(report) {
  const history = report.execution_history
    .map((execution, index) => {
      const debug = report.debug_history[index];
      return `
        <div class="timeline-card">
          <h3>Iteration ${index + 1}</h3>
          <span>Status: ${execution.status}</span>
          <p>${execution.tests_collected ?? "n/a"} collected, exit code ${execution.exit_code}, duration ${execution.duration_seconds.toFixed(2)}s.</p>
          <p>${debug ? debug.diagnosis : "No debugger intervention needed."}</p>
        </div>
      `;
    })
    .join("");

  els.timeline.innerHTML = history || `<div class="empty">No timeline yet.</div>`;
}

function setSummary(report) {
  const generated = report.generation_history.at(-1);
  const lines = [
    `Repository: ${report.repository_path}`,
    `Planner summary: ${report.plan.summary}`,
    `Generator summary: ${generated ? generated.summary : "n/a"}`,
  ];
  els.summary.innerHTML = `
    <div class="json-card">
      <h3>Run Summary</h3>
      <pre>${lines.join("\n")}</pre>
    </div>
  `;
}

function setLogs(report) {
  const execution = report.execution_history.at(-1);
  if (!execution) {
    els.logs.innerHTML = `<div class="empty">Execution logs will appear here.</div>`;
    return;
  }

  els.logs.innerHTML = `
    <div class="split">
      <div class="log-card">
        <h3>stdout</h3>
        <pre>${escapeHtml(execution.stdout || "No stdout output.")}</pre>
      </div>
      <div class="log-card">
        <h3>stderr</h3>
        <pre>${escapeHtml(execution.stderr || "No stderr output.")}</pre>
      </div>
    </div>
  `;
}

function setJson(report) {
  els.json.innerHTML = `
    <div class="json-card">
      <h3>Structured Report</h3>
      <pre>${escapeHtml(JSON.stringify(report, null, 2))}</pre>
    </div>
  `;
}

function renderReport(report) {
  state.runId = report.run_id;
  state.latestReport = report;
  setStatus(report.status.toUpperCase(), report.status);
  setMetrics(report);
  setTimeline(report);
  setSummary(report);
  setLogs(report);
  setJson(report);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function runOrchestration(event) {
  event.preventDefault();
  els.runButton.disabled = true;
  setStatus("Running orchestration...");

  const payload = {
    repository_path: els.repositoryPath.value.trim(),
    max_retries: Number(els.maxRetries.value),
  };

  try {
    const response = await fetch("/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Request failed.");
    }
    renderReport(data);
  } catch (error) {
    setStatus("ERROR", "error");
    els.summary.innerHTML = `
      <div class="json-card">
        <h3>Request Error</h3>
        <pre>${escapeHtml(String(error.message || error))}</pre>
      </div>
    `;
  } finally {
    els.runButton.disabled = false;
  }
}

async function loadLatestReport() {
  if (!state.runId) {
    setStatus("No run selected");
    return;
  }

  const response = await fetch(`/runs/${state.runId}/report`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Failed to load report.");
  }
  renderReport(data);
}

els.form.addEventListener("submit", runOrchestration);
els.sampleButton.addEventListener("click", () => {
  els.repositoryPath.value = samplePath;
});
els.reportButton.addEventListener("click", async () => {
  try {
    await loadLatestReport();
  } catch (error) {
    setStatus("ERROR", "error");
  }
});

setStatus("Ready");
els.repositoryPath.value = samplePath;
