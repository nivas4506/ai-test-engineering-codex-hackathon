const recommendation = document.getElementById("playbook-recommendation");

async function loadPlaybookRecommendation() {
  const response = await fetch("/runs/latest/report");
  if (!response.ok) {
    recommendation.textContent = "No recent runs yet. Start on the Overview page and generate a first report.";
    return;
  }

  const report = await response.json();
  const latestExecution = report.execution_history.at(-1);
  if (report.status === "passed") {
    recommendation.textContent =
      "Best next move: show the result. Your latest run passed, so this is a good time to open the Results page and present the output.";
    return;
  }
  if (latestExecution?.status === "error") {
    recommendation.textContent =
      "Best next move: focus on the error. The last run hit a pipeline problem, so fix the setup or import issue before asking the app to do more.";
    return;
  }
  recommendation.textContent =
    "Best next move: start with a quick scan. Read the summary first, then decide if you want a broader or safer test run.";
}

loadPlaybookRecommendation();
