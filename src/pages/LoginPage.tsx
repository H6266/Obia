import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError, type LoginChallenge } from "../lib/api";
import { isValidEmail, isValidOtpCode, normalizeEmail } from "../lib/authValidation";

export function LoginPage() {
  const { login, completeLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (challenge) {
        const normalizedCode = code.trim();
        if (!isValidOtpCode(normalizedCode)) {
          setError("Enter the 8-digit code sent to your email.");
          return;
        }
        await completeLogin({
          challenge_token: challenge.challenge_token,
          channel: "email",
          code: normalizedCode,
        });
        const destination = (location.state as { from?: string } | null)?.from ?? "/dashboard";
        navigate(destination.startsWith("/") ? destination : "/dashboard", { replace: true });
      } else {
        const normalizedEmail = normalizeEmail(email);
        if (!isValidEmail(normalizedEmail)) {
          setError("Enter a valid email address.");
          return;
        }
        const pending = await login({ email: normalizedEmail, password });
        setChallenge(pending);
        setPassword("");
      }
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 401) {
          setError("Email or password is incorrect.");
        } else if (requestError.status === 403 && requestError.message.toLowerCase().includes("verify")) {
          setError("Verify your email address before signing in.");
        } else if (requestError.status === 403) {
          setError("This account is not available.");
        } else {
          setError(requestError.message);
        }
      } else {
        setError(requestError instanceof Error ? requestError.message : "Could not sign in. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="login-title">
        <span className="eyebrow">WELCOME BACK</span>
        <h1 id="login-title">Sign in to Obia</h1>
        <p>Use your verified email address and confirm sign-in with a one-time email code.</p>
        <form className="account-form" onSubmit={handleSubmit} noValidate>
          {!challenge ? (
            <>
              <label htmlFor="login-email">Email address</label>
              <input
                autoComplete="username"
                id="login-email"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
                type="email"
                value={email}
              />
              <label htmlFor="login-password">Password</label>
              <div className="password-control">
            <input
              autoComplete="current-password"
              id="login-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type={showPassword ? "text" : "password"}
              value={password}
            />
            <button onClick={() => setShowPassword((shown) => !shown)} type="button">
              {showPassword ? "Hide" : "Show"}
            </button>
              </div>
            </>
          ) : (
            <>
              <p role="status">
                Enter the 8-digit sign-in code sent to {challenge.email ?? "your email address"}.
              </p>
              <label htmlFor="login-code">8-digit sign-in code</label>
              <input
                autoComplete="one-time-code"
                id="login-code"
                inputMode="numeric"
                maxLength={8}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
                pattern="[0-9]{8}"
                required
                value={code}
              />
              <button
                className="button button--outline button--wide"
                onClick={() => {
                  setChallenge(null);
                  setCode("");
                  setError("");
                }}
                type="button"
              >
                Use a different account
              </button>
            </>
          )}
          <div className="account-form__trailing"><Link to="/forgot-password">Forgot password?</Link></div>
          {error && <p className="account-error" role="alert">{error}</p>}
          <button className="button button--primary button--wide" disabled={submitting} type="submit">
            {submitting ? (challenge ? "Verifying…" : "Checking…") : challenge ? "Verify and sign in" : "Continue"}
          </button>
        </form>
        <p className="account-switch">New to Obia? <Link to="/signup">Create an account</Link></p>
      </section>
    </main>
  );
}
