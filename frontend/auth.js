"use strict";
/* Firebase Auth — link-based email verification (Option A).
   4 screens: Sign in · Create account · Check email · Success

   Signup → Firebase sends a verification LINK to the email
   → user clicks it → comes back → "I've clicked the link" → enters the app. */

(function () {
  if (!window.firebase || !window.FIREBASE_CONFIG) {
    console.error("Firebase SDK or config missing. Auth disabled.");
    window.MedAuth = { enabled: false, open: () => {}, getIdToken: async () => null, onChange: () => {}, signOut: async () => {} };
    return;
  }

  try { firebase.app(); }
  catch { firebase.initializeApp(window.FIREBASE_CONFIG); }
  const auth = firebase.auth();

  // Sends the user back to this page after the verification link opens.
  const verifySettings = () => ({ url: location.origin + location.pathname });

  const $ = (s) => document.querySelector(s);

  const modal = $("#authModal");
  const screens = {
    signIn:  $("#screenSignIn"),
    signUp:  $("#screenSignUp"),
    verify:  $("#screenVerify"),
    success: $("#screenSuccess"),
  };

  if (!modal || !screens.signIn) {
    console.error("Auth modal markup missing from index.html. Auth disabled.");
    window.MedAuth = { enabled: false, open: () => {}, getIdToken: async () => null, onChange: () => {}, signOut: async () => {} };
    return;
  }

  const verifyEmailEl = $("#verifyEmail");
  const verifyMsgEl   = $("#verifyMsg");
  const navBtn        = $("#navAuthBtn");
  const navLabel      = $("#navAuthLabel");

  function showScreen(name) {
    Object.entries(screens).forEach(([k, el]) => { if (el) el.hidden = k !== name; });
  }

  function setMsg(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.style.color = kind === "error" ? "var(--red)" : kind === "ok" ? "var(--green)" : "";
  }

  // Turns Firebase error codes into a sentence the user can act on.
  function authMessage(err) {
    const map = {
      "auth/invalid-credential": "Email or password is incorrect for this project. Check both, or press “Forgot password?” to reset it.",
      "auth/invalid-login-credentials": "Email or password is incorrect for this project. Check both, or press “Forgot password?” to reset it.",
      "auth/wrong-password": "Wrong password. Press “Forgot password?” to reset it.",
      "auth/user-not-found": "No account uses this email in this project. Create an account instead.",
      "auth/email-already-in-use": "This email already has an account. Sign in below, or press “Forgot password?”.",
      "auth/user-disabled": "This account has been disabled in the Firebase console.",
      "auth/too-many-requests": "Too many attempts. Wait a minute, then try again.",
      "auth/network-request-failed": "Network problem. Check your connection and try again.",
      "auth/operation-not-allowed": "Email/password sign-in is disabled in the Firebase console (Authentication → Sign-in method).",
      "auth/invalid-api-key": "The Firebase API key is invalid or restricted for this domain.",
      "auth/unauthorized-continue-uri": "Add this origin to Authentication → Settings → Authorized domains in Firebase.",
      "auth/weak-password": "Use a password of at least 6 characters.",
      "auth/invalid-email": "That email address is not valid.",
      "auth/missing-email": "Enter your email first.",
      "auth/internal-error": "Firebase returned an internal error. Try again.",
    };
    return map[(err && err.code) || ""] || (err && err.message) || "Something went wrong. Try again.";
  }

  function openAuth() {
    if (!modal.open) modal.showModal();
    if (!auth.currentUser) showScreen("signIn");
  }
  function closeAuth() { if (modal.open) modal.close(); }

  function setSidebar(user) {
    const nameEl = $("#profileName");
    const subEl  = $("#profileSub");
    if (!nameEl || !subEl) return;
    if (user) {
      const display = (user.displayName && user.displayName.trim())
        || (user.email ? user.email.split("@")[0] : "")
        || "Doctor";
      nameEl.textContent = display;
      subEl.textContent = user.email ? user.email + (user.emailVerified ? "" : " · not verified") : "(no email)";
      if (navLabel) navLabel.textContent = user.emailVerified ? "Sign out" : "Verify email";
      if (navBtn) {
        navBtn.classList.add("signed-in");
        const use = navBtn.querySelector("use");
        if (use) use.setAttribute("href", user.emailVerified ? "#i-logout" : "#i-mail");
      }
    } else {
      nameEl.textContent = "Guest";
      subEl.textContent  = "Not signed in";
      if (navLabel) navLabel.textContent = "Sign in";
      if (navBtn) {
        navBtn.classList.remove("signed-in");
        const use = navBtn.querySelector("use");
        if (use) use.setAttribute("href", "#i-user");
      }
    }
  }

  /* Screen 1: Sign in */
  const signInForm = $("#signInForm");
  if (signInForm) {
    signInForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email    = $("#signInEmail").value.trim();
      const password = $("#signInPassword").value;
      const msg      = $("#signInMsg");
      const btn      = $("#signInBtn");
      if (!email || password.length < 6) {
        setMsg(msg, "Enter a valid email and a password of at least 6 characters.", "error");
        return;
      }
      btn.disabled = true;
      setMsg(msg, "Signing in…");
      try {
        const cred = await auth.signInWithEmailAndPassword(email, password);
        if (!cred.user.emailVerified) {
          if (verifyEmailEl) verifyEmailEl.textContent = email;
          setMsg(verifyMsgEl, "Please verify your email first. Check your inbox for the link.", "error");
          showScreen("verify");
          verifyAccount(true);
        } else {
          closeAuth();
        }
      } catch (err) {
        const wrongLogin = /invalid-credential|invalid-login-credentials|wrong-password/.test((err && err.code) || "");
        setMsg(msg, wrongLogin ? "Email or password is incorrect for " + email + " in this project. Check both, or press “Forgot password?”." : authMessage(err), "error");
      } finally {
        btn.disabled = false;
      }
    });
  }

  /* Screen 2: Create account */
  const signUpForm = $("#signUpForm");
  if (signUpForm) {
    signUpForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email       = $("#signUpEmail").value.trim();
      const password    = $("#signUpPassword").value;
      const confirm     = $("#signUpConfirm").value;
      const displayName = ($("#signUpName").value || "").trim();
      const msg         = $("#signUpMsg");
      const btn         = $("#signUpBtn");

      if (!email)              return setMsg(msg, "Enter your email.", "error");
      if (password.length < 6) return setMsg(msg, "Password must be at least 6 characters.", "error");
      if (password !== confirm) return setMsg(msg, "Passwords do not match.", "error");

      btn.disabled = true;
      setMsg(msg, "Creating account…");
      try {
        const cred = await auth.createUserWithEmailAndPassword(email, password);
        if (displayName) await cred.user.updateProfile({ displayName });
        await cred.user.sendEmailVerification(verifySettings());
        if (verifyEmailEl) verifyEmailEl.textContent = email;
        closeAuth();
        window.dispatchEvent(new CustomEvent("medev:auth", { detail: { user: cred.user } }));
      } catch (err) {
        if (err && err.code === "auth/email-already-in-use") {
          $("#signInEmail").value = email;
          showScreen("signIn");
          setMsg($("#signInMsg"), authMessage(err), "error");
        } else {
          setMsg(msg, authMessage(err), "error");
        }
      } finally {
        btn.disabled = false;
      }
    });
  }

  /* Screen 3: Verify (link-based) */
  let checking = false;

  // Reloads the account, refreshes the token and reports whether the email is now verified.
  async function verifyAccount(silent) {
    const user = auth.currentUser;
    if (!user) { showScreen("signIn"); return false; }
    if (checking) return false;
    checking = true;
    const btn = $("#verifyBtn");
    if (btn) btn.disabled = true;
    if (!silent) setMsg(verifyMsgEl, "Checking verification status…");
    try {
      await user.reload();
      let claims = null;
      try { claims = (await user.getIdTokenResult(true)).claims; } catch { /* token refresh failed; the user record still counts */ }
      if (user.emailVerified || (claims && claims.email_verified)) {
        setMsg(verifyMsgEl, "Verified! Opening MedEvidence…", "ok");
        showScreen("success");
        window.dispatchEvent(new CustomEvent("medev:auth", { detail: { user: auth.currentUser } }));
        setTimeout(closeAuth, 700);
        return true;
      }
      const account = user.email || "this account";
      setMsg(verifyMsgEl, silent
        ? "Waiting for the newest link sent to " + account + "."
        : "Not verified yet for " + account + ". Click the newest link sent to that inbox, then press again.", "error");
      return false;
    } catch (err) {
      setMsg(verifyMsgEl, authMessage(err), "error");
      return false;
    } finally {
      checking = false;
      if (btn) btn.disabled = false;
    }
  }

  const verifyForm = $("#verifyForm");
  if (verifyForm) verifyForm.addEventListener("submit", (e) => { e.preventDefault(); verifyAccount(false); });

  // Re-checks by itself whenever the user returns from the inbox with the verify screen open.
  const onVerifyScreen = () => Boolean(screens.verify && !screens.verify.hidden);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && onVerifyScreen()) verifyAccount(true); });
  window.addEventListener("focus", () => { if (onVerifyScreen()) verifyAccount(true); });
  let verifyChecks = 0;
  setInterval(() => { if (modal.open && onVerifyScreen() && verifyChecks++ < 60) verifyAccount(true); }, 5000);

  /* Resend */
  const resendBtn = $("#resendCode");
  if (resendBtn) {
    resendBtn.addEventListener("click", async () => {
      const user = auth.currentUser;
      if (!user) return;
      try {
        await user.sendEmailVerification(verifySettings());
        setMsg(verifyMsgEl, "Verification email resent. Check your inbox.", "ok");
      } catch (err) {
        setMsg(verifyMsgEl, authMessage(err), "error");
      }
    });
  }

  /* Forgot password */
  const forgotBtn = $("#forgotPassword");
  if (forgotBtn) {
    forgotBtn.addEventListener("click", async () => {
      const email = ($("#signInEmail").value || "").trim();
      const msg = $("#signInMsg");
      if (!email) return setMsg(msg, "Enter your email above, then press Forgot password.", "error");
      forgotBtn.disabled = true;
      try {
        await auth.sendPasswordResetEmail(email);
        setMsg(msg, "If an account exists for " + email + ", a reset link is on its way. Check the inbox and spam folder, then sign in with the new password.", "ok");
      } catch (err) {
        setMsg(msg, authMessage(err), "error");
      } finally {
        forgotBtn.disabled = false;
      }
    });
  }

  const backBtn = $("#backFromVerify");
  if (backBtn) {
    backBtn.addEventListener("click", async () => {
      await auth.signOut().catch(() => {});
      showScreen("signIn");
      setMsg(verifyMsgEl, "");
    });
  }

  /* Navigation */
  const toSignUp = $("#toSignUp");
  if (toSignUp) toSignUp.addEventListener("click", () => showScreen("signUp"));
  const toSignIn = $("#toSignIn");
  if (toSignIn) toSignIn.addEventListener("click", () => showScreen("signIn"));
  const authClose = $("#authClose");
  if (authClose) authClose.addEventListener("click", closeAuth);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeAuth(); });

  /* Nav button */
  if (navBtn) {
    navBtn.addEventListener("click", async () => {
      const user = auth.currentUser;
      if (!user) { openAuth(); return; }
      if (!user.emailVerified) {
        openAuth();
        showScreen("verify");
        setMsg(verifyMsgEl, "Still open the newest link sent to " + (user.email || "your email") + ". This screen checks again automatically.", "");
        verifyAccount(true);
        return;
      }
      if (confirm("Sign out?")) await auth.signOut();
    });
  }

  /* Auth state */
  auth.onAuthStateChanged((user) => {
    setSidebar(user);
    if (user && user.email) { try { localStorage.setItem("me_last_email", user.email); } catch { /* storage blocked */ } }
    if (user && user.emailVerified) {
      if (modal.open) closeAuth();
      user.getIdToken(true).catch(() => {});
    }
    window.dispatchEvent(new CustomEvent("medev:auth", { detail: { user } }));
  });

  setSidebar(auth.currentUser);
  try { const last = localStorage.getItem("me_last_email"); if (last && !$("#signInEmail").value) $("#signInEmail").value = last; } catch { /* storage blocked */ }

  /* Public API */
  window.MedAuth = {
    enabled: true,
    open: openAuth,
    signOut: () => auth.signOut(),
    isSignedIn() { return Boolean(auth.currentUser); },
    async getIdToken() {
      const user = auth.currentUser;
      return user ? user.getIdToken().catch(() => null) : null;
    },
    onChange(cb) { auth.onAuthStateChanged(cb); },
  };
})();