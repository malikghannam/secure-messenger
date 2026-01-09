"""
Extension Points Module

This module defines interfaces and hooks for future feature extensions without
implementing the actual features. These extension points provide architectural
support for encrypted file transfer, voice/video calls, multi-device support,
UI enhancements, and 2FA integration.

All interfaces are designed to be implemented in the future without modifying
the core cryptographic layer or existing application logic.
"""

from .file_transfer import FileTransferInterface, FileTransferHooks
from .media_transport import MediaTransportInterface, MediaTransportHooks
from .multi_device import MultiDeviceInterface, MultiDeviceHooks
from .ui_framework import UIFrameworkInterface, UIExtensionHooks
from .authentication import TwoFactorInterface, AuthenticationHooks

__all__ = [
    'FileTransferInterface',
    'FileTransferHooks', 
    'MediaTransportInterface',
    'MediaTransportHooks',
    'MultiDeviceInterface',
    'MultiDeviceHooks',
    'UIFrameworkInterface',
    'UIExtensionHooks',
    'TwoFactorInterface',
    'AuthenticationHooks'
]