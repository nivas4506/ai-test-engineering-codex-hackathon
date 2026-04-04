const identityEl = document.getElementById("profile-identity");
const statsEl = document.getElementById("profile-stats");
const latestRunEl = document.getElementById("profile-latest-run");
const guidanceEl = document.getElementById("profile-guidance");

function formatDate(value) {
  if (!value) {
    return "Not available yet";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not available yet";
  }
  return date.toLocaleString();
}

function profileGuidance(profile) {
  if (profile.stats.total_runs === 0) {
    return "You have an account but no saved runs yet. Start on the Overview page and complete one run to begin building your history.";
  }

  if (profile.stats.runs_needing_attention === 0) {
    return "Your recent runs are in a healthy state. This is a good moment to share results or try the product on another repository.";
  }

  return "Some runs still need attention. Open the Results page to inspect the latest failing run and review the debugger notes.";
}

async function loadProfilePage() {
  const response = await fetch("/profile/summary");
  const data = await response.json();

  if (!response.ok) {
    identityEl.textContent = data.detail || "Failed to load profile details.";
    statsEl.innerHTML = `<div class="empty">Profile stats are not available right now.</div>`;
    latestRunEl.textContent = "Latest run information is not available.";
    guidanceEl.textContent = "Try refreshing the page.";
    return;
  }

  identityEl.innerHTML = `
    <div class="detail-section">
      <div class="detail-label">Full name</div>
      <pre>${data.full_name}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Email</div>
      <pre>${data.email}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Member since</div>
      <pre>${formatDate(data.member_since)}</pre>
    </div>
    <div class="detail-section">
      <div class="detail-label">Last login</div>
      <pre>${formatDate(data.last_login_at)}</pre>
    </div>
  `;

  statsEl.innerHTML = `
    <article class="panel dashboard-card">
      <div class="dashboard-icon">1</div>
      <div class="section-kicker">Total runs</div>
      <h2>${data.stats.total_runs}</h2>
      <p>All saved runs connected to your account.</p>
    </article>
    <article class="panel dashboard-card tone-good">
      <div class="dashboard-icon">2</div>
      <div class="section-kicker">Passed runs</div>
      <h2>${data.stats.passed_runs}</h2>
      <p>Runs that finished successfully.</p>
    </article>
    <article class="panel dashboard-card ${data.stats.runs_needing_attention > 0 ? "tone-alert" : ""}">
      <div class="dashboard-icon">3</div>
      <div class="section-kicker">Need attention</div>
      <h2>${data.stats.runs_needing_attention}</h2>
      <p>Runs that still need review or another attempt.</p>
    </article>
    <article class="panel dashboard-card">
      <div class="dashboard-icon">4</div>
      <div class="section-kicker">Latest run</div>
      <h2>${data.stats.latest_run_id || "None yet"}</h2>
      <p>${data.stats.latest_run_status ? `${data.stats.latest_run_status.toUpperCase()} status` : "No runs have been saved yet."}</p>
    </article>
  `;

  latestRunEl.textContent = data.stats.latest_run_id
    ? `Your most recent run is ${data.stats.latest_run_id} and its current status is ${data.stats.latest_run_status}.`
    : "You do not have a saved run yet. Start with the Overview page to create your first one.";

  guidanceEl.textContent = profileGuidance(data);
}

loadProfilePage();
