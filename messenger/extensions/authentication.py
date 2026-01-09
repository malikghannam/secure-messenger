"""
Authentication Extension Interface

This module defines interfaces for future 2FA and enhanced authentication
capabilities. The interfaces are designed to extend the existing authentication
system without modifying the core login/registration flow.

These interfaces are NOT implemented - they provide architectural hooks for
future development.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime, timedelta


class TwoFactorMethod(Enum):
    """Types of two-factor authentication methods."""
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"    # SMS verification
    EMAIL = "email"  # Email verification
    HARDWARE_KEY = "hardware_key"  # Hardware security key
    BACKUP_CODES = "backup_codes"  # Recovery codes


class AuthenticationStatus(Enum):
    """Status of authentication attempts."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    LOCKED = "locked"


class TwoFactorInterface(ABC):
    """
    Interface for two-factor authentication capabilities.
    
    This interface defines how 2FA would integrate with the existing
    authentication system. 2FA would add an additional verification step
    after username/password authentication without modifying the core
    cryptographic identity system.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    @abstractmethod
    def enable_2fa(
        self, 
        username: str,
        method: TwoFactorMethod,
        method_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enable two-factor authentication for a user.
        
        Args:
            username: Username to enable 2FA for
            method: Type of 2FA method to enable
            method_config: Method-specific configuration
            
        Returns:
            Setup information (e.g., QR code for TOTP, backup codes)
        """
        pass
    
    @abstractmethod
    def disable_2fa(self, username: str, method: TwoFactorMethod) -> bool:
        """
        Disable two-factor authentication for a user.
        
        Args:
            username: Username to disable 2FA for
            method: Type of 2FA method to disable
            
        Returns:
            True if 2FA was disabled successfully
        """
        pass
    
    @abstractmethod
    def verify_2fa_code(
        self, 
        username: str,
        method: TwoFactorMethod,
        code: str
    ) -> bool:
        """
        Verify a two-factor authentication code.
        
        Args:
            username: Username attempting verification
            method: 2FA method being used
            code: Verification code provided by user
            
        Returns:
            True if code is valid and verification succeeds
        """
        pass
    
    @abstractmethod
    def generate_backup_codes(self, username: str) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            username: Username to generate codes for
            
        Returns:
            List of one-time backup codes
        """
        pass
    
    @abstractmethod
    def get_enabled_methods(self, username: str) -> List[TwoFactorMethod]:
        """
        Get list of enabled 2FA methods for a user.
        
        Args:
            username: Username to check
            
        Returns:
            List of enabled 2FA methods
        """
        pass
    
    @abstractmethod
    def is_2fa_required(self, username: str) -> bool:
        """
        Check if 2FA is required for a user.
        
        Args:
            username: Username to check
            
        Returns:
            True if 2FA is required for this user
        """
        pass
    
    @abstractmethod
    def get_auth_status(self, username: str) -> AuthenticationStatus:
        """
        Get current authentication status for a user.
        
        Args:
            username: Username to check
            
        Returns:
            Current authentication status
        """
        pass


class AuthenticationHooks:
    """
    Hook system for authentication events.
    
    This class provides hooks that would be called during authentication
    operations, allowing the UI and other components to respond to auth
    events without tight coupling to the authentication implementation.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    def __init__(self):
        """Initialize authentication hooks."""
        self._callbacks = {
            'login_attempt': None,
            'login_success': None,
            'login_failed': None,
            '2fa_required': None,
            '2fa_verified': None,
            '2fa_failed': None,
            'account_locked': None,
            'password_changed': None,
            '2fa_enabled': None,
            '2fa_disabled': None
        }
    
    def register_login_attempt_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for login attempts.
        
        Args:
            callback: Function called with (username, ip_address)
        """
        self._callbacks['login_attempt'] = callback
    
    def register_login_success_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for successful logins.
        
        Args:
            callback: Function called with (username,)
        """
        self._callbacks['login_success'] = callback
    
    def register_login_failed_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for failed logins.
        
        Args:
            callback: Function called with (username, failure_reason)
        """
        self._callbacks['login_failed'] = callback
    
    def register_2fa_required_hook(
        self, 
        callback: Callable[[str, List[TwoFactorMethod]], None]
    ):
        """
        Register callback for when 2FA is required.
        
        Args:
            callback: Function called with (username, available_methods)
        """
        self._callbacks['2fa_required'] = callback
    
    def register_2fa_verified_hook(
        self, 
        callback: Callable[[str, TwoFactorMethod], None]
    ):
        """
        Register callback for successful 2FA verification.
        
        Args:
            callback: Function called with (username, method_used)
        """
        self._callbacks['2fa_verified'] = callback
    
    def register_2fa_failed_hook(
        self, 
        callback: Callable[[str, TwoFactorMethod, int], None]
    ):
        """
        Register callback for failed 2FA attempts.
        
        Args:
            callback: Function called with (username, method_used, attempt_count)
        """
        self._callbacks['2fa_failed'] = callback
    
    def register_account_locked_hook(
        self, 
        callback: Callable[[str, timedelta], None]
    ):
        """
        Register callback for when an account is locked.
        
        Args:
            callback: Function called with (username, lockout_duration)
        """
        self._callbacks['account_locked'] = callback
    
    def register_2fa_enabled_hook(
        self, 
        callback: Callable[[str, TwoFactorMethod], None]
    ):
        """
        Register callback for when 2FA is enabled.
        
        Args:
            callback: Function called with (username, method_enabled)
        """
        self._callbacks['2fa_enabled'] = callback
    
    def register_2fa_disabled_hook(
        self, 
        callback: Callable[[str, TwoFactorMethod], None]
    ):
        """
        Register callback for when 2FA is disabled.
        
        Args:
            callback: Function called with (username, method_disabled)
        """
        self._callbacks['2fa_disabled'] = callback