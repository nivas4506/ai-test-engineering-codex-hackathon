const STORAGE_KEY = "ai-test-engineering-mission";

const state = {
  runId: null,
  latestReport: null,
  samplePath: "",
  uploadId: null,
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
  targetInput: document.getElementById("target_input"),
  testingObjective: document.getElementById("testing_objective"),
  repoArchive: document.getElementById("repo_archive"),
  maxRetries: document.getElementById("max_retries"),
  modelName: document.getElementById("model_name"),
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
  projectSourceHint: document.getElementById("project-source-hint"),
};

const modelState = {
  options: [],
  selected: "",
};

function readStoredMission() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function isWindowsAbsolutePath(value) {
  return /^[A-Za-z]:[\\/]/.test(String(value || ""));
}

function isProductionHost() {
  return !["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function sanitizeStoredMission(stored) {
  const next = { ...stored };
  if (isProductionHost() && isWindowsAbsolutePath(next.repository_path)) {
    next.repository_path = "";
    next.upload_id = null;
    next.run_id = null;
  }
  return next;
}

function writeStoredMission(partial) {
  const nextValue = sanitizeStoredMission({ ...readStoredMission(), ...partial });
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextValue));
}

function getNormalizedRepositoryPath() {
  return els.repositoryPath?.value.trim() || "";
}

function hasRunnableProject() {
  return Boolean(getNormalizedRepositoryPath() || state.uploadId);
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function getModelLabel(modelId) {
  const labels = {
    "automation-fast": "AI automation trio",
    "gpt-5-mini": "GPT-5 mini",
    "gpt-5": "GPT-5",
    "gpt-5.1": "GPT-5.1",
    "gpt-5-codex": "GPT-5 Codex",
    "gpt-5.1-codex": "GPT-5.1 Codex",
    "gpt-5.1-codex-mini": "GPT-5.1 Codex mini",
    heuristic: "Heuristic fallback",
  };
  return labels[modelId] || modelId || "Heuristic fallback";
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
    return getModelLabel(model || "automation-fast");
  }
  return "Heuristic fallback";
}

