"""
Email Verification Service

Handles verification code generation, sending via Gmail SMTP,
and validation for new user registration.
"""

import os
import re
import time
import random
import string
import hashlib
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class PendingVerification:
    """Stores pending registration data."""
    username: str
    password_hash: str
    email_encrypted: str
    code_hash: str
    created_at: float
    expires_at: float
    attempts: int = 0
    resend_count: int = 0
    last_resend: float = 0


class EmailVerificationService:
    """
    Handles email verification for new user registration.
    
    Features:
    - 6-digit verification code generation
    - Gmail SMTP email sending
    - Code expiration (10 minutes)
    - Attempt limiting (5 max)
    - Resend limiting (3 max, 60s cooldown)
    - Email encryption for storage
    """
    
    CODE_LENGTH = 6
    CODE_EXPIRY_SECONDS = 600  # 10 minutes
    MAX_ATTEMPTS = 5
    MAX_RESENDS = 3
    RESEND_COOLDOWN = 60  # seconds
    
    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the email verification service.
        
        Args:
            smtp_config: Optional SMTP configuration dict with keys:
                - server: SMTP server address
                - port: SMTP port
                - sender_email: Sender email address
                - sender_password: App-specific password
        """
        self.smtp_config = smtp_config or self._load_smtp_config()
        self._pending: Dict[str, PendingVerification] = {}
        self._encryption_key = self._get_encryption_key()
        self._fernet = Fernet(self._encryption_key) if self._encryption_key else None
    
    def _load_smtp_config(self) -> Dict[str, Any]:
        """Load SMTP configuration from environment variables."""
        return {
            'server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.environ.get('SMTP_PORT', '587')),
            'sender_email': os.environ.get('GMAIL_SENDER', ''),
            'sender_password': os.environ.get('GMAIL_APP_PASSWORD', ''),
        }
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get or generate encryption key for email storage."""
        key = os.environ.get('EMAIL_ENCRYPTION_KEY')
        if key:
            return key.encode() if isinstance(key, str) else key
        # Generate a key if not provided (for development)
        return Fernet.generate_key()
    
    def generate_code(self) -> str:
        """
        Generate a random 6-digit verification code.
        
        Returns:
            A string of exactly 6 numeric digits.
        """
        return ''.join(random.choices(string.digits, k=self.CODE_LENGTH))
    
    def _hash_code(self, code: str) -> str:
        """Hash the verification code for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def _encrypt_email(self, email: str) -> str:
        """Encrypt email address for storage."""
        if self._fernet:
            return self._fernet.encrypt(email.encode()).decode()
        return email  # Fallback for development
    
    def _decrypt_email(self, encrypted: str) -> str:
        """Decrypt email address."""
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception:
                return encrypted
        return encrypted
    
    def validate_gmail(self, email: str) -> bool:
        """
        Validate that the email is a valid Gmail address.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid Gmail address, False otherwise
        """
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        return bool(re.match(pattern, email.lower()))
    
    def mask_email(self, email: str) -> str:
        """
        Mask email for display (e.g., m***d@gmail.com).
        
        Args:
            email: Email address to mask
            
        Returns:
            Masked email string
        """
        if not email or '@' not in email:
            return '***@***.com'
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + '*' * (len(local) - 1) if len(local) > 1 else '*'
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def send_verification_email(self, email: str, code: str) -> Tuple[bool, str]:
        """
        Send verification code to the specified Gmail address.
        
        Args:
            email: Recipient email address
            code: Verification code to send
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.smtp_config.get('sender_email') or not self.smtp_config.get('sender_password'):
            logger.warning("SMTP not configured, skipping email send")
            return False, "Email service not configured"
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Secure Messenger - Verification Code'
            msg['From'] = self.smtp_config['sender_email']
            msg['To'] = email
            
            # Plain text version
            text = f"""
Your Secure Messenger verification code is:

{code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.
"""
            
            # HTML version
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #0a0a0a; color: #ffffff; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .code {{ font-size: 32px; font-weight: bold; color: #00d26a; letter-spacing: 8px; 
                 text-align: center; padding: 20px; background: #1a1a2e; border-radius: 8px; }}
        .footer {{ color: #888; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🔐 Secure Messenger</h2>
        <p>Your verification code is:</p>
        <div class="code">{code}</div>
        <p>This code will expire in <strong>10 minutes</strong>.</p>
        <p class="footer">If you didn't request this code, please ignore this email.</p>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['sender_email'], self.smtp_config['sender_password'])
                server.send_message(msg)
            
            logger.info(f"Verification email sent to {self.mask_email(email)}")
            return True, "Verification code sent"
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return False, "Email authentication failed"
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False, "Failed to send email"
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False, "Failed to send email"
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID for pending verification."""
        return hashlib.sha256(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:32]
    
    def store_pending_verification(
        self,
        email: str,
        code: str,
        username: str,
        password_hash: str
    ) -> str:
        """
        Store pending registration with verification code.
        
        Args:
            email: User's Gmail address
            code: Generated verification code
            username: Chosen username
            password_hash: Hashed password
            
        Returns:
            Session ID for this verification attempt
        """
        session_id = self.generate_session_id()
        now = time.time()
        
        self._pending[session_id] = PendingVerification(
            username=username,
            password_hash=password_hash,
            email_encrypted=self._encrypt_email(email),
            code_hash=self._hash_code(code),
            created_at=now,
            expires_at=now + self.CODE_EXPIRY_SECONDS,
            attempts=0,
            resend_count=0,
            last_resend=now
        )
        
        # Cleanup expired sessions
        self._cleanup_expired()
        
        return session_id
    
    def _cleanup_expired(self):
        """Remove expired pending verifications."""
        now = time.time()
        expired = [
            sid for sid, pv in self._pending.items()
            if pv.expires_at < now
        ]
        for sid in expired:
            del self._pending[sid]
    
    def verify_code(self, session_id: str, code: str) -> Dict[str, Any]:
        """
        Verify the code and return user data if valid.
        
        Args:
            session_id: Session ID from store_pending_verification
            code: Code entered by user
            
        Returns:
            Dict with keys:
                - success: bool
                - error: str (if failed)
                - username: str (if success)
                - password_hash: str (if success)
                - email_encrypted: str (if success)
        """
        if session_id not in self._pending:
            return {'success': False, 'error': 'Invalid or expired session'}
        
        pv = self._pending[session_id]
        now = time.time()
        
        # Check expiration
        if now > pv.expires_at:
            del self._pending[session_id]
            return {'success': False, 'error': 'Verification code expired'}
        
        # Check attempt limit
        if pv.attempts >= self.MAX_ATTEMPTS:
            return {'success': False, 'error': 'Too many failed attempts. Please request a new code.'}
        
        # Verify code
        if self._hash_code(code) != pv.code_hash:
            pv.attempts += 1
            remaining = self.MAX_ATTEMPTS - pv.attempts
            if remaining > 0:
                return {'success': False, 'error': f'Invalid code. {remaining} attempts remaining.'}
            else:
                return {'success': False, 'error': 'Too many failed attempts. Please request a new code.'}
        
        # Success - return user data and cleanup
        result = {
            'success': True,
            'username': pv.username,
            'password_hash': pv.password_hash,
            'email_encrypted': pv.email_encrypted
        }
        del self._pending[session_id]
        return result
    
    def resend_code(self, session_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate and send a new code, invalidating the old one.
        
        Args:
            session_id: Session ID from store_pending_verification
            
        Returns:
            Tuple of (success: bool, message: str, new_code: Optional[str])
        """
        if session_id not in self._pending:
            return False, 'Invalid or expired session', None
        
        pv = self._pending[session_id]
        now = time.time()
        
        # Check resend limit
        if pv.resend_count >= self.MAX_RESENDS:
            return False, 'Maximum resend attempts reached. Please try again later.', None
        
        # Check cooldown
        if now - pv.last_resend < self.RESEND_COOLDOWN:
            remaining = int(self.RESEND_COOLDOWN - (now - pv.last_resend))
            return False, f'Please wait {remaining} seconds before requesting a new code.', None
        
        # Generate new code
        new_code = self.generate_code()
        email = self._decrypt_email(pv.email_encrypted)
        
        # Send email
        success, msg = self.send_verification_email(email, new_code)
        if not success:
            return False, msg, None
        
        # Update pending verification
        pv.code_hash = self._hash_code(new_code)
        pv.resend_count += 1
        pv.last_resend = now
        pv.attempts = 0  # Reset attempts on resend
        pv.expires_at = now + self.CODE_EXPIRY_SECONDS
        
        return True, 'New verification code sent', new_code
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a pending verification session."""
        if session_id not in self._pending:
            return None
        
        pv = self._pending[session_id]
        now = time.time()
        
        return {
            'username': pv.username,
            'email_masked': self.mask_email(self._decrypt_email(pv.email_encrypted)),
            'expires_in': max(0, int(pv.expires_at - now)),
            'attempts_remaining': max(0, self.MAX_ATTEMPTS - pv.attempts),
            'resends_remaining': max(0, self.MAX_RESENDS - pv.resend_count),
            'can_resend': now - pv.last_resend >= self.RESEND_COOLDOWN,
            'resend_cooldown': max(0, int(self.RESEND_COOLDOWN - (now - pv.last_resend)))
        }


# Global instance
_verification_service: Optional[EmailVerificationService] = None


def get_verification_service() -> EmailVerificationService:
    """Get or create the global verification service instance."""
    global _verification_service
    if _verification_service is None:
        _verification_service = EmailVerificationService()
    return _verification_service
