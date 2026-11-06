import re
from datetime import datetime
from uuid import UUID

from typing import Literal

import phonenumbers
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from phonenumbers import PhoneNumberFormat, PhoneNumberType


def normalize_ghana_phone(value: str) -> str:
    phone = value.strip()
    if not re.fullmatch(r"\+?[\d\s().-]{7,32}", phone):
        raise ValueError("Enter a valid Ghanaian mobile number.")

    digits = re.sub(r"\D", "", phone)
    parse_value = f"+{digits}" if digits.startswith("233") and not phone.startswith("+") else phone
    try:
        parsed = phonenumbers.parse(parse_value, "GH")
    except phonenumbers.NumberParseException as error:
        raise ValueError("Enter a valid Ghanaian mobile number.") from error

    if (
        not phonenumbers.is_valid_number_for_region(parsed, "GH")
        or phonenumbers.number_type(parsed)
        not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)
    ):
        raise ValueError("Enter a valid Ghanaian mobile number.")
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def normalize_email(value: str) -> str:
    return value.strip().lower()


class CustomerRead(BaseModel):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerPhone(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_ghana_phone(value)


class RegisterRequest(CustomerPhone):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2 or not any(character.isalpha() for character in normalized):
            raise ValueError("Enter your full name.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_customer_email(cls, value: str) -> str:
        return normalize_email(str(value))

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = None
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str | None) -> str | None:
        return normalize_email(str(value)) if value else None

    @field_validator("phone")
    @classmethod
    def normalize_login_phone(cls, value: str | None) -> str | None:
        return normalize_ghana_phone(value) if value else None

    @model_validator(mode="after")
    def require_identifier(self) -> "LoginRequest":
        if not self.email and not self.phone:
            raise ValueError("Enter your email address or phone number.")
        return self


class LoginChallengeResponse(BaseModel):
    login_required: bool = True
    challenge_token: str
    email: str | None = None
    phone_masked: str | None = None
    channels: list[str]
    message: str


class LoginVerificationRequest(BaseModel):
    challenge_token: str = Field(min_length=16, max_length=128)
    channel: Literal["email", "phone"] = "email"
    code: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()


class EmailVerificationRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    code: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")

    @field_validator("email")
    @classmethod
    def normalize_verification_email(cls, value: str) -> str:
        return normalize_email(str(value))

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()


class ResendEmailVerificationRequest(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_resend_email(cls, value: str) -> str:
        return normalize_email(str(value))


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_recovery_email(cls, value: str) -> str:
        return normalize_email(str(value))


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    code: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_reset_email(cls, value: str) -> str:
        return normalize_email(str(value))

    @field_validator("code")
    @classmethod
    def normalize_reset_code(cls, value: str) -> str:
        return value.strip()

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


# Legacy/phone verification compatibility (provider unavailable in this phase).
class PhoneVerificationRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class RegisterResponse(BaseModel):
    email: str
    verification_required: bool = True
    message: str


class GenericAuthResponse(BaseModel):
    message: str


class CustomerAccount(BaseModel):
    id: UUID
    identity_id: UUID
    full_name: str
    email: str
    phone: str
    phone_verified: bool
    email_verified: bool
    account_status: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
