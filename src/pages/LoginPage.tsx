import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ phone, password });
      const destination = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(destination.startsWith("/") ? destination : "/dashboard", { replace: true });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 401
          ? "Phone number or password is incorrect."
          : requestError instanceof Error
            ? requestError.message
            : "Could not sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="login-title">
        <span className="eyebrow">WELCOME BACK</span>
        <h1 id="login-title">Sign in to Falaaa</h1>
        <p>Access your account and recent purchase requests.</p>
        <form className="account-form" onSubmit={handleSubmit}>
          <label htmlFor="login-phone">Ghanaian phone number</label>
          <input
            autoComplete="username"
            id="login-phone"
            inputMode="tel"
            onChange={(event) => setPhone(event.target.value)}
            placeholder="024 123 4567"
            required
            value={phone}
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
          <div className="account-form__trailing"><Link to="/forgot-password">Forgot password?</Link></div>
          {error && <p className="account-error" role="alert">{error}</p>}
          <button className="button button--primary button--wide" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="account-switch">New to Falaaa? <Link to="/signup">Create an account</Link></p>
        <div className="account-provider-note">
          Forgot-password recovery is unavailable until a verified messaging provider is configured. No recovery message has been sent.
        </div>
      </section>
    </main>
  );
}
