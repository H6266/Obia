export function isValidGhanaPhone(value: string): boolean {
  const digits = value.replace(/\D/g, "");
  const localNumber = digits.startsWith("233") ? digits.slice(3) : digits;
  return /^0[235]\d{8}$/.test(localNumber) || /^[235]\d{8}$/.test(localNumber);
}

export function maskPhoneNumber(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 4) return "Not entered";
  return `••• ••• ${digits.slice(-3)}`;
}
