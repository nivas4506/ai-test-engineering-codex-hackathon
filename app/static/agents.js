const agentCards = document.getElementById("agent-cards");
const plannerLive = document.getElementById("planner-live");
const executionLive = document.getElementById("execution-live");

function agentCard(index, title, body, bullets) {
  return `
    <article class="panel feature-card">
      <div class="section-kicker">${String(index).padStart(2, "0")}</div>
      <h2>${title}</h2>
      <p>${body}</p>
      <ul class="plain-list">
        ${bullets.map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </article>
  `;
}

async function loadAgentPage() {
  const response = await fetch("/runs/latest/report");
  if (!response.ok) {
    agentCards.innerHTML = `<div class="empty">No completed runs yet. Run the overview workflow first.</div>`;
    return;
  }

  const report = await response.json();
  const latestGeneration = report.generation_history.at(-1);
  const latestExecution = report.execution_history.at(-1);
  const latestDebug = report.debug_history.at(-1);
  const moduleCount = report.analysis.modules.length;
  const totalFunctions = report.analysis.modules.reduce((count, module) => count + module.functions.length, 0);

  agentCards.innerHTML = [
    agentCard(1, "Scout the repository", "The tester agent first reads the project and figures out what files, languages, and functions matter.", [
      `${moduleCount} code files checked`,
      `${totalFunctions} main functions found`,
      report.plan.summary,
    ]),
    agentCard(2, "Build the coverage", "The tester agent creates runnable tests based on what it learned from the repository.", [
      `${latestGeneration.generated_files.length} test files created`,
      `Style: ${latestGeneration.mode}`,
      latestGeneration.summary,
    ]),
    agentCard(3, "Execute and judge", "The tester agent runs tests for real and treats that execution result as the source of truth.", [
      `Result: ${latestExecution.status}`,
      `Exit code: ${latestExecution.exit_code}`,
      `${latestExecution.tests_collected ?? "n/a"} tests found`,
    ]),
  ].join("");

  plannerLive.textContent = report.plan.modules
    .slice(0, 4)
    .map((module) => `${module.module_import}: ${module.priority} importance`)
    .join(" | ");

  executionLive.textContent = latestDebug
    ? `${latestExecution.status.toUpperCase()} after ${report.iterations} tries. The tester agent diagnosed the issue like this: ${latestDebug.diagnosis}`
    : `${latestExecution.status.toUpperCase()} after ${report.iterations} tries. No extra debug step was needed.`;
}

loadAgentPage();
