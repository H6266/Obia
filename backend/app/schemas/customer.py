import re
from datetime import datetime
from uuid import UUID

import phonenumbers
from pydantic import BaseModel, ConfigDict, Field, field_validator
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
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2 or not any(character.isalpha() for character in normalized):
            raise ValueError("Enter your full name.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(CustomerPhone):
    password: str = Field(min_length=1, max_length=128)


class PasswordRecoveryRequest(CustomerPhone):
    pass


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class PhoneVerificationRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class CustomerAccount(BaseModel):
    id: UUID
    full_name: str
    phone: str
    phone_verified: bool
    account_status: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
