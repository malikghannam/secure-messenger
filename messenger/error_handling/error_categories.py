"""
Error Categories

Defines the hierarchy of error types for the secure messaging application.
Each error category provides specific handling and user-friendly messaging.
"""

from typing import Optional, Dict, Any
import logging


class MessengerError(Exception):
    """
    Base exception for all messenger-related errors.
    
    Provides structured error information with user-friendly messages
    and secure logging capabilities.
    """
    
    def __init__(
        self, 
        message: str, 
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize messenger error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly error message
            error_code: Standardized error code
            details: Additional error details (will be sanitized for logging)
            recoverable: Whether the error is recoverable
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or self._get_default_user_message()
        self.error_code = error_code or self._get_default_error_code()
        self.details = details or {}
        self.recoverable = recoverable
    
    def _get_default_user_message(self) -> str:
        """Get default user-friendly message for this error type."""
        return "An unexpected error occurred. Please try again."
    
    def _get_default_error_code(self) -> str:
        """Get default error code for this error type."""
        return "internal_error"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            'ok': False,
            'error': self.error_code,
            'message': self.user_message,
            'recoverable': self.recoverable
        }
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        """Get sanitized data safe for logging (no sensitive information)."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'recoverable': self.recoverable,
            'details_count': len(self.details) if self.details else 0
        }


class CryptoError(MessengerError):
    """
    Cryptographic operation errors.
    
    These errors occur during encryption, decryption, key generation,
    or other cryptographic operations. They never expose key material
    or sensitive cryptographic state in logs.
    """
    
    def _get_default_user_message(self) -> str:
        return "Secure communication error. Please try again or restart the conversation."
    
    def _get_default_error_code(self) -> str:
        return "crypto_error"
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        """Crypto errors get extra sanitization - no crypto details logged."""
        base_data = super().get_secure_log_data()
        # Never log crypto-specific details
        base_data['crypto_operation'] = 'redacted'
        return base_data


class NetworkError(MessengerError):
    """
    Network and transport-related errors.
    
    These errors occur during HTTP requests, WebSocket connections,
    or other network operations.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
    
    def _get_default_user_message(self) -> str:
        return "Connection problem. Please check your internet connection and try again."
    
    def _get_default_error_code(self) -> str:
        return "network_error"
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        base_data = super().get_secure_log_data()
        if self.status_code:
            base_data['status_code'] = self.status_code
        return base_data


class ValidationError(MessengerError):
    """
    Input validation and data format errors.
    
    These errors occur when user input or data doesn't meet
    expected formats or constraints.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
    
    def _get_default_user_message(self) -> str:
        if self.field:
            return f"Invalid {self.field}. Please check your input and try again."
        return "Invalid input. Please check your data and try again."
    
    def _get_default_error_code(self) -> str:
        return "validation_error"
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        base_data = super().get_secure_log_data()
        if self.field:
            base_data['field'] = self.field
        return base_data


class StateError(MessengerError):
    """
    Application state inconsistency errors.
    
    These errors occur when the application state becomes
    inconsistent or corrupted.
    """
    
    def _get_default_user_message(self) -> str:
        return "Application state error. Please refresh the page or restart the application."
    
    def _get_default_error_code(self) -> str:
        return "state_error"


class StorageError(MessengerError):
    """
    Local storage and persistence errors.
    
    These errors occur during file I/O, database operations,
    or other storage-related operations.
    """
    
    def __init__(self, message: str, storage_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.storage_type = storage_type
    
    def _get_default_user_message(self) -> str:
        return "Storage error. Please check available disk space and file permissions."
    
    def _get_default_error_code(self) -> str:
        return "storage_error"
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        base_data = super().get_secure_log_data()
        if self.storage_type:
            base_data['storage_type'] = self.storage_type
        return base_data


class AuthenticationError(MessengerError):
    """
    Authentication and authorization errors.
    
    These errors occur during login, session validation,
    or permission checks.
    """
    
    def _get_default_user_message(self) -> str:
        return "Authentication error. Please log in again."
    
    def _get_default_error_code(self) -> str:
        return "authentication_error"
    
    def get_secure_log_data(self) -> Dict[str, Any]:
        base_data = super().get_secure_log_data()
        # Never log authentication details
        base_data['auth_details'] = 'redacted'
        return base_data


# Error mapping for converting generic exceptions to messenger errors
ERROR_MAPPING = {
    ConnectionError: NetworkError,
    TimeoutError: NetworkError,
    ValueError: ValidationError,
    KeyError: StateError,
    FileNotFoundError: StorageError,
    PermissionError: StorageError,
    OSError: StorageError,
}


def categorize_error(error: Exception) -> MessengerError:
    """
    Convert a generic exception to an appropriate MessengerError.
    
    Args:
        error: The original exception
        
    Returns:
        Categorized MessengerError instance
    """
    if isinstance(error, MessengerError):
        return error
    
    error_type = type(error)
    messenger_error_class = ERROR_MAPPING.get(error_type, MessengerError)
    
    return messenger_error_class(
        message=str(error),
        details={'original_type': error_type.__name__}
    )