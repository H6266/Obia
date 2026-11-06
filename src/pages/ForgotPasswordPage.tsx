import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, requestPasswordRecovery, resetPassword } from "../lib/api";
import { isValidEmail, isValidOtpCode, normalizeEmail, validatePassword } from "../lib/authValidation";

export function ForgotPasswordPage() {
  const [step, setStep] = useState<"request" | "reset" | "done">("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");
    const normalizedEmail = normalizeEmail(email);
    if (!isValidEmail(normalizedEmail)) {
      setError("Enter a valid email address.");
      setSubmitting(false);
      return;
    }
    try {
      const response = await requestPasswordRecovery(normalizedEmail);
      setEmail(normalizedEmail);
      setMessage(response.message);
      setStep("reset");
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 429) {
        setError("Please wait before requesting another recovery code.");
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not request password recovery.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");
    const normalizedEmail = normalizeEmail(email);
    if (!isValidEmail(normalizedEmail)) {
      setError("Enter a valid email address.");
      setSubmitting(false);
      return;
    }
    if (!isValidOtpCode(code.trim())) {
      setError("Enter the 8-digit recovery code.");
      setSubmitting(false);
      return;
    }
    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      setSubmitting(false);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      setSubmitting(false);
      return;
    }
    try {
      const response = await resetPassword({
        email: normalizedEmail,
        code: code.trim(),
        new_password: newPassword,
      });
      setMessage(response.message);
      setStep("done");
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 429) {
        setError("Too many attempts. Request a new recovery code and try again.");
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not reset your password.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="recovery-title">
        <span className="eyebrow">ACCOUNT RECOVERY</span>
        <h1 id="recovery-title">Reset your password</h1>
        {step === "request" && (
          <>
            <p>Enter your account email address to request a recovery code.</p>
            <form className="account-form" onSubmit={handleRequest} noValidate>
              <label htmlFor="recovery-email">Email address</label>
              <input
                autoComplete="email"
                id="recovery-email"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
                type="email"
                value={email}
              />
              {error && <p className="account-error" role="alert">{error}</p>}
              {message && <p className="account-success" role="status">{message}</p>}
              <button className="button button--primary button--wide" disabled={submitting} type="submit">
                {submitting ? "Sending…" : "Request recovery code"}
              </button>
            </form>
          </>
        )}

        {step === "reset" && (
          <>
            <p>Enter the 8-digit recovery code sent to your email, then choose a new password.</p>
            <form className="account-form" onSubmit={handleReset} noValidate>
              <label htmlFor="reset-email">Email address</label>
              <input
                autoComplete="email"
                id="reset-email"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
              <label htmlFor="reset-code">Recovery code</label>
              <input
                autoComplete="one-time-code"
                id="reset-code"
                inputMode="numeric"
                maxLength={8}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
                pattern="[0-9]{8}"
                placeholder="12345678"
                value={code}
              />
              <label htmlFor="reset-password">New password</label>
              <div className="password-control">
                <input
                  autoComplete="new-password"
                  id="reset-password"
                  onChange={(event) => setNewPassword(event.target.value)}
                  type={showPassword ? "text" : "password"}
                  value={newPassword}
                />
                <button onClick={() => setShowPassword((shown) => !shown)} type="button">
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <label htmlFor="reset-confirm">Confirm new password</label>
              <input
                autoComplete="new-password"
                id="reset-confirm"
                onChange={(event) => setConfirmPassword(event.target.value)}
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
              />
              <span className="account-field-hint">At least 12 characters, including a letter and a number.</span>
              {error && <p className="account-error" role="alert">{error}</p>}
              {message && <p className="account-success" role="status">{message}</p>}
              <button className="button button--primary button--wide" disabled={submitting} type="submit">
                {submitting ? "Resetting…" : "Reset password"}
              </button>
            </form>
          </>
        )}

        {step === "done" && (
          <>
            {message && <p className="account-success" role="status">{message}</p>}
            <p><Link className="button button--primary button--wide" to="/login">Back to sign in</Link></p>
          </>
        )}

        <p className="account-switch"><Link to="/login">Back to sign in</Link></p>
      </section>
    </main>
  );
}
