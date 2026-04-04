const summaryCards = document.getElementById("report-summary-cards");
const runList = document.getElementById("reports-run-list");
const reportDetail = document.getElementById("selected-report-detail");

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function statusTone(status) {
  return status === "passed" ? "tone-good" : "tone-alert";
}

function renderReportDetail(report) {
  const latestExecution = report.execution_history.at(-1);
  const latestGeneration = report.generation_history.at(-1);
  const latestDebug = report.debug_history.at(-1);

  reportDetail.innerHTML = `
    <div class="detail-hero">
      <div>
        <div class="section-kicker">Selected run</div>
        <h3>${report.run_id}</h3>
      </div>
      <div class="status-pill ${report.status}">${report.status.toUpperCase()}</div>
    </div>
    <div class="detail-metrics">
      <div class="detail-stat">
        <span>How many tries</span>
        <strong>${report.iterations}</strong>
      </div>
      <div class="detail-stat">
        <span>Tests found</span>
        <strong>${latestExecution?.tests_collected ?? "n/a"}</strong>
      </div>
      <div class="detail-stat">
        <span>Test style</span>
        <strong>${latestGeneration?.mode ?? "n/a"}</strong>
      </div>
      <div class="detail-stat">
        <span>AI model</span>
        <strong>${latestGeneration?.provider === "openai" ? latestGeneration?.model ?? "gpt-5-mini" : "Heuristic fallback"}</strong>
      </div>
    </div>
    <div class="detail-section">
      <div class="detail-label">Project folder</div>
      <pre>${escapeHtml(report.repository_path)}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">What the app understood</div>
      <pre>${escapeHtml(report.plan.summary)}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Problem found</div>
      <pre>${escapeHtml(latestDebug?.diagnosis || "No extra problem was found after the last run.")}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Run facts</div>
      <pre>${escapeHtml(
        [
          `Exit code: ${latestExecution?.exit_code ?? "n/a"}`,
          `Time taken: ${latestExecution?.duration_seconds?.toFixed(2) ?? "n/a"}s`,
          `Output lines: ${latestExecution?.stdout?.split("\\n").filter(Boolean).length ?? 0}`,
          `Error lines: ${latestExecution?.stderr?.split("\\n").filter(Boolean).length ?? 0}`,
          `AI provider: ${latestGeneration?.provider ?? "n/a"}`,
          `AI model: ${latestGeneration?.model ?? "heuristic fallback"}`,
        ].join("\n"),
      )}</pre>
    </div>
  `;
}

async function loadReportsPage() {
  const response = await fetch("/runs");
  if (!response.ok) {
    summaryCards.innerHTML = `<div class="empty">Failed to load run registry.</div>`;
    return;
  }

  const runs = await response.json();
  if (runs.length === 0) {
    summaryCards.innerHTML = `<div class="empty">No runs available yet.</div>`;
    runList.innerHTML = `<div class="empty">Run the overview workflow to populate this page.</div>`;
    return;
  }

  const passCount = runs.filter((run) => run.status === "passed").length;
  const failCount = runs.filter((run) => run.status !== "passed").length;
  const avgIterations = (runs.reduce((sum, run) => sum + run.iterations, 0) / runs.length).toFixed(1);
  const latestRun = runs[0];

  summaryCards.innerHTML = `
    <article class="panel dashboard-card">
      <div class="dashboard-icon">1</div>
      <div class="section-kicker">Total runs</div>
      <h2>${runs.length} saved runs</h2>
      <p>This tells you how many past results are available to review.</p>
    </article>
    <article class="panel dashboard-card ${failCount === 0 ? "tone-good" : "tone-alert"}">
      <div class="dashboard-icon">2</div>
      <div class="section-kicker">Success vs issue</div>
      <h2>${passCount} worked / ${failCount} need attention</h2>
      <p>Green means the run worked. Red means the run still needs a closer look.</p>
    </article>
    <article class="panel dashboard-card">
      <div class="dashboard-icon">3</div>
      <div class="section-kicker">Average retries</div>
      <h2>${avgIterations} tries per run</h2>
      <p>Lower numbers usually mean the app is behaving more smoothly.</p>
    </article>
    <article class="panel dashboard-card ${statusTone(latestRun.status)}">
      <div class="dashboard-icon">4</div>
      <div class="section-kicker">Latest result</div>
      <h2>${latestRun.run_id}</h2>
      <p>${latestRun.status.toUpperCase()} | ${latestRun.latest_test_count ?? "n/a"} tests | ${latestRun.iterations} tries</p>
    </article>
  `;

  runList.innerHTML = runs
    .map(
      (run) => `
        <button class="run-item ${statusTone(run.status)}" type="button" data-run-id="${run.run_id}">
          <span>${run.run_id}</span>
          <strong>${run.status}</strong>
          <small>${run.iterations} tries | ${run.latest_test_count ?? "n/a"} tests</small>
        </button>
      `,
    )
    .join("");

  runList.querySelectorAll("[data-run-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const reportResponse = await fetch(`/runs/${button.getAttribute("data-run-id")}/report`);
      if (!reportResponse.ok) {
        return;
      }
      const report = await reportResponse.json();
      renderReportDetail(report);
    });
  });

  const latestReport = await fetch(`/runs/${latestRun.run_id}/report`);
  if (latestReport.ok) {
    renderReportDetail(await latestReport.json());
  }
}

loadReportsPage();
