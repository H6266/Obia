import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login({ email, password, totp_code: totp });
      const state = location.state as { from?: string } | null;
      navigate(state?.from?.startsWith("/") ? state.from : "/", { replace: true });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <span className="kicker">FALAAA OPERATIONS</span>
        <h1>Staff sign in</h1>
        <p>Use your invited staff account and authenticator app.</p>
        <label htmlFor="staff-email">Work email</label>
        <input id="staff-email" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <label htmlFor="staff-password">Password</label>
        <input id="staff-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
        <label htmlFor="staff-totp">Authenticator code</label>
        <input id="staff-totp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={totp} onChange={(event) => setTotp(event.target.value)} />
        {error && <p className="error" role="alert">{error}</p>}
        <button disabled={loading} type="submit">{loading ? "Verifying…" : "Sign in securely"}</button>
        <small>Staff access is invitation-only. MFA is required for every staff sign in.</small>
        <Link to="/invite">Accept an invitation</Link>
      </form>
    </main>
  );
}
