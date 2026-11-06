import { describe, expect, it } from "vitest";
import { isValidEmail, isValidOtpCode, validatePassword, validateRegistration } from "./authValidation";

describe("auth validation helpers", () => {
  it("validates email addresses", () => {
    expect(isValidEmail("amina@example.com")).toBe(true);
    expect(isValidEmail("AMINA@EXAMPLE.COM")).toBe(true);
    expect(isValidEmail("not-an-email")).toBe(false);
  });

  it("validates 8-digit OTP codes", () => {
    expect(isValidOtpCode("12345678")).toBe(true);
    expect(isValidOtpCode("01234567")).toBe(true);
    expect(isValidOtpCode("1234567")).toBe(false);
    expect(isValidOtpCode("abcdefgh")).toBe(false);
  });

  it("enforces password policy", () => {
    expect(validatePassword("secure-customer-pass-2026")).toBeNull();
    expect(validatePassword("short1")).toContain("12 characters");
    expect(validatePassword("alllettersandlong")).toContain("letter and one number");
  });

  it("collects registration errors", () => {
    const errors = validateRegistration({
      fullName: "A",
      email: "bad",
      phone: "123",
      password: "short",
      confirmPassword: "different",
      acceptedPolicies: false,
    });
    expect(errors.full_name).toBeTruthy();
    expect(errors.email).toBeTruthy();
    expect(errors.phone).toBeTruthy();
    expect(errors.password).toBeTruthy();
    expect(errors.confirmPassword).toBeTruthy();
    expect(errors.acceptedPolicies).toBeTruthy();
  });
});
