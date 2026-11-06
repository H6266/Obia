from typing import Protocol


class PhoneVerificationProvider(Protocol):
    def send_verification_code(self, phone: str) -> None:
        """Send a verification challenge using a configured SMS provider."""

    def verify_code(self, phone: str, code: str) -> bool:
        """Validate a provider-issued phone verification challenge."""


class PasswordRecoveryProvider(Protocol):
    def send_recovery_link(self, phone: str, token: str) -> None:
        """Send a single-use password recovery link through a real provider."""


class EmailDeliveryProvider(Protocol):
    def send_email(self, to: str, subject: str, html: str, text: str) -> None:
        """Send a transactional email through a configured provider."""

