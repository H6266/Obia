import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";
import { isValidGhanaPhone } from "../lib/phone";

export function SignupPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedPolicies, setAcceptedPolicies] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors: Record<string, string> = {};
    if (fullName.trim().length < 2) errors.full_name = "Enter your full name.";
    if (!isValidGhanaPhone(phone)) errors.phone = "Enter a valid Ghanaian mobile number.";
    if (password.length < 12 || !/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      errors.password = "Use at least 12 characters with at least one letter and one number.";
    }
    if (password !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
    if (!acceptedPolicies) errors.acceptedPolicies = "You must accept the Terms and Privacy Policy.";
    setFieldErrors(errors);
    setError("");
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      await register({ full_name: fullName.trim(), phone, password });
      navigate("/dashboard", { replace: true, state: { welcome: true } });
    } catch (requestError) {
      if (requestError instanceof ApiError) setFieldErrors(requestError.fieldErrors);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not create your account. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="account-page" id="main-content" tabIndex={-1}>
      <section className="account-card" aria-labelledby="signup-title">
        <span className="eyebrow">JOIN FALAAA</span>
        <h1 id="signup-title">Create your account</h1>
        <p>Use your Ghanaian mobile number to manage purchase requests and order history.</p>
        <form className="account-form" onSubmit={handleSubmit} noValidate>
          <label htmlFor="signup-name">Full name</label>
          <input
            autoComplete="name"
            id="signup-name"
            maxLength={100}
            onChange={(event) => setFullName(event.target.value)}
            value={fullName}
            aria-invalid={Boolean(fieldErrors.full_name)}
          />
          {fieldErrors.full_name && <span className="account-field-error">{fieldErrors.full_name}</span>}

          <label htmlFor="signup-phone">Ghanaian phone number</label>
          <input
            autoComplete="tel"
            id="signup-phone"
            inputMode="tel"
            onChange={(event) => setPhone(event.target.value)}
            placeholder="024 123 4567"
            value={phone}
            aria-invalid={Boolean(fieldErrors.phone)}
          />
          {fieldErrors.phone && <span className="account-field-error">{fieldErrors.phone}</span>}

          <label htmlFor="signup-password">Password</label>
          <input
            autoComplete="new-password"
            id="signup-password"
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            value={password}
            aria-invalid={Boolean(fieldErrors.password)}
          />
          <span className="account-field-hint">At least 12 characters, including a letter and a number.</span>
          {fieldErrors.password && <span className="account-field-error">{fieldErrors.password}</span>}

          <label htmlFor="signup-confirm">Confirm password</label>
          <input
            autoComplete="new-password"
            id="signup-confirm"
            onChange={(event) => setConfirmPassword(event.target.value)}
            type="password"
            value={confirmPassword}
            aria-invalid={Boolean(fieldErrors.confirmPassword)}
          />
          {fieldErrors.confirmPassword && <span className="account-field-error">{fieldErrors.confirmPassword}</span>}

          <label className="account-checkbox">
            <input
              checked={acceptedPolicies}
              onChange={(event) => setAcceptedPolicies(event.target.checked)}
              type="checkbox"
            />
            <span>I agree to the <Link to="/terms">Terms of Use</Link> and <Link to="/privacy">Privacy Policy</Link>.</span>
          </label>
          {fieldErrors.acceptedPolicies && <span className="account-field-error">{fieldErrors.acceptedPolicies}</span>}

          {error && <p className="account-error" role="alert">{error}</p>}
          <button className="button button--primary button--wide" disabled={submitting} type="submit">
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <div className="account-provider-note" role="status">
          Your account will be active but phone-unverified. SMS verification is unavailable until an SMS provider is connected; no verification message has been sent.
        </div>
        <p className="account-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
