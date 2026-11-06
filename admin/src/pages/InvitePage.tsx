import { useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../services/api";

export function InvitePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [enrollment, setEnrollment] = useState<{
    enrollment_token: string;
    totp_secret: string;
    issuer: string;
    account_name: string;
  } | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const uri = useMemo(() => {
    if (!enrollment) return "";
    const label = encodeURIComponent(`${enrollment.issuer}:${enrollment.account_name}`);
    return `otpauth://totp/${label}?secret=${enrollment.totp_secret}&issuer=${encodeURIComponent(enrollment.issuer)}&algorithm=SHA1&digits=6&period=30`;
  }, [enrollment]);

  async function accept(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setEnrollment(await api.acceptInvitation(token, password));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not accept this invitation.");
    } finally {
      setLoading(false);
    }
  }

  async function enableMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enrollment) return;
    setLoading(true);
    setError("");
    try {
      await api.confirmMfa(enrollment.enrollment_token, code);
      navigate("/login", { replace: true, state: { message: "MFA enabled. Sign in with your password and authenticator code." } });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not verify the authenticator code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <span className="kicker">STAFF ONBOARDING</span>
        {!token ? (
          <>
            <h1>Invitation link required</h1>
            <p>Staff accounts can only be created from a valid, owner-issued invitation.</p>
            <Link to="/login">Return to sign in</Link>
          </>
        ) : !enrollment ? (
          <form onSubmit={accept}>
            <h1>Accept staff invitation</h1>
            <p>Choose a strong password. You will need to enroll an authenticator before the account is activated.</p>
            <label htmlFor="invite-password">Password</label>
            <input id="invite-password" type="password" autoComplete="new-password" minLength={14} required value={password} onChange={(event) => setPassword(event.target.value)} />
            <label htmlFor="invite-confirm">Confirm password</label>
            <input id="invite-confirm" type="password" autoComplete="new-password" minLength={14} required value={confirm} onChange={(event) => setConfirm(event.target.value)} />
            {error && <p className="error" role="alert">{error}</p>}
            <button disabled={loading} type="submit">{loading ? "Accepting…" : "Continue to MFA setup"}</button>
          </form>
        ) : (
          <form onSubmit={enableMfa}>
            <h1>Enable authenticator MFA</h1>
            <p>Add this account to an authenticator app. This setup secret is shown once; store it only in the authenticator.</p>
            <label htmlFor="totp-secret">Setup secret</label>
            <input id="totp-secret" readOnly value={enrollment.totp_secret} />
            <label htmlFor="totp-uri">Authenticator setup URI</label>
            <textarea id="totp-uri" readOnly rows={3} value={uri} />
            <label htmlFor="enroll-code">Current 6-digit code</label>
            <input id="enroll-code" inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={code} onChange={(event) => setCode(event.target.value)} />
            {error && <p className="error" role="alert">{error}</p>}
            <button disabled={loading} type="submit">{loading ? "Verifying…" : "Verify and activate account"}</button>
          </form>
        )}
      </section>
    </main>
  );
}
