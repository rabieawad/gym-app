(() => {
  const form = document.getElementById("auth-form");
  const title = document.getElementById("title");
  const errorBox = document.getElementById("error");
  const nameField = document.getElementById("name-field");
  const nameInput = document.getElementById("display_name");
  const emailInput = document.getElementById("email");
  const passInput = document.getElementById("password");
  const hint = document.getElementById("password-hint");
  const submit = document.getElementById("submit");
  const tabLogin = document.getElementById("tab-login");
  const tabRegister = document.getElementById("tab-register");

  let mode = "login";

  function setMode(next) {
    mode = next;
    const reg = mode === "register";
    tabLogin.setAttribute("aria-selected", String(!reg));
    tabRegister.setAttribute("aria-selected", String(reg));
    title.textContent = reg ? "Create your account" : "Log in";
    submit.textContent = reg ? "Create account" : "Log in";
    nameField.hidden = !reg;
    hint.hidden = !reg;
    passInput.autocomplete = reg ? "new-password" : "current-password";
    errorBox.textContent = "";
  }

  tabLogin.addEventListener("click", () => setMode("login"));
  tabRegister.addEventListener("click", () => setMode("register"));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.textContent = "";

    const email = emailInput.value.trim();
    const password = passInput.value;
    if (!email || !password) {
      errorBox.textContent = "Enter your email and password.";
      return;
    }
    const reg = mode === "register";
    if (reg && !nameInput.value.trim()) {
      errorBox.textContent = "Enter your name.";
      return;
    }

    submit.disabled = true;
    try {
      const data = reg
        ? await Api.post("/auth/register", { email, password, display_name: nameInput.value }, { auth: false })
        : await Api.post("/auth/login", { email, password }, { auth: false });
      Api.setToken(data.access_token);
      window.location.href = "dashboard.html";
    } catch (err) {
      errorBox.textContent = err.message;
      submit.disabled = false;
    }
  });

  // Already logged in? Skip straight to the log.
  if (Api.getToken()) {
    Api.get("/auth/me").then(() => { window.location.href = "dashboard.html"; }).catch(() => {});
  }

  setMode(new URLSearchParams(window.location.search).get("mode") === "register" ? "register" : "login");
})();
