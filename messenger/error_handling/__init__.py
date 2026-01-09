"""
Error Handling Framework

This module provides comprehensive error handling with proper categorization,
secure logging, and graceful degradation for the secure messaging application.
"""

from .error_categories import (
    MessengerError, CryptoError, NetworkError, ValidationError, 
    StateError, StorageError, AuthenticationError
)
from .secure_logger import SecureLogger
from .error_recovery import ErrorRecoveryManager
from .graceful_degradation import GracefulDegradationManager

__all__ = [
    'MessengerError', 'CryptoError', 'NetworkError', 'ValidationError',
    'StateError', 'StorageError', 'AuthenticationError',
    'SecureLogger', 'ErrorRecoveryManager', 'GracefulDegradationManager'
]