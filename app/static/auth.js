const authMessage = document.getElementById("auth-message");
const googleSignInButton = document.getElementById("google-signin-button");

function setAuthMessage(message, isError = false) {
  if (!authMessage) return;
  authMessage.textContent = message;
  authMessage.className = `auth-message${isError ? " auth-error" : ""}`;
}

async function signInWithGoogle(credential) {
  const response = await fetch("/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Google sign-in failed.");
  }
  window.location.href = "/";
}

async function bootstrapGoogleSignIn() {
  if (!googleSignInButton) {
    return;
  }

  try {
    const response = await fetch("/auth/google/config");
    const config = await response.json();
    if (!response.ok || !config.enabled || !config.client_id) {
      setAuthMessage("Google sign-in is not configured yet. Add GOOGLE_CLIENT_ID first.", true);
      return;
    }

    if (!window.google?.accounts?.id) {
      setAuthMessage("Google Identity Services did not load.", true);
      return;
    }

    window.google.accounts.id.initialize({
      client_id: config.client_id,
      callback: async ({ credential }) => {
        try {
          setAuthMessage("Signing you in with Google...");
          await signInWithGoogle(credential);
        } catch (error) {
          setAuthMessage(error.message || "Google sign-in failed.", true);
        }
      },
      auto_select: false,
      cancel_on_tap_outside: true,
      use_fedcm_for_prompt: true,
    });

    window.google.accounts.id.renderButton(googleSignInButton, {
      theme: "outline",
      size: "large",
      shape: "pill",
      text: "continue_with",
      width: 320,
    });

    setAuthMessage("Use the Google button above to continue.");
  } catch (error) {
    setAuthMessage(error.message || "Google sign-in setup failed.", true);
  }
}

window.addEventListener("load", () => {
  void bootstrapGoogleSignIn();
});
