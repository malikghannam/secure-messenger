"""Secure file sharing module."""

from messenger.files.models import (
    PolicyType,
    FilePolicy,
    SecureFile,
    SecureFileResult,
    SecureFileContent,
    FileValidationResult,
)
from messenger.files.config import (
    SUPPORTED_FILE_TYPES,
    get_max_size_for_type,
    is_supported_type,
    get_category,
    get_extension,
)
from messenger.files.validator import (
    validate_file,
    validate_file_content,
    detect_mime_type,
    detect_mime_type_from_content,
)
from messenger.files.policy_engine import (
    PolicyEngine,
    PolicyValidationResult,
    AccessCheckResult,
    ViewRecordResult,
)
from messenger.files.encryption import (
    generate_file_key,
    encrypt_file,
    decrypt_file,
    encrypt_file_with_new_key,
)
from messenger.files.secure_file_service import SecureFileService
from messenger.files.viewer import FileViewer, ViewSession, CloseResult
from messenger.files.expiration_manager import (
    ExpirationManager,
    DeletionResult,
    CleanupResult,
    ExpirationStatus,
)
from messenger.files.notifications import (
    NotificationService,
    NotificationType,
    FileNotification,
    get_notification_service,
)
from messenger.files.file_message_handler import (
    FileMessageHandler,
    get_file_handler,
)

__all__ = [
    'PolicyType',
    'FilePolicy',
    'SecureFile',
    'SecureFileResult',
    'SecureFileContent',
    'FileValidationResult',
    'SUPPORTED_FILE_TYPES',
    'get_max_size_for_type',
    'is_supported_type',
    'get_category',
    'get_extension',
    'validate_file',
    'validate_file_content',
    'detect_mime_type',
    'detect_mime_type_from_content',
    'PolicyEngine',
    'PolicyValidationResult',
    'AccessCheckResult',
    'ViewRecordResult',
    'generate_file_key',
    'encrypt_file',
    'decrypt_file',
    'encrypt_file_with_new_key',
    'SecureFileService',
    'FileViewer',
    'ViewSession',
    'CloseResult',
    'ExpirationManager',
    'DeletionResult',
    'CleanupResult',
    'ExpirationStatus',
    'NotificationService',
    'NotificationType',
    'FileNotification',
    'get_notification_service',
    'FileMessageHandler',
    'get_file_handler',
]
