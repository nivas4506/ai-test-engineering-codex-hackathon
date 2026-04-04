const sessionUser = document.getElementById("session-user");
const logoutButton = document.getElementById("logout-button");

async function bootstrapSession() {
  if (!sessionUser) return;
  const response = await fetch("/auth/me");
  if (!response.ok) {
    window.location.href = "/login";
    return;
  }
  const user = await response.json();
  sessionUser.textContent = user.full_name;
}

if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

bootstrapSession();
