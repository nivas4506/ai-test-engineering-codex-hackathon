const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const authMessage = document.getElementById("auth-message");

function setAuthMessage(message, isError = false) {
  if (!authMessage) return;
  authMessage.textContent = message;
  authMessage.className = `auth-message${isError ? " auth-error" : ""}`;
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = new URLSearchParams({
      username: document.getElementById("login-email").value.trim(),
      password: document.getElementById("login-password").value,
    });

    const response = await fetch("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      setAuthMessage(data.detail || "Login failed.", true);
      return;
    }
    window.location.href = "/";
  });
}

if (signupForm) {
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      full_name: document.getElementById("signup-name").value.trim(),
      email: document.getElementById("signup-email").value.trim(),
      password: document.getElementById("signup-password").value,
    };

    const response = await fetch("/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setAuthMessage(data.detail || "Signup failed.", true);
      return;
    }
    window.location.href = "/";
  });
}
