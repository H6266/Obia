import { isValidGhanaPhone } from "./phone";

export function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

export function isValidEmail(value: string): boolean {
  const email = normalizeEmail(value);
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254;
}

export function validatePassword(value: string): string | null {
  if (value.length < 12 || !/[a-zA-Z]/.test(value) || !/\d/.test(value)) {
    return "Use at least 12 characters with at least one letter and one number.";
  }
  return null;
}

export function isValidOtpCode(value: string): boolean {
  return /^\d{8}$/.test(value.trim());
}

export function validateRegistration(input: {
  fullName: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
  acceptedPolicies: boolean;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  if (input.fullName.trim().length < 2) errors.full_name = "Enter your full name.";
  if (!isValidEmail(input.email)) errors.email = "Enter a valid email address.";
  if (!isValidGhanaPhone(input.phone)) errors.phone = "Enter a valid Ghanaian mobile number.";
  const passwordError = validatePassword(input.password);
  if (passwordError) errors.password = passwordError;
  if (input.password !== input.confirmPassword) errors.confirmPassword = "Passwords do not match.";
  if (!input.acceptedPolicies) errors.acceptedPolicies = "You must accept the Terms and Privacy Policy.";
  return errors;
}
