import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";
import { validateRegistration } from "../lib/authValidation";

export function SignupPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedPolicies, setAcceptedPolicies] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateRegistration({
      fullName,
      email,
      phone,
      password,
      confirmPassword,
      acceptedPolicies,
    });
    setFieldErrors(errors);
    setError("");
    if (Object.keys(errors).length) return;

    setSubmitting(true);
    try {
      const response = await register({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        phone,
        password,
      });
      navigate("/verify-email", {
        replace: true,
        state: { email: response.email },
      });
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
        <span className="eyebrow">JOIN OBIA</span>
        <h1 id="signup-title">Create your account</h1>
        <p>Use your email address to verify your account and manage purchase requests.</p>
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

          <label htmlFor="signup-email">Email address</label>
          <input
            autoComplete="email"
            id="signup-email"
            inputMode="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            type="email"
            value={email}
            aria-invalid={Boolean(fieldErrors.email)}
          />
          {fieldErrors.email && <span className="account-field-error">{fieldErrors.email}</span>}

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
          <div className="password-control">
            <input
              autoComplete="new-password"
              id="signup-password"
              onChange={(event) => setPassword(event.target.value)}
              type={showPassword ? "text" : "password"}
              value={password}
              aria-invalid={Boolean(fieldErrors.password)}
            />
            <button onClick={() => setShowPassword((shown) => !shown)} type="button">
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          <span className="account-field-hint">At least 12 characters, including a letter and a number.</span>
          {fieldErrors.password && <span className="account-field-error">{fieldErrors.password}</span>}

          <label htmlFor="signup-confirm">Confirm password</label>
          <input
            autoComplete="new-password"
            id="signup-confirm"
            onChange={(event) => setConfirmPassword(event.target.value)}
            type={showPassword ? "text" : "password"}
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
          After you register, Obia will send an 8-digit verification code to your email address. You must verify your email before signing in.
        </div>
        <p className="account-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
