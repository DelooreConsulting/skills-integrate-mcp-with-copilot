document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("login-toggle");
  const logoutBtn = document.getElementById("logout-btn");
  const userStatus = document.getElementById("user-status");
  const authForm = document.getElementById("auth-form");
  const authSubmit = document.getElementById("auth-submit");
  const authSwitch = document.getElementById("auth-switch");
  const authEmail = document.getElementById("auth-email");
  const authPassword = document.getElementById("auth-password");
  const authName = document.getElementById("auth-name");
  const nameGroup = document.getElementById("name-group");
  const emailInput = document.getElementById("email");

  const STORAGE_KEY = "mergington-auth-token";
  let isRegisterMode = false;
  let currentUser = null;

  function getAuthHeaders() {
    const token = localStorage.getItem(STORAGE_KEY);
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function setUser(user) {
    currentUser = user;
    if (user) {
      userStatus.textContent = `Signed in as ${user.name || user.email}`;
      emailInput.value = user.email;
      emailInput.readOnly = true;
      logoutBtn.classList.remove("hidden");
      loginToggle.classList.add("hidden");
    } else {
      userStatus.textContent = "Not signed in";
      emailInput.value = "";
      emailInput.readOnly = false;
      logoutBtn.classList.add("hidden");
      loginToggle.classList.remove("hidden");
    }
  }

  async function fetchCurrentUser() {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) {
      setUser(null);
      return;
    }

    try {
      const response = await fetch("/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        localStorage.removeItem(STORAGE_KEY);
        setUser(null);
        return;
      }

      const user = await response.json();
      setUser(user);
    } catch (error) {
      console.error("Error fetching current user:", error);
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
    }
  }

  function showAuthForm() {
    authForm.classList.remove("hidden");
  }

  function hideAuthForm() {
    authForm.classList.add("hidden");
    authForm.reset();
  }

  loginToggle.addEventListener("click", () => {
    isRegisterMode = false;
    authSubmit.textContent = "Login";
    authSwitch.textContent = "Register instead";
    nameGroup.classList.add("hidden");
    showAuthForm();
  });

  authSwitch.addEventListener("click", () => {
    isRegisterMode = !isRegisterMode;
    authSubmit.textContent = isRegisterMode ? "Register" : "Login";
    authSwitch.textContent = isRegisterMode ? "Login instead" : "Register instead";
    nameGroup.classList.toggle("hidden", !isRegisterMode);
  });

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      email: authEmail.value,
      password: authPassword.value,
    };

    if (isRegisterMode) {
      payload.name = authName.value || authEmail.value;
      payload.role = "student";
    }

    try {
      const response = await fetch(
        isRegisterMode ? "/auth/register" : "/auth/login",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Authentication failed");
      }

      localStorage.setItem(STORAGE_KEY, result.token);
      hideAuthForm();
      await fetchCurrentUser();
      messageDiv.textContent = isRegisterMode
        ? "Account created successfully."
        : "Logged in successfully.";
      messageDiv.className = "success";
      messageDiv.classList.remove("hidden");
    } catch (error) {
      messageDiv.textContent = error.message;
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
    }
  });

  logoutBtn.addEventListener("click", async () => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) {
      return;
    }

    try {
      await fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) {
      console.error("Logout failed:", error);
    }

    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
    messageDiv.textContent = "Logged out.";
    messageDiv.className = "info";
    messageDiv.classList.remove("hidden");
  });

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        currentUser && (currentUser.role === "activity_admin" || currentUser.role === "system_admin" || currentUser.email === email)
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        await fetchCurrentUser();
        await fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = emailInput.value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup${currentUser ? "" : `?email=${encodeURIComponent(email)}`}`,
        {
          method: "POST",
          headers: {
            ...getAuthHeaders(),
            "Content-Type": "application/json",
          },
          body: currentUser ? JSON.stringify({}) : undefined,
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();
        await fetchCurrentUser();
        await fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  fetchCurrentUser();
  fetchActivities();
});
