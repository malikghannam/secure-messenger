"""
TOTP Two-Factor Authentication Service

Implements RFC 6238 TOTP (Time-based One-Time Password) for two-factor authentication.
Provides secret generation, code verification with time window tolerance,
backup code management, and QR code generation for authenticator apps.
"""

import os
import time
import secrets
import hashlib
import hmac
import base64
import json
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TOTPService:
    """
    TOTP Service for generating and verifying time-based one-time passwords.
    
    Implements RFC 6238 with:
    - 6-digit codes
    - 30-second time steps
    - HMAC-SHA1 algorithm
    - ±1 time window tolerance
    """
    
    DIGITS = 6
    TIME_STEP = 30  # seconds
    WINDOW = 1      # ±1 period tolerance
    SECRET_LENGTH = 32  # characters (160 bits)
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 8
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes in seconds
    
    # Base32 alphabet for secret generation
    BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize TOTP service.
        
        Args:
            encryption_key: Fernet encryption key for storing secrets.
                           If None, will try to load from environment.
        """
        self._encryption_key = encryption_key or self._get_encryption_key()
        self._fernet = Fernet(self._encryption_key) if self._encryption_key else None
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key from environment or load/generate from file."""
        # First try environment variables
        key = os.environ.get('TOTP_ENCRYPTION_KEY') or os.environ.get('EMAIL_ENCRYPTION_KEY')
        if key:
            return key.encode() if isinstance(key, str) else key
        
        # Try to load from file (persistent key for development)
        key_file = os.path.join(os.path.dirname(__file__), '.totp_key')
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read TOTP key file: {e}")
        
        # Generate new key and save it
        new_key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(new_key)
            logger.info("Generated and saved new TOTP encryption key")
        except Exception as e:
            logger.warning(f"Failed to save TOTP key file: {e}")
        
        return new_key
    
    def generate_secret(self) -> str:
        """
        Generate a new base32-encoded secret key.
        
        Returns:
            A 32-character base32-encoded string.
        """
        # Generate random bytes and encode as base32
        random_bytes = secrets.token_bytes(20)  # 160 bits
        secret = base64.b32encode(random_bytes).decode('utf-8')
        # Ensure exactly 32 characters (pad or trim if needed)
        return secret[:self.SECRET_LENGTH]
    
    def generate_provisioning_uri(
        self, 
        secret: str, 
        username: str, 
        issuer: str = "SecureMessenger"
    ) -> str:
        """
        Generate otpauth:// URI for authenticator apps.
        
        Args:
            secret: Base32-encoded secret key
            username: User's account name
            issuer: Service name to display in authenticator
            
        Returns:
            otpauth:// URI string
        """
        # URL encode the parameters
        from urllib.parse import quote
        
        label = f"{issuer}:{username}"
        params = {
            'secret': secret,
            'issuer': issuer,
            'algorithm': 'SHA1',
            'digits': str(self.DIGITS),
            'period': str(self.TIME_STEP)
        }
        
        param_str = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"otpauth://totp/{quote(label)}?{param_str}"

    
    def _get_time_counter(self, timestamp: Optional[float] = None) -> int:
        """
        Get the time counter for TOTP calculation.
        
        Args:
            timestamp: Unix timestamp. If None, uses current time.
            
        Returns:
            Time counter (timestamp // TIME_STEP)
        """
        if timestamp is None:
            timestamp = time.time()
        return int(timestamp) // self.TIME_STEP
    
    def _generate_totp(self, secret: str, counter: int) -> str:
        """
        Generate TOTP code for a given counter value.
        
        Implements RFC 6238 / RFC 4226 HOTP algorithm.
        
        Args:
            secret: Base32-encoded secret key
            counter: Time counter value
            
        Returns:
            6-digit TOTP code as string
        """
        # Decode base32 secret
        try:
            key = base64.b32decode(secret.upper())
        except Exception:
            raise ValueError("Invalid base32 secret")
        
        # Convert counter to 8-byte big-endian
        counter_bytes = counter.to_bytes(8, byteorder='big')
        
        # Calculate HMAC-SHA1
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation (RFC 4226)
        offset = hmac_hash[-1] & 0x0F
        binary = (
            ((hmac_hash[offset] & 0x7F) << 24) |
            ((hmac_hash[offset + 1] & 0xFF) << 16) |
            ((hmac_hash[offset + 2] & 0xFF) << 8) |
            (hmac_hash[offset + 3] & 0xFF)
        )
        
        # Generate 6-digit code
        otp = binary % (10 ** self.DIGITS)
        return str(otp).zfill(self.DIGITS)
    
    def generate_code(self, secret: str, timestamp: Optional[float] = None) -> str:
        """
        Generate current TOTP code.
        
        Args:
            secret: Base32-encoded secret key
            timestamp: Unix timestamp. If None, uses current time.
            
        Returns:
            6-digit TOTP code as string
        """
        counter = self._get_time_counter(timestamp)
        return self._generate_totp(secret, counter)
    
    def verify_code(
        self, 
        secret: str, 
        code: str, 
        window: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        Verify TOTP code with time window tolerance.
        
        Args:
            secret: Base32-encoded secret key
            code: 6-digit code to verify
            window: Time window tolerance (default: ±1 period)
            
        Returns:
            Tuple of (is_valid, time_drift) where time_drift is periods offset.
            time_drift is 0 for current period, negative for past, positive for future.
        """
        if window is None:
            window = self.WINDOW
        
        # Validate code format
        if not code or len(code) != self.DIGITS or not code.isdigit():
            return False, 0
        
        current_counter = self._get_time_counter()
        
        # Check current and adjacent time periods
        for offset in range(-window, window + 1):
            expected_code = self._generate_totp(secret, current_counter + offset)
            # Use constant-time comparison to prevent timing attacks
            if hmac.compare_digest(code, expected_code):
                return True, offset
        
        return False, 0
    
    def generate_backup_codes(self) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Returns:
            List of 10 unique 8-character alphanumeric codes.
        """
        codes = set()
        while len(codes) < self.BACKUP_CODE_COUNT:
            # Generate random alphanumeric code
            code = ''.join(
                secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')  # Exclude confusing chars
                for _ in range(self.BACKUP_CODE_LENGTH)
            )
            codes.add(code)
        return list(codes)
    
    def hash_backup_code(self, code: str) -> str:
        """Hash a backup code for secure storage."""
        return hashlib.sha256(code.upper().encode()).hexdigest()
    
    def verify_backup_code(
        self, 
        stored_hashes: List[str], 
        provided_code: str
    ) -> Tuple[bool, List[str]]:
        """
        Verify backup code and return remaining codes.
        
        Args:
            stored_hashes: List of hashed backup codes
            provided_code: Code provided by user
            
        Returns:
            Tuple of (is_valid, remaining_hashes).
            If valid, the used code's hash is removed from remaining_hashes.
        """
        provided_hash = self.hash_backup_code(provided_code)
        
        # Use constant-time comparison for each hash
        for i, stored_hash in enumerate(stored_hashes):
            if hmac.compare_digest(provided_hash, stored_hash):
                # Remove used code and return remaining
                remaining = stored_hashes[:i] + stored_hashes[i+1:]
                return True, remaining
        
        return False, stored_hashes
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret for storage."""
        if self._fernet:
            return self._fernet.encrypt(secret.encode()).decode()
        return secret  # Fallback for development
    
    def decrypt_secret(self, encrypted: str) -> str:
        """Decrypt TOTP secret from storage."""
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception:
                logger.error("Failed to decrypt TOTP secret")
                raise ValueError("Failed to decrypt TOTP secret")
        return encrypted


# Global instance
_totp_service: Optional[TOTPService] = None


def get_totp_service() -> TOTPService:
    """Get or create the global TOTP service instance."""
    global _totp_service
    if _totp_service is None:
        _totp_service = TOTPService()
    return _totp_service
