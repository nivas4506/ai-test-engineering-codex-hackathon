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
  const memoryCount = report.memory_context?.length || 0;
  const traceByAgent = Object.fromEntries((report.agent_trace || []).map((entry) => [entry.agent, entry]));

  agentCards.innerHTML = [
    agentCard(1, "Memory Manager", "The memory agent recalls past failures, flaky behavior, and prior run context before planning starts.", [
      `${memoryCount} memory items pulled into this run`,
      traceByAgent.memory?.summary || "No prior memory context was available.",
      ...(traceByAgent.memory?.details || []).slice(0, 1),
    ]),
    agentCard(2, "Planner Agent", "The planner turns repository analysis into a prioritized test strategy and structured execution steps.", [
      `${moduleCount} modules analyzed`,
      `${totalFunctions} top-level functions found`,
      traceByAgent.planner?.summary || report.plan.summary,
    ]),
    agentCard(3, "Executor Agent", "The executor creates runnable coverage and uses the toolbox to run the generated tests for real.", [
      `${latestGeneration.generated_files.length} test files created`,
      `Mode: ${latestGeneration.mode}`,
      traceByAgent.executor?.summary || latestGeneration.summary,
    ]),
    agentCard(4, "Critic Agent", "The critic inspects the execution result, decides whether to retry, and explains likely root causes.", [
      `Result: ${latestExecution.status}`,
      `Exit code: ${latestExecution.exit_code}`,
      traceByAgent.critic?.summary || (latestDebug ? latestDebug.diagnosis : "No critic intervention was needed."),
    ]),
  ].join("");

  plannerLive.textContent = report.test_plan
    .slice(0, 4)
    .map((item) => `${item.category}: ${item.target}`)
    .join(" | ");

  executionLive.textContent = latestDebug
    ? `${latestExecution.status.toUpperCase()} after ${report.iterations} tries. The critic diagnosed the issue like this: ${latestDebug.diagnosis}`
    : `${latestExecution.status.toUpperCase()} after ${report.iterations} tries. The multi-agent loop completed without extra critic intervention.`;
}

loadAgentPage();
