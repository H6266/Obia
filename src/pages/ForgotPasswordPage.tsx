import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { requestPasswordRecovery } from "../lib/api";

export function ForgotPasswordPage() {
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      await requestPasswordRecovery(phone);
      setMessage("Recovery request accepted.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Password recovery is not available.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="recovery-title">
        <span className="eyebrow">ACCOUNT RECOVERY</span>
        <h1 id="recovery-title">Forgot your password?</h1>
        <p>Enter your account phone number to check recovery availability.</p>
        <form className="account-form" onSubmit={handleSubmit}>
          <label htmlFor="recovery-phone">Ghanaian phone number</label>
          <input
            autoComplete="tel"
            id="recovery-phone"
            inputMode="tel"
            onChange={(event) => setPhone(event.target.value)}
            placeholder="024 123 4567"
            required
            value={phone}
          />
          {error && <p className="account-error" role="alert">{error}</p>}
          {message && <p className="account-success" role="status">{message}</p>}
          <button className="button button--primary button--wide" disabled={submitting} type="submit">
            {submitting ? "Checking…" : "Request recovery"}
          </button>
        </form>
        <div className="account-provider-note">
          Recovery is currently unavailable. No SMS or recovery message will be sent until a real provider is configured.
        </div>
        <p className="account-switch"><Link to="/login">Back to sign in</Link></p>
      </section>
    </main>
  );
}
