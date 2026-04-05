const state = {
  runId: null,
  latestReport: null,
  samplePath: "",
};

const systemState = {
  ai_provider: "heuristic",
  ai_model: null,
  openai_configured: false,
  reasoning_effort: null,
};

const els = {
  form: document.getElementById("orchestrate-form"),
  repositoryPath: document.getElementById("repository_path"),
  repoArchive: document.getElementById("repo_archive"),
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
  recentRuns: document.getElementById("recent-runs"),
  loading: document.getElementById("loading-indicator"),
  modelChip: document.getElementById("model-chip"),
  modelHint: document.getElementById("model-hint"),
  repoArchiveName: document.getElementById("repo-archive-name"),
  uploadFeedback: document.getElementById("upload-feedback"),
};

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function setStatus(text, variant = "") {
  const normalizedVariant = String(variant || "").toLowerCase();
  const loweredText = String(text || "").toLowerCase();
  let stateName = "idle";

  if (normalizedVariant.includes("error") || loweredText.includes("error")) {
    stateName = "error";
  } else if (loweredText.includes("running") || loweredText.includes("uploading")) {
    stateName = "running";
  } else if (normalizedVariant.includes("passed") || normalizedVariant.includes("failed") || normalizedVariant.includes("completed")) {
    stateName = "completed";
  }

  if (stateName === "idle") {
    els.status.textContent = "Idle";
  } else if (stateName === "running") {
    els.status.textContent = "Running";
  } else if (stateName === "completed") {
    els.status.textContent = "Completed";
  } else {
    els.status.textContent = "Error";
  }

  els.status.className = `status-pill ${stateName}`.trim();
}

function setLoading(visible) {
  if (!els.loading) {
    return;
  }
  els.loading.classList.toggle("visible", Boolean(visible));
  els.loading.setAttribute("aria-hidden", String(!visible));
}

function setUploadFeedback(message, tone = "") {
  if (!els.uploadFeedback) {
    return;
  }
  els.uploadFeedback.textContent = message;
  els.uploadFeedback.className = `upload-feedback${tone ? ` is-${tone}` : ""}`;
}

function getSelectedUploadLabel(files) {
  if (files.length === 0) {
    return "No file selected";
  }

  if (files.length === 1) {
    const selected = files[0];
    return selected.webkitRelativePath ? selected.webkitRelativePath : selected.name;
  }

  const rootNames = new Set(
    files
      .map((file) => file.webkitRelativePath || file.name)
      .map((path) => path.split(/[\\/]/, 1)[0])
      .filter(Boolean),
  );

  if (rootNames.size === 1) {
    return `${files.length} files from ${Array.from(rootNames)[0]}`;
  }

  return `${files.length} files selected`;
}

async function ensureSamplePath() {
  if (state.samplePath) {
    return state.samplePath;
  }

  const response = await fetch("/sample-repository");
  const raw = await response.text();
  const data = raw ? JSON.parse(raw) : {};
  if (!response.ok || !data.repository_path) {
    throw new Error((typeof data?.detail === "string" && data.detail) || "Sample repository is unavailable.");
  }

  state.samplePath = data.repository_path;
  return state.samplePath;
}

function getModelDisplay(provider, model) {
  if (provider === "openai") {
    return model || "gpt-5-mini";
  }
  return "Heuristic fallback";
}

