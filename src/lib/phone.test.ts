import { describe, expect, it } from "vitest";
import { isValidGhanaPhone, maskPhoneNumber } from "./phone";

describe("Ghana phone number helpers", () => {
  it.each(["0241234567", "541234567", "+233 24 123 4567"])(
    "accepts a valid local or international number: %s",
    (phone) => {
      expect(isValidGhanaPhone(phone)).toBe(true);
    },
  );

  it.each(["", "123", "020123456", "02412345678"])(
    "rejects an invalid number: %s",
    (phone) => {
      expect(isValidGhanaPhone(phone)).toBe(false);
    },
  );

  it("masks a recipient number except for the final three digits", () => {
    expect(maskPhoneNumber("0241234567")).toBe("••• ••• 567");
    expect(maskPhoneNumber("")).toBe("Not entered");
  });
});
