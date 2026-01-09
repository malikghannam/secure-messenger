"""
Secure Logger

Provides secure logging that never exposes sensitive information like
private keys, plaintexts, passwords, or internal cryptographic state.
"""

import logging
import json
import re
from typing import Any, Dict, Optional, Union
from datetime import datetime
import hashlib


class SecureLogger:
    """
    Secure logger that sanitizes sensitive information before logging.
    
    This logger ensures that no cryptographic material, user data, or
    other sensitive information is ever written to log files.
    """
    
    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = [
        # Cryptographic keys and material
        r'(?i)(private|secret|key|token|password|pass|pwd)',
        r'(?i)(ik_priv|spk_priv|kyber_priv|opk_priv)',
        r'(?i)(session_key|root_key|chain_key|message_key)',
        
        # Base64 encoded data (likely crypto material)
        r'[A-Za-z0-9+/]{32,}={0,2}',
        
        # Hex encoded data (likely crypto material)
        r'[0-9a-fA-F]{32,}',
        
        # User content that might be sensitive
        r'(?i)(plaintext|message|text|content)',
        
        # Authentication data
        r'(?i)(auth|login|credential|bearer)',
    ]
    
    # Fields that should always be redacted
    SENSITIVE_FIELDS = {
        'password', 'pass', 'pwd', 'secret', 'token', 'key',
        'private_key', 'public_key', 'ik_priv', 'ik_pub',
        'spk_priv', 'spk_pub', 'kyber_priv', 'kyber_pub',
        'opk_priv', 'opk_pub', 'session_key', 'root_key',
        'chain_key', 'message_key', 'plaintext', 'ciphertext',
        'payload', 'envelope', 'bundle', 'auth_token',
        'bearer_token', 'credentials', 'user_data'
    }
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize secure logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create formatter that includes timestamp and level
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _sanitize_value(self, value: Any) -> Any:
        """
        Sanitize a value to remove sensitive information.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value safe for logging
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            return self._sanitize_string(value)
        
        elif isinstance(value, dict):
            return self._sanitize_dict(value)
        
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        
        elif isinstance(value, bytes):
            # Never log raw bytes - could be crypto material
            return f"<bytes:{len(value)}>"
        
        else:
            # For other types, convert to string and sanitize
            return self._sanitize_string(str(value))
    
    def _sanitize_string(self, text: str) -> str:
        """
        Sanitize a string to remove sensitive patterns.
        
        Args:
            text: String to sanitize
            
        Returns:
            Sanitized string
        """
        if not text:
            return text
        
        # Check for sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                # If it looks sensitive, hash it for debugging purposes
                hash_value = hashlib.sha256(text.encode()).hexdigest()[:8]
                return f"<redacted:hash:{hash_value}>"
        
        # Limit length to prevent log spam
        if len(text) > 200:
            return text[:200] + "...<truncated>"
        
        return text
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a dictionary to remove sensitive fields.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if field name indicates sensitive data
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                # Redact sensitive fields but keep type info
                if isinstance(value, str):
                    sanitized[key] = f"<redacted:str:{len(value)}>"
                elif isinstance(value, bytes):
                    sanitized[key] = f"<redacted:bytes:{len(value)}>"
                elif isinstance(value, dict):
                    sanitized[key] = f"<redacted:dict:{len(value)}>"
                else:
                    sanitized[key] = f"<redacted:{type(value).__name__}>"
            else:
                # Recursively sanitize non-sensitive fields
                sanitized[key] = self._sanitize_value(value)
        
        return sanitized
    
    def _format_message(self, message: str, *args, **kwargs) -> str:
        """
        Format log message with sanitized arguments.
        
        Args:
            message: Log message format string
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Formatted and sanitized message
        """
        # Sanitize all arguments
        sanitized_args = [self._sanitize_value(arg) for arg in args]
        sanitized_kwargs = self._sanitize_dict(kwargs)
        
        try:
            return message.format(*sanitized_args, **sanitized_kwargs)
        except (KeyError, ValueError, IndexError):
            # If formatting fails, log the message safely
            return f"{message} (formatting failed - args sanitized)"
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with sanitization."""
        if self.logger.isEnabledFor(logging.DEBUG):
            sanitized_msg = self._format_message(message, *args, **kwargs)
            self.logger.debug(sanitized_msg)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with sanitization."""
        if self.logger.isEnabledFor(logging.INFO):
            sanitized_msg = self._format_message(message, *args, **kwargs)
            self.logger.info(sanitized_msg)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with sanitization."""
        if self.logger.isEnabledFor(logging.WARNING):
            sanitized_msg = self._format_message(message, *args, **kwargs)
            self.logger.warning(sanitized_msg)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with sanitization."""
        if self.logger.isEnabledFor(logging.ERROR):
            sanitized_msg = self._format_message(message, *args, **kwargs)
            self.logger.error(sanitized_msg)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with sanitization."""
        if self.logger.isEnabledFor(logging.CRITICAL):
            sanitized_msg = self._format_message(message, *args, **kwargs)
            self.logger.critical(sanitized_msg)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an error with secure sanitization.
        
        Args:
            error: Exception to log
            context: Additional context (will be sanitized)
        """
        from .error_categories import MessengerError
        
        if isinstance(error, MessengerError):
            # Use the error's secure logging method
            error_data = error.get_secure_log_data()
            if context:
                error_data.update(self._sanitize_dict(context))
            
            self.error(
                "MessengerError occurred: {error_type} - {error_code}",
                error_type=error_data.get('error_type'),
                error_code=error_data.get('error_code')
            )
        else:
            # Generic exception - sanitize carefully
            sanitized_context = self._sanitize_dict(context) if context else {}
            self.error(
                "Exception occurred: {exception_type} - {message}",
                exception_type=type(error).__name__,
                message=self._sanitize_string(str(error))
            )
    
    def log_security_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """
        Log a security-related event.
        
        Args:
            event_type: Type of security event
            details: Event details (will be sanitized)
        """
        sanitized_details = self._sanitize_dict(details) if details else {}
        self.warning(
            "Security event: {event_type} - {timestamp}",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat()
        )
        
        if sanitized_details:
            self.debug("Security event details: {details}", details=sanitized_details)


# Global secure logger instance
secure_logger = SecureLogger("messenger.secure")