function setMetrics(report) {
  const execution = report.execution_history.at(-1);
  const latestGeneration = report.generation_history.at(-1);
  const cards = [
    { label: "Run ID", value: report.run_id, sublabel: report.status.toUpperCase() },
    { label: "Iterations", value: String(report.iterations), sublabel: "retry loop" },
    { label: "Tests", value: execution?.tests_collected != null ? String(execution.tests_collected) : "n/a", sublabel: "collected" },
    {
      label: "AI Model",
      value: getModelDisplay(latestGeneration?.provider ?? systemState.ai_provider, latestGeneration?.model ?? systemState.ai_model),
      sublabel: latestGeneration?.provider ?? systemState.ai_provider,
    },
  ];

  els.metrics.innerHTML = cards
    .map(
      (card) => `
        <div class="metric">
          <div class="metric-label">${card.label}</div>
          <strong>${escapeHtml(card.value)}</strong>
          <div class="metric-meta">${escapeHtml(card.sublabel)}</div>
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
        <div class="timeline-card reveal-card">
          <h3>Iteration ${index + 1}</h3>
          <span>Status: ${escapeHtml(execution.status)}</span>
          <p>${execution.tests_collected ?? "n/a"} collected, exit code ${execution.exit_code}, duration ${execution.duration_seconds.toFixed(2)}s.</p>
          <p>${escapeHtml(debug ? debug.diagnosis : "No debugger intervention needed.")}</p>
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
    `AI provider: ${generated?.provider ?? systemState.ai_provider}`,
    `AI model: ${generated?.model ?? (systemState.ai_model || "heuristic fallback")}`,
  ];

  els.summary.innerHTML = `
    <div class="json-card">
      <h3>Run Summary</h3>
      <pre>${escapeHtml(lines.join("\n"))}</pre>
    </div>
  `;
}

function getLogIcon(line) {
  const text = String(line).toLowerCase();
  if (text.includes("analyzing")) return ">";
  if (text.includes("generating")) return "+";
  if (text.includes("error") || text.includes("failed")) return "x";
  if (text.includes("fix") || text.includes("retry")) return "*";
  if (text.includes("success") || text.includes("passed") || text.includes("complete")) return "o";
  return "-";
}

function streamLogLines(container, lines) {
  if (!container) {
    return;
  }

  const safeLines = lines.length > 0 ? lines : ["No output."];
  container.innerHTML = "";
  safeLines.forEach((line, index) => {
    const row = document.createElement("div");
    row.className = "terminal-line";
    row.innerHTML = `<span class="log-icon">${escapeHtml(getLogIcon(line))}</span><span class="log-text">${escapeHtml(line)}</span>`;
    row.style.animationDelay = `${index * 24}ms`;
    container.appendChild(row);
  });
}

function setLogs(report) {
  const execution = report.execution_history.at(-1);
  if (!execution) {
    els.logs.innerHTML = `<div class="empty">Execution logs will appear here.</div>`;
    return;
  }

  els.logs.innerHTML = `
    <div class="split logs-split">
      <div class="log-card terminal-card">
        <h3>stdout</h3>
        <div class="terminal" data-log-target="stdout"></div>
      </div>
      <div class="log-card terminal-card">
        <h3>stderr</h3>
        <div class="terminal" data-log-target="stderr"></div>
      </div>
    </div>
  `;

  streamLogLines(
    els.logs.querySelector('[data-log-target="stdout"]'),
    String(execution.stdout || "No stdout output.").split(/\r?\n/).filter((line) => line.trim().length > 0),
  );
  streamLogLines(
    els.logs.querySelector('[data-log-target="stderr"]'),
    String(execution.stderr || "No stderr output.").split(/\r?\n/).filter((line) => line.trim().length > 0),
  );
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
  setStatus("Completed", "completed");
  setMetrics(report);
  setTimeline(report);
  setSummary(report);
  setLogs(report);
  setJson(report);
  loadRecentRuns();
}

async function runOrchestration(event) {
  event.preventDefault();
  els.runButton.disabled = true;
  setLoading(true);
  setStatus("Running orchestration...", "running");

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

    const raw = await response.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = {};
      }
    }
    if (!response.ok) {
      throw new Error((typeof data?.detail === "string" && data.detail) || raw || "Request failed.");
    }
    renderReport(data);
  } catch (error) {
    setStatus("ERROR", "error");
    els.summary.innerHTML = `
      <div class="json-card">
        <h3>Request Error</h3>
        <pre>${escapeHtml(error.message || error)}</pre>
      </div>
    `;
  } finally {
    setLoading(false);
    els.runButton.disabled = false;
  }
}

async function uploadArchive() {
  const files = Array.from(els.repoArchive.files || []);
  if (files.length === 0) {
    setStatus("Choose a file first", "error");
    setUploadFeedback("Choose a file or archive first.", "error");
    return;
  }

  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file, file.webkitRelativePath || file.name);
  });
  setLoading(true);
  setStatus("Uploading repository...", "running");
  setUploadFeedback(`Uploading ${getSelectedUploadLabel(files)}...`, "busy");

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });
    const raw = await response.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = {};
      }
    }
    if (!response.ok) {
      const message = (typeof data?.detail === "string" && data.detail) || raw || "Upload failed.";
      throw new Error(message);
    }
    els.repositoryPath.value = data.repository_path;
    if (els.repoArchiveName) {
      els.repoArchiveName.textContent = `${getSelectedUploadLabel(files)} ready`;
    }
    setUploadFeedback("Upload complete. Repository path has been filled in.", "success");
    setStatus(`Uploaded ${data.original_filename}`);
  } catch (error) {
    setStatus("UPLOAD ERROR", "error");
    setUploadFeedback(error.message || "Upload failed.", "error");
    els.summary.innerHTML = `
      <div class="json-card">
        <h3>Upload Error</h3>
        <pre>${escapeHtml(error.message || error)}</pre>
      </div>
    `;
  } finally {
    setLoading(false);
  }
}

function handleArchiveSelection() {
  const files = Array.from(els.repoArchive.files || []);
  if (!els.repoArchiveName) {
    return;
  }
  els.repoArchiveName.textContent = getSelectedUploadLabel(files);
  if (files.length > 0) {
    setUploadFeedback("File selected. Uploading now...", "busy");
    void uploadArchive();
  } else {
    setUploadFeedback("The upload starts as soon as you choose a file or archive.");
  }
}

async function loadLatestReport() {
  if (!state.runId) {
    setStatus("No run selected");
    return;
  }

  const response = await fetch(`/runs/${state.runId}/report`);
  const raw = await response.text();
  const data = raw ? JSON.parse(raw) : {};
  if (!response.ok) {
    throw new Error((typeof data?.detail === "string" && data.detail) || "Failed to load report.");
  }
  renderReport(data);
}

async function loadRecentRuns() {
  const response = await fetch("/runs");
  const raw = await response.text();
  let data = [];
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = [];
    }
  }
  if (!response.ok) {
    return;
  }

  els.recentRuns.innerHTML =
    data.length > 0
      ? data
          .map(
            (run) => `
              <button class="run-item" type="button" data-run-id="${run.run_id}">
                <span>${run.run_id}</span>
                <strong>${escapeHtml(run.status)}</strong>
                <small>${run.iterations} iterations | ${run.latest_test_count ?? "n/a"} tests</small>
              </button>
            `,
          )
          .join("")
      : `<div class="empty">No completed runs yet.</div>`;

  els.recentRuns.querySelectorAll("[data-run-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const runId = button.getAttribute("data-run-id");
      const reportResponse = await fetch(`/runs/${runId}/report`);
      const report = await reportResponse.json();
      if (reportResponse.ok) {
        renderReport(report);
      }
    });
  });
}

async function loadSystemStatus() {
  try {
    const response = await fetch("/system/status");
    const raw = await response.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = {};
      }
    }
    if (!response.ok) {
      return;
    }

    Object.assign(systemState, data);

    if (els.modelChip) {
      els.modelChip.textContent = data.ai_provider === "openai" ? `OpenAI ${data.ai_model}` : "Heuristic fallback mode";
    }

    if (els.modelHint) {
      els.modelHint.textContent =
        data.ai_provider === "openai"
          ? `AI generation is active with ${data.ai_model} (${data.reasoning_effort} reasoning).`
          : "OpenAI key not configured. The app is using the built-in heuristic generator.";
    }
  } catch (error) {
    if (els.modelHint) {
      els.modelHint.textContent = "AI model status could not be loaded.";
    }
  }
}

els.form.addEventListener("submit", runOrchestration);
els.repoArchive.addEventListener("change", handleArchiveSelection);
els.sampleButton.addEventListener("click", async () => {
  try {
    els.repositoryPath.value = await ensureSamplePath();
    setStatus("Sample repository ready");
  } catch (error) {
    setStatus("ERROR", "error");
    setUploadFeedback(error.message || "Sample repository is unavailable.", "error");
  }
});
els.reportButton.addEventListener("click", async () => {
  try {
    await loadLatestReport();
  } catch (error) {
    setStatus("ERROR", "error");
  }
});

setStatus("Idle", "idle");
ensureSamplePath()
  .then((repositoryPath) => {
    els.repositoryPath.value = repositoryPath;
  })
  .catch(() => {
    if (els.modelHint) {
      els.modelHint.textContent = "Sample repository is unavailable in this environment. Upload a project or enter a path manually.";
    }
  });
loadSystemStatus();
loadRecentRuns();
