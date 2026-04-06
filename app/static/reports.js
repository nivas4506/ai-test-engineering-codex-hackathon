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
  const topFinding = latestDebug?.findings?.[0];
  const topFix = latestDebug?.fix_suggestions?.[0];
  const dependencyCount = report.analysis.dependency_map?.length || 0;
  const endpointCount = report.analysis.api_endpoints?.length || 0;
  const coverage = report.coverage_report;

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
      <div class="detail-label">Codebase summary</div>
      <pre>${escapeHtml(
        [
          `Project folder: ${report.repository_path}`,
          `Detected languages: ${report.analysis.detected_languages.join(", ") || "unknown"}`,
          `Modules: ${report.analysis.summary?.total_modules ?? report.analysis.modules.length}`,
          `Functions: ${report.analysis.summary?.total_functions ?? 0}`,
          `Classes: ${report.analysis.summary?.total_classes ?? 0}`,
          `API endpoints: ${endpointCount}`,
          `Dependency links: ${dependencyCount}`,
        ].join("\n"),
      )}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Generated test files</div>
      <pre>${escapeHtml(
        (latestGeneration?.generated_files || [])
          .map((file) => `${file.file_path} -> ${file.strategy}`)
          .join("\n") || "No generated test files recorded.",
      )}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Test execution report</div>
      <pre>${escapeHtml(
        [
          `Planner summary: ${report.plan.summary}`,
          `Execution status: ${latestExecution?.status ?? "n/a"}`,
          `Exit code: ${latestExecution?.exit_code ?? "n/a"}`,
          `Duration: ${latestExecution?.duration_seconds?.toFixed(2) ?? "n/a"}s`,
          `Collected tests: ${latestExecution?.tests_collected ?? "n/a"}`,
        ].join("\n"),
      )}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Bug report</div>
      <pre>${escapeHtml(
        topFinding
          ? [
              `Title: ${topFinding.title}`,
              `Severity: ${topFinding.severity}`,
              `Error: ${topFinding.error_message}`,
              `Root cause: ${topFinding.root_cause}`,
              `Location: ${topFinding.file_path || "n/a"}${topFinding.line_number ? `:${topFinding.line_number}` : ""}`,
            ].join("\n")
          : latestDebug?.diagnosis || "No extra problem was found after the last run.",
      )}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Fix suggestion</div>
      <pre>${escapeHtml(
        topFix
          ? [
              `Title: ${topFix.title}`,
              `Summary: ${topFix.summary}`,
              `Location: ${topFix.file_path || "n/a"}${topFix.line_number ? `:${topFix.line_number}` : ""}`,
              "",
              topFix.patch,
            ].join("\n")
          : "No fix suggestion was needed after the latest run.",
      )}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Coverage report</div>
      <pre>${escapeHtml(
        coverage
          ? [
              `Estimated line coverage: ${coverage.estimated_line_coverage}%`,
              `Covered areas:`,
              ...coverage.covered_areas.map((item) => `- ${item}`),
              `Missing edge cases:`,
              ...coverage.missing_edge_cases.map((item) => `- ${item}`),
              `Suggested additional tests:`,
              ...coverage.suggested_additional_tests.map((item) => `- ${item}`),
            ].join("\n")
          : "Coverage estimate unavailable.",
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
