const STORAGE_KEY = "ai-test-engineering-mission";

const state = {
  uploadId: null,
  samplePath: "",
};

const systemState = {
  ai_provider: "heuristic",
  ai_model: null,
  openai_configured: false,
  reasoning_effort: null,
};

const modelState = {
  options: [],
  selected: "",
};

const els = {
  form: document.getElementById("mission-form"),
  repositoryPath: document.getElementById("repository_path"),
  repoArchive: document.getElementById("repo_archive"),
  maxRetries: document.getElementById("max_retries"),
  modelName: document.getElementById("model_name"),
  continueButton: document.getElementById("continue-button"),
  sampleButton: document.getElementById("sample-button"),
  status: document.getElementById("upload-status"),
  loading: document.getElementById("loading-indicator"),
  modelChip: document.getElementById("model-chip"),
  modelHint: document.getElementById("model-hint"),
  repoArchiveName: document.getElementById("repo-archive-name"),
  uploadFeedback: document.getElementById("upload-feedback"),
  missionSummary: document.getElementById("mission-summary"),
  recentRuns: document.getElementById("recent-runs"),
  uploadModelName: document.getElementById("upload-model-name"),
  uploadModelMeta: document.getElementById("upload-model-meta"),
};

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

function setStatus(text, variant = "") {
  if (!els.status) {
    return;
  }
  const normalizedVariant = String(variant || "").toLowerCase();
  const loweredText = String(text || "").toLowerCase();
  let stateName = "idle";

  if (normalizedVariant.includes("error") || loweredText.includes("error")) {
    stateName = "error";
  } else if (loweredText.includes("uploading") || loweredText.includes("loading")) {
    stateName = "running";
  } else if (normalizedVariant.includes("completed") || loweredText.includes("ready")) {
    stateName = "completed";
  }

  els.status.textContent = stateName === "error" ? "Error" : stateName === "running" ? "Uploading" : stateName === "completed" ? "Ready" : "Idle";
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
    return files[0].webkitRelativePath || files[0].name;
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

function updateMissionSummary() {
  if (!els.missionSummary) {
    return;
  }

  const selectedModel = modelState.options.find((item) => item.id === (els.modelName?.value || ""));
  const repositoryValue = els.repositoryPath?.value.trim() || "No repository selected yet.";
  const uploadValue = state.uploadId ? `Upload stored as ${state.uploadId}.` : "Waiting for a file, folder, or archive.";
  const modelValue = selectedModel
    ? `${selectedModel.label}${selectedModel.recommended ? " (recommended)" : ""}`
    : "Loading available testing models.";
  const nextValue = repositoryValue && repositoryValue !== "No repository selected yet."
    ? "Continue to the run page to launch the tester agent."
    : "Choose a repository path or upload a project before continuing.";

  els.missionSummary.innerHTML = `
    <article class="agent-brief-card">
      <span>Repository</span>
      <p>${escapeHtml(repositoryValue)}</p>
    </article>
    <article class="agent-brief-card">
      <span>Upload</span>
      <p>${escapeHtml(uploadValue)}</p>
    </article>
    <article class="agent-brief-card">
      <span>Model</span>
      <p>${escapeHtml(modelValue)}</p>
    </article>
    <article class="agent-brief-card">
      <span>Next</span>
      <p>${escapeHtml(nextValue)}</p>
    </article>
  `;
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

async function uploadArchive() {
  const files = Array.from(els.repoArchive?.files || []);
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
    const response = await fetch("/upload", { method: "POST", body: formData });
    const raw = await response.text();
    const data = raw ? JSON.parse(raw) : {};
    if (!response.ok) {
      throw new Error((typeof data?.detail === "string" && data.detail) || raw || "Upload failed.");
    }

    state.uploadId = data.upload_id || null;
    els.repositoryPath.value = data.repository_path;
    if (els.repoArchiveName) {
      els.repoArchiveName.textContent = `${getSelectedUploadLabel(files)} ready`;
    }
    writeStoredMission({
      repository_path: data.repository_path,
      upload_id: state.uploadId,
      max_retries: Number(els.maxRetries?.value || 2),
      model: els.modelName?.value || "heuristic",
    });
    setUploadFeedback("Upload complete. Continue to the run page when ready.", "success");
    setStatus("Repository ready", "completed");
    updateMissionSummary();
  } catch (error) {
    setStatus("Upload error", "error");
    setUploadFeedback(error.message || "Upload failed.", "error");
  } finally {
    setLoading(false);
  }
}

function handleArchiveSelection() {
  const files = Array.from(els.repoArchive?.files || []);
  if (els.repoArchiveName) {
    els.repoArchiveName.textContent = getSelectedUploadLabel(files);
  }
  if (files.length > 0) {
    setUploadFeedback("File selected. Uploading now...", "busy");
    void uploadArchive();
  } else {
    setUploadFeedback("Choose a folder, archive, or file and it will upload automatically.");
  }
}

async function loadSystemStatus() {
  try {
    const response = await fetch("/system/status");
    const raw = await response.text();
    const data = raw ? JSON.parse(raw) : {};
    if (!response.ok) {
      return;
    }

    Object.assign(systemState, data);

    const modelName = data.ai_provider === "openai" ? getModelLabel(data.ai_model) : "Heuristic fallback";
    const modelMeta = data.ai_provider === "openai"
      ? `${data.reasoning_effort} reasoning enabled`
      : "Built-in generator active";

    if (els.modelChip) {
      els.modelChip.textContent = data.ai_provider === "openai" ? `OpenAI ${getModelLabel(data.ai_model)}` : "Heuristic fallback mode";
    }
    if (els.modelHint) {
      els.modelHint.textContent = data.ai_provider === "openai"
        ? `Tester agent generation is active with ${getModelLabel(data.ai_model)} (${data.reasoning_effort} reasoning).`
        : "OpenAI key not configured. The tester agent is using the built-in heuristic generator.";
    }
    if (els.uploadModelName) {
      els.uploadModelName.textContent = modelName;
    }
    if (els.uploadModelMeta) {
      els.uploadModelMeta.textContent = modelMeta;
    }
  } catch {
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
  const selected = stored.model || systemState.ai_model || "heuristic";
  els.modelName.innerHTML = models
    .map((model) => {
      const disabled = model.provider === "openai" && !model.available ? " disabled" : "";
      const selectedAttr = model.id === selected ? " selected" : "";
      const suffix = model.recommended ? " (recommended)" : "";
      return `<option value="${escapeHtml(model.id)}"${disabled}${selectedAttr}>${escapeHtml(model.label + suffix)}</option>`;
    })
    .join("");
  updateMissionSummary();
}

async function loadAvailableModels() {
  if (!els.modelName) {
    return;
  }
  try {
    const response = await fetch("/system/models");
    const raw = await response.text();
    const data = raw ? JSON.parse(raw) : [];
    if (!response.ok || !Array.isArray(data) || data.length === 0) {
      throw new Error("No model list available.");
    }
    renderModelOptions(data);
  } catch {
    els.modelName.innerHTML = '<option value="heuristic">Heuristic fallback</option>';
    updateMissionSummary();
  }
}

async function loadRecentRuns() {
  if (!els.recentRuns) {
    return;
  }

  const response = await fetch("/runs");
  const raw = await response.text();
  const data = raw ? JSON.parse(raw) : [];
  if (!response.ok) {
    return;
  }

  els.recentRuns.innerHTML = data.length > 0
    ? data
        .map(
          (run) => `
            <a class="run-item" href="/reports">
              <span>${run.run_id}</span>
              <strong>${escapeHtml(run.status)}</strong>
              <small>${run.iterations} iterations | ${run.latest_test_count ?? "n/a"} tests</small>
            </a>
          `,
        )
        .join("")
    : '<div class="empty">No completed runs yet.</div>';
}

function restoreStoredMission() {
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
  if (stored.upload_id) {
    state.uploadId = stored.upload_id;
  }
}

async function useSampleRepo() {
  try {
    const repositoryPath = await ensureSamplePath();
    state.uploadId = null;
    els.repositoryPath.value = repositoryPath;
    writeStoredMission({
      repository_path: repositoryPath,
      upload_id: null,
      max_retries: Number(els.maxRetries?.value || 2),
      model: els.modelName?.value || "heuristic",
    });
    setStatus("Sample ready", "completed");
    setUploadFeedback("Sample repository loaded. Continue to the run page when ready.", "success");
    updateMissionSummary();
  } catch (error) {
    setStatus("Sample error", "error");
    setUploadFeedback(error.message || "Sample repository is unavailable.", "error");
  }
}

function continueToRun(event) {
  event.preventDefault();
  const repositoryPath = els.repositoryPath?.value.trim();
  if (!repositoryPath) {
    setStatus("Missing repository", "error");
    setUploadFeedback("Enter a repository path or upload a project before continuing.", "error");
    return;
  }

  writeStoredMission({
    repository_path: repositoryPath,
    upload_id: state.uploadId,
    max_retries: Number(els.maxRetries?.value || 2),
    model: els.modelName?.value || "heuristic",
  });
  window.location.href = "/run";
}

if (els.form) {
  els.form.addEventListener("submit", continueToRun);
}
if (els.repoArchive) {
  els.repoArchive.addEventListener("change", handleArchiveSelection);
}
if (els.sampleButton) {
  els.sampleButton.addEventListener("click", useSampleRepo);
}
if (els.repositoryPath) {
  els.repositoryPath.addEventListener("input", updateMissionSummary);
}
if (els.maxRetries) {
  els.maxRetries.addEventListener("input", updateMissionSummary);
}
if (els.modelName) {
  els.modelName.addEventListener("change", () => {
    writeStoredMission({ model: els.modelName.value });
    updateMissionSummary();
  });
}

setStatus("Idle", "idle");
restoreStoredMission();
updateMissionSummary();
loadSystemStatus();
loadAvailableModels();
loadRecentRuns();