function setMetrics(report) {
  if (!els.metrics) {
    return;
  }
  const execution = report.execution_history.at(-1);
  const latestGeneration = report.generation_history.at(-1);
  const languageSummary = report.analysis.detected_languages.length > 0 ? report.analysis.detected_languages.join(", ") : "unknown";
  const cards = [
    { label: "Run ID", value: report.run_id, sublabel: report.status.toUpperCase() },
    { label: "Iterations", value: String(report.iterations), sublabel: "retry loop" },
    { label: "Tests", value: execution?.tests_collected != null ? String(execution.tests_collected) : "n/a", sublabel: "collected" },
    {
      label: "AI Model",
      value: getModelDisplay(latestGeneration?.provider ?? systemState.ai_provider, latestGeneration?.model ?? systemState.ai_model),
      sublabel: `${latestGeneration?.provider ?? systemState.ai_provider} | ${languageSummary}`,
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
  if (!els.timeline) {
    return;
  }
  const phaseLabels = ["Scout + Builder", "Runner", "Debugger"];
  const history = report.execution_history
    .map((execution, index) => {
      const debug = report.debug_history[index];
      const phaseLine = debug ? `${phaseLabels[0]} -> ${phaseLabels[1]} -> ${phaseLabels[2]}` : `${phaseLabels[0]} -> ${phaseLabels[1]}`;
      return `
        <div class="timeline-card reveal-card">
          <h3>Iteration ${index + 1}</h3>
          <span>Status: ${escapeHtml(execution.status)} | ${escapeHtml(phaseLine)}</span>
          <p>${execution.tests_collected ?? "n/a"} collected, exit code ${execution.exit_code}, duration ${execution.duration_seconds.toFixed(2)}s.</p>
          <p>${escapeHtml(debug ? debug.diagnosis : "No debugger intervention needed.")}</p>
        </div>
      `;
    })
    .join("");

  els.timeline.innerHTML = history || `<div class="empty">No timeline yet.</div>`;
}

function setSummary(report) {
  if (!els.summary) {
    return;
  }
  const generated = report.generation_history.at(-1);
  const execution = report.execution_history.at(-1);
  const moduleCount = report.analysis.summary?.total_modules ?? report.analysis.modules.length;
  const functionCount = report.analysis.summary?.total_functions ?? report.analysis.modules.reduce((count, module) => count + module.functions.length, 0);
  const classCount = report.analysis.summary?.total_classes ?? report.analysis.modules.reduce((count, module) => count + (module.class_names?.length || 0), 0);
  const endpointCount = report.analysis.summary?.total_api_endpoints ?? (report.analysis.api_endpoints?.length || 0);
  const latestDebug = report.debug_history.at(-1);
  const topFinding = latestDebug?.findings?.[0];
  const topFix = latestDebug?.fix_suggestions?.[0];
  const nextMove = report.status === "passed"
    ? "Agent finished successfully. Review logs and export the report."
    : report.debug_history.at(-1)?.diagnosis || "Agent stopped after the latest execution error.";
  const sections = [
    {
      title: "Multi-Agent Architecture",
      items: [
        `Architecture: ${report.architecture || "multi_agent"}`,
        `Memory records: ${report.memory_context?.length || 0}`,
        `Agent trace entries: ${report.agent_trace?.length || 0}`,
      ],
    },
    {
      title: "Test Plan",
      items: report.test_plan?.length
        ? report.test_plan.slice(0, 5).map((item) => `${item.category.toUpperCase()} | ${item.title} -> ${item.target}`)
        : ["No explicit test plan was recorded."],
    },
    {
      title: "Execution Steps",
      items: report.execution_steps?.length
        ? report.execution_steps.slice(0, 5).map((step) => {
            const parts = [step.action];
            if (step.value) parts.push(step.value);
            if (step.selector) parts.push(`selector=${step.selector}`);
            if (step.expected) parts.push(`expect=${step.expected}`);
            return parts.join(" | ");
          })
        : ["No structured execution steps were recorded."],
    },
    {
      title: "Codebase Analysis",
      items: [
        `${moduleCount} modules`,
        `${functionCount} functions`,
        `${classCount} classes`,
        `${endpointCount} endpoints`,
        `${report.analysis.dependency_map?.length || 0} dependency links`,
      ],
    },
    {
      title: "Test Generation",
      items: generated
        ? [
            `${generated.generated_files.length} generated files`,
            generated.summary,
            ...generated.generated_files.slice(0, 3).map((file) => PathLabel(file.file_path, file.strategy)),
          ]
        : ["No generation record available."],
    },
    {
      title: "Execution Report",
      items: execution
        ? [
            `Status: ${execution.status.toUpperCase()}`,
            `Exit code: ${execution.exit_code}`,
            `Collected tests: ${execution.tests_collected ?? "n/a"}`,
            `Duration: ${execution.duration_seconds.toFixed(2)}s`,
          ]
        : ["No execution record available."],
    },
    {
      title: "Bug Report",
      items: topFinding
        ? [
            `Severity: ${topFinding.severity.toUpperCase()}`,
            `Issue: ${topFinding.title}`,
            topFinding.root_cause,
            `Location: ${topFinding.file_path || "n/a"}${topFinding.line_number ? `:${topFinding.line_number}` : ""}`,
          ]
        : ["No blocking bug was reported after the latest execution."],
    },
    {
      title: "Fix Suggestion",
      items: topFix
        ? [
            topFix.title,
            topFix.summary,
            `Target: ${topFix.file_path || "n/a"}${topFix.line_number ? `:${topFix.line_number}` : ""}`,
          ]
        : [nextMove],
    },
    {
      title: "Coverage and Improvement",
      items: report.coverage_report
        ? [
            `${report.coverage_report.estimated_line_coverage}% estimated line coverage`,
            `Missing gaps: ${report.coverage_report.missing_edge_cases.length}`,
            report.improvement_report?.rerun_summary || nextMove,
          ]
        : ["Coverage estimate unavailable."],
    },
    {
      title: "Observations and Final Report",
      items: report.observations?.length
        ? [
            ...report.observations.slice(0, 3).map((item) => `${item.status.toUpperCase()} | ${item.title} -> ${item.detail}`),
            `Tests run: ${report.final_structured_report?.tests_run ?? 0}`,
            `Passed: ${report.final_structured_report?.passed ?? 0} | Failed: ${report.final_structured_report?.failed ?? 0}`,
          ]
        : ["No structured observations were recorded."],
    },
    {
      title: "Memory and Agent Trace",
      items: report.agent_trace?.length
        ? report.agent_trace.slice(0, 5).map((entry) => `${entry.agent.toUpperCase()} | ${entry.status.toUpperCase()} -> ${entry.summary}`)
        : ["No agent trace was recorded."],
    },
  ];

  els.summary.innerHTML = `
    <div class="assessment-grid">
      ${sections
        .map(
          (section) => `
            <article class="assessment-section">
              <span>${escapeHtml(section.title)}</span>
              <ul class="assessment-list">
                ${section.items
                  .map((item) => `<li>${escapeHtml(item)}</li>`)
                  .join("")}
              </ul>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function PathLabel(path, strategy) {
  const fileName = String(path).split(/[\\/]/).pop();
  return `${fileName} -> ${strategy}`;
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
  if (!els.logs) {
    return;
  }
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
  if (!els.json) {
    return;
  }
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
  writeStoredMission({ run_id: report.run_id });
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
  if (els.runButton) {
    els.runButton.disabled = true;
  }
  setLoading(true);
  setStatus("Running orchestration...", "running");

  if (!hasRunnableProject()) {
    setLoading(false);
    setStatus("ERROR", "error");
    els.summary.innerHTML = `
      <div class="json-card">
        <h3>Agent Request Error</h3>
        <pre>${escapeHtml("Upload a project or provide a valid repository path before launching the tester agent.")}</pre>
      </div>
    `;
    if (els.runButton) {
      els.runButton.disabled = false;
    }
    return;
  }

  const payload = {
    repository_path: getNormalizedRepositoryPath() || null,
    max_retries: Number(els.maxRetries?.value),
    model: els.modelName?.value || null,
    upload_id: state.uploadId,
    target_input: els.targetInput?.value.trim() || null,
    testing_objective: els.testingObjective?.value.trim() || null,
  };
  writeStoredMission(payload);

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
        <h3>Agent Request Error</h3>
        <pre>${escapeHtml(error.message || error)}</pre>
      </div>
    `;
  } finally {
    setLoading(false);
    if (els.runButton) {
      els.runButton.disabled = false;
    }
  }
}

async function uploadArchive() {
  if (!els.repoArchive) {
    return;
  }
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
    els.repositoryPath.value = "";
    state.uploadId = data.upload_id || null;
    writeStoredMission({
      repository_path: "",
      upload_id: state.uploadId,
      max_retries: Number(els.maxRetries?.value || 2),
      model: els.modelName?.value || "heuristic",
    });
    if (els.repoArchiveName) {
      els.repoArchiveName.textContent = `${getSelectedUploadLabel(files)} ready`;
    }
    setUploadFeedback("Upload complete. The tester agent can use this uploaded project directly.", "success");
    setStatus(`Agent ready for ${data.original_filename}`);
    if (els.projectSourceHint) {
      els.projectSourceHint.textContent = `Uploaded project ready (${data.upload_id}). The tester agent can run directly from this bundle.`;
    }
  } catch (error) {
    setStatus("UPLOAD ERROR", "error");
    setUploadFeedback(error.message || "Upload failed.", "error");
    els.summary.innerHTML = `
      <div class="json-card">
        <h3>Agent Upload Error</h3>
        <pre>${escapeHtml(error.message || error)}</pre>
      </div>
    `;
  } finally {
    setLoading(false);
  }
}

function handleArchiveSelection() {
  if (!els.repoArchive) {
    return;
  }
  const files = Array.from(els.repoArchive.files || []);
  if (!els.repoArchiveName) {
    return;
  }
  els.repoArchiveName.textContent = getSelectedUploadLabel(files);
  if (files.length > 0) {
    setUploadFeedback("File selected. Uploading now...", "busy");
    void uploadArchive();
  } else {
    setUploadFeedback("The upload starts as soon as you choose a folder, archive, or source file.");
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
  if (!els.recentRuns) {
    return;
  }
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
      els.modelChip.textContent = data.ai_provider === "openai" ? `OpenAI ${getModelLabel(data.ai_model)}` : "Heuristic fallback mode";
    }

    if (els.modelHint) {
      els.modelHint.textContent =
        data.ai_provider === "openai"
          ? `Tester agent generation is active with ${getModelLabel(data.ai_model)} (${data.reasoning_effort} reasoning).`
          : "OpenAI key not configured. The tester agent is using the built-in heuristic generator.";
    }
  } catch (error) {
    if (els.modelHint) {
      els.modelHint.textContent = "Tester agent model status could not be loaded.";
    }
  }
}

function renderModelOptions(models) {
  if (!els.modelName) {
    return;
  }

  modelState.options = models;
  const stored = readStoredMission();
  const selected = modelState.selected || stored.model || systemState.ai_model || "heuristic";
  els.modelName.innerHTML = models
    .map((model) => {
      const disabled = model.provider === "openai" && !model.available ? " disabled" : "";
      const selectedAttr = selected === model.id ? " selected" : "";
      const suffix = model.recommended ? " (recommended)" : "";
      return `<option value="${escapeHtml(model.id)}"${disabled}${selectedAttr}>${escapeHtml(model.label + suffix)}</option>`;
    })
    .join("");

  if (!models.some((model) => model.id === selected)) {
    els.modelName.value = models[0]?.id || "";
  }
}

async function loadAvailableModels() {
  if (!els.modelName) {
    return;
  }

  try {
    const response = await fetch("/system/models");
    const raw = await response.text();
    let data = [];
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = [];
      }
    }
    if (!response.ok || !Array.isArray(data) || data.length === 0) {
      throw new Error("No model list available.");
    }
    renderModelOptions(data);
  } catch {
    els.modelName.innerHTML = '<option value="heuristic">Heuristic fallback</option>';
  }
}

if (els.modelName) {
  els.modelName.addEventListener("change", () => {
    modelState.selected = els.modelName.value;
    writeStoredMission({ model: modelState.selected });
    const selectedModel = modelState.options.find((item) => item.id === modelState.selected);
    if (selectedModel && els.modelHint) {
      els.modelHint.textContent = selectedModel.description;
    }
  });
}

if (els.form) {
  els.form.addEventListener("submit", runOrchestration);
}
if (els.repoArchive) {
  els.repoArchive.addEventListener("change", handleArchiveSelection);
}
if (els.sampleButton) {
  els.sampleButton.addEventListener("click", async () => {
    try {
      const repositoryPath = await ensureSamplePath();
      if (els.repositoryPath) {
        els.repositoryPath.value = repositoryPath;
      }
      state.uploadId = null;
      writeStoredMission({
      repository_path: repositoryPath,
      upload_id: null,
      max_retries: Number(els.maxRetries?.value || 2),
      model: els.modelName?.value || "heuristic",
      target_input: els.targetInput?.value.trim() || null,
      testing_objective: els.testingObjective?.value.trim() || null,
      });
      setStatus("Sample repository ready");
      if (els.projectSourceHint) {
        els.projectSourceHint.textContent = "Sample repository selected. The tester agent will use the server-side sample path.";
      }
    } catch (error) {
      setStatus("ERROR", "error");
      setUploadFeedback(error.message || "Sample repository is unavailable.", "error");
    }
  });
}
if (els.reportButton) {
  els.reportButton.addEventListener("click", async () => {
    try {
      await loadLatestReport();
    } catch (error) {
      setStatus("ERROR", "error");
    }
  });
}

function applyStoredMission() {
  const stored = sanitizeStoredMission(readStoredMission());
  if (JSON.stringify(stored) !== JSON.stringify(readStoredMission())) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  }
  if (stored.repository_path && els.repositoryPath) {
    els.repositoryPath.value = stored.repository_path;
  }
  if (typeof stored.max_retries === "number" && els.maxRetries) {
    els.maxRetries.value = String(stored.max_retries);
  }
  if (stored.target_input && els.targetInput) {
    els.targetInput.value = stored.target_input;
  }
  if (stored.testing_objective && els.testingObjective) {
    els.testingObjective.value = stored.testing_objective;
  }
  if (stored.upload_id) {
    state.uploadId = stored.upload_id;
  }
  if (stored.run_id) {
    state.runId = stored.run_id;
  }
  if (els.projectSourceHint) {
    els.projectSourceHint.textContent = state.uploadId
      ? `Uploaded project ready (${state.uploadId}). The tester agent can run directly from this bundle.`
      : "If you came from the upload page, the tester agent can run directly from that uploaded project.";
  }
}

setStatus("Idle", "idle");
applyStoredMission();
if (els.repositoryPath && !els.repositoryPath.value.trim() && !state.uploadId) {
  ensureSamplePath()
    .then((repositoryPath) => {
      els.repositoryPath.value = repositoryPath;
    })
    .catch(() => {
      if (els.modelHint) {
        els.modelHint.textContent = "Sample repository is unavailable in this environment. Upload a project and launch the tester agent manually.";
      }
    });
}
loadSystemStatus();
loadAvailableModels();
loadRecentRuns();
