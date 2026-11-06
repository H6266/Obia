import re
from datetime import datetime
from uuid import UUID

import phonenumbers
from pydantic import BaseModel, ConfigDict, field_validator
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
