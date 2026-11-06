import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError, resendEmailVerification } from "../lib/api";
import { isValidEmail, isValidOtpCode, normalizeEmail } from "../lib/authValidation";

const RESEND_COOLDOWN_SECONDS = 60;

export function VerifyEmailPage() {
  const { completeEmailVerification } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const stateEmail =
    typeof location.state === "object" &&
    location.state !== null &&
    "email" in location.state &&
    typeof (location.state as { email?: unknown }).email === "string"
      ? String((location.state as { email?: string }).email ?? "")
      : "";
  const queryEmail = new URLSearchParams(location.search).get("email") ?? "";
  const initialEmail = useMemo(
    () => normalizeEmail(stateEmail || queryEmail),
    [stateEmail, queryEmail],
  );

  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState(
    initialEmail
      ? `Enter the 8-digit code sent to ${initialEmail}. The code expires in 10 minutes.`
      : "Enter your email address and the 8-digit verification code.",
  );
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const normalizedEmail = normalizeEmail(email);
    if (!isValidEmail(normalizedEmail)) {
      setError("Enter the email address used for your account.");
      return;
    }
    const normalizedCode = code.trim();
    if (!isValidOtpCode(normalizedCode)) {
      setError("Enter the 8-digit verification code.");
      return;
    }

    setSubmitting(true);
    try {
      await completeEmailVerification({ email: normalizedEmail, code: normalizedCode });
      navigate("/dashboard", { replace: true, state: { welcome: true } });
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 429) {
        setError("Too many incorrect attempts or requests. Please wait and request a new code if needed.");
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not verify your email. Please try again.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    setError("");
    setMessage("");
    const normalizedEmail = normalizeEmail(email);
    if (!isValidEmail(normalizedEmail)) {
      setError("Enter the email address used for your account.");
      return;
    }
    if (cooldown > 0) return;

    setResending(true);
    try {
      const response = await resendEmailVerification(normalizedEmail);
      setMessage(response.message);
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 429) {
        setCooldown(RESEND_COOLDOWN_SECONDS);
        setError("Please wait before requesting another code.");
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not resend the verification code.",
        );
      }
    } finally {
      setResending(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="verify-email-title">
        <span className="eyebrow">VERIFY YOUR EMAIL</span>
        <h1 id="verify-email-title">Enter your verification code</h1>
        <p>We sent an 8-digit code to verify your Obia account. The code expires in 10 minutes.</p>
        <form className="account-form" onSubmit={handleSubmit} noValidate>
          <label htmlFor="verify-email">Email address</label>
          <input
            autoComplete="email"
            id="verify-email"
            inputMode="email"
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            value={email}
          />

          <label htmlFor="verify-code">8-digit verification code</label>
          <input
            autoComplete="one-time-code"
            id="verify-code"
            inputMode="numeric"
            maxLength={8}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
            pattern="[0-9]{8}"
            placeholder="12345678"
            value={code}
          />
          <span className="account-field-hint">Codes expire in 10 minutes. Do not share your code.</span>

          {error && <p className="account-error" role="alert">{error}</p>}
          {message && <p className="account-success" role="status">{message}</p>}

          <button className="button button--primary button--wide" disabled={submitting} type="submit">
            {submitting ? "Verifying…" : "Verify email"}
          </button>
          <button
            className="button button--outline button--wide"
            disabled={resending || cooldown > 0}
            onClick={handleResend}
            type="button"
          >
            {resending ? "Sending…" : cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
          </button>
        </form>
        <p className="account-switch">Already verified? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
