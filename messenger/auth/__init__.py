"""
Authentication Module

Provides email verification, TOTP two-factor authentication, and authentication services.
"""

from .email_verification import (
    EmailVerificationService,
    get_verification_service,
    PendingVerification
)

from .totp_service import (
    TOTPService,
    get_totp_service
)

from .qr_generator import (
    QRCodeGenerator,
    get_qr_generator
)

from .totp_client import (
    TOTPClient,
    TOTPClientError,
    get_totp_client
)

__all__ = [
    'EmailVerificationService',
    'get_verification_service',
    'PendingVerification',
    'TOTPService',
    'get_totp_service',
    'QRCodeGenerator',
    'get_qr_generator',
    'TOTPClient',
    'TOTPClientError',
    'get_totp_client'
]
