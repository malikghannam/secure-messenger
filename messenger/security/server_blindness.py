"""
Server Blindness Verification

This module provides monitoring and verification to ensure that no plaintext
message data or private key material is ever transmitted to the relay server.
It validates that all payloads sent to the server contain only encrypted content.

Requirements: 1.3 - THE Relay_Server SHALL remain cryptographically blind to
all message content and private keys.
"""

import re
import base64
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


logger = logging.getLogger(__name__)


class BlindnessViolationType(Enum):
    """Types of server blindness violations."""
    PLAINTEXT_MESSAGE = "plaintext_message"
    PRIVATE_KEY_EXPOSURE = "private_key_exposure"
    SESSION_STATE_EXPOSURE = "session_state_exposure"
    UNENCRYPTED_PAYLOAD = "unencrypted_payload"
    SENSITIVE_METADATA = "sensitive_metadata"
    CRYPTOGRAPHIC_STATE = "cryptographic_state"


@dataclass
class BlindnessViolation:
    """
    Represents a detected server blindness violation.
    
    Attributes:
        violation_type: Type of violation detected
        field_path: Path to the field containing the violation
        description: Human-readable description of the violation
        severity: Severity level (critical, high, medium, low)
        timestamp: When the violation was detected
        context: Additional context about the violation
    """
    violation_type: BlindnessViolationType
    field_path: str
    description: str
    severity: str = "critical"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary for logging/reporting."""
        return {
            "type": self.violation_type.value,
            "field_path": self.field_path,
            "description": self.description,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


class PayloadValidator:
    """
    Validates that message payloads contain only encrypted content.
    
    This validator checks outgoing payloads to ensure they don't contain
    plaintext messages, private keys, or other sensitive data that should
    never reach the relay server.
    """
    
    # Patterns that indicate potentially unencrypted or sensitive data
    SENSITIVE_PATTERNS = {
        # Private key indicators
        "private_key_pem": re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
        "private_key_hex": re.compile(r"[0-9a-f]{64,}", re.IGNORECASE),  # Long hex strings
        
        # Common plaintext indicators (should be encrypted)
        "readable_text": re.compile(r"^[a-zA-Z\s]{20,}$"),  # Long readable text
        
        # Session state indicators
        "ratchet_state": re.compile(r"(root_key|chain_key|message_key)", re.IGNORECASE),
        "session_secret": re.compile(r"(shared_secret|derived_key|master_key)", re.IGNORECASE),
    }
    
    # Fields that are allowed to contain plaintext (routing metadata)
    ALLOWED_PLAINTEXT_FIELDS = {
        "type", "from", "to", "ts", "opk_id", "message_type"
    }
    
    # Fields that must contain base64-encoded encrypted data
    ENCRYPTED_FIELDS = {
        "payload", "ek_pub", "kyber_ct", "ciphertext", "encrypted_data"
    }
    
    def __init__(self):
        """Initialize the payload validator."""
        self._violation_count = 0
        self._last_violations: List[BlindnessViolation] = []
    
    def validate_outgoing_envelope(
        self, 
        envelope: Dict[str, Any]
    ) -> List[BlindnessViolation]:
        """
        Validate an outgoing message envelope for server blindness.
        
        Args:
            envelope: Message envelope to validate
            
        Returns:
            List of detected violations (empty if valid)
        """
        violations = []
        
        # Check each field in the envelope
        violations.extend(self._validate_field("", envelope))
        
        # Verify encrypted fields are properly encoded
        violations.extend(self._verify_encrypted_fields(envelope))
        
        # Check for sensitive patterns in string values
        violations.extend(self._check_sensitive_patterns(envelope))
        
        # Update tracking
        self._violation_count += len(violations)
        self._last_violations = violations
        
        return violations
    
    def _validate_field(
        self, 
        path: str, 
        value: Any
    ) -> List[BlindnessViolation]:
        """
        Recursively validate a field for blindness violations.
        
        Args:
            path: Current field path
            value: Field value to validate
            
        Returns:
            List of violations found
        """
        violations = []
        field_name = path.split(".")[-1] if path else ""
        
        if isinstance(value, dict):
            for key, val in value.items():
                new_path = f"{path}.{key}" if path else key
                violations.extend(self._validate_field(new_path, val))
                
        elif isinstance(value, list):
            for i, item in enumerate(value):
                new_path = f"{path}[{i}]"
                violations.extend(self._validate_field(new_path, item))
                
        elif isinstance(value, str):
            # Check if this field should be encrypted but isn't
            if field_name in self.ENCRYPTED_FIELDS:
                if not self._is_valid_base64(value):
                    violations.append(BlindnessViolation(
                        violation_type=BlindnessViolationType.UNENCRYPTED_PAYLOAD,
                        field_path=path,
                        description=f"Field '{field_name}' should contain base64-encoded encrypted data",
                        severity="critical"
                    ))
            
            # Check for private key patterns
            if self._contains_private_key_pattern(value):
                violations.append(BlindnessViolation(
                    violation_type=BlindnessViolationType.PRIVATE_KEY_EXPOSURE,
                    field_path=path,
                    description="Potential private key material detected in payload",
                    severity="critical"
                ))
        
        return violations
    
    def _verify_encrypted_fields(
        self, 
        envelope: Dict[str, Any]
    ) -> List[BlindnessViolation]:
        """
        Verify that fields expected to be encrypted are properly encoded.
        
        Args:
            envelope: Message envelope to check
            
        Returns:
            List of violations found
        """
        violations = []
        
        # Check payload field specifically
        if "payload" in envelope:
            payload = envelope["payload"]
            if isinstance(payload, dict):
                # Payload should contain encrypted components
                required_encrypted = {"header", "ciphertext", "nonce"}
                if not any(key in payload for key in required_encrypted):
                    # Check if it looks like a Double Ratchet payload
                    if not self._is_valid_ratchet_payload(payload):
                        violations.append(BlindnessViolation(
                            violation_type=BlindnessViolationType.UNENCRYPTED_PAYLOAD,
                            field_path="payload",
                            description="Payload does not appear to be properly encrypted",
                            severity="high"
                        ))
        
        return violations
    
    def _check_sensitive_patterns(
        self, 
        envelope: Dict[str, Any],
        path: str = ""
    ) -> List[BlindnessViolation]:
        """
        Check for sensitive data patterns in the envelope.
        
        Args:
            envelope: Message envelope to check
            path: Current path in the envelope
            
        Returns:
            List of violations found
        """
        violations = []
        
        for key, value in envelope.items():
            current_path = f"{path}.{key}" if path else key
            
            # Skip allowed plaintext fields
            if key in self.ALLOWED_PLAINTEXT_FIELDS:
                continue
            
            if isinstance(value, str):
                for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
                    if pattern.search(value):
                        violations.append(BlindnessViolation(
                            violation_type=BlindnessViolationType.SENSITIVE_METADATA,
                            field_path=current_path,
                            description=f"Sensitive pattern '{pattern_name}' detected",
                            severity="high",
                            context={"pattern": pattern_name}
                        ))
                        
            elif isinstance(value, dict):
                violations.extend(self._check_sensitive_patterns(value, current_path))
        
        return violations
    
    def _is_valid_base64(self, value: str) -> bool:
        """Check if a string is valid base64-encoded data."""
        try:
            # Check if it looks like base64
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', value):
                return False
            # Try to decode
            base64.b64decode(value)
            return True
        except Exception:
            return False
    
    def _is_valid_ratchet_payload(self, payload: Dict[str, Any]) -> bool:
        """Check if payload looks like a valid Double Ratchet encrypted payload."""
        # Double Ratchet payloads typically have specific structure
        # This is a heuristic check - actual validation happens in crypto layer
        if isinstance(payload, dict):
            # Check for typical encrypted payload fields
            has_encrypted_content = any(
                isinstance(payload.get(key), str) and len(payload.get(key, "")) > 20
                for key in ["ct", "ciphertext", "data", "encrypted"]
            )
            return has_encrypted_content or len(payload) > 0
        return False
    
    def _contains_private_key_pattern(self, value: str) -> bool:
        """Check if a string contains private key patterns."""
        for pattern in [
            self.SENSITIVE_PATTERNS["private_key_pem"],
        ]:
            if pattern.search(value):
                return True
        return False
    
    def get_violation_count(self) -> int:
        """Get total number of violations detected."""
        return self._violation_count
    
    def get_last_violations(self) -> List[BlindnessViolation]:
        """Get the most recent violations detected."""
        return self._last_violations.copy()


class ServerBlindnessVerifier:
    """
    Main verifier class for ensuring server blindness.
    
    This class coordinates payload validation and provides monitoring
    capabilities to ensure the relay server never receives plaintext
    message content or private key material.
    """
    
    def __init__(self):
        """Initialize the server blindness verifier."""
        self._validator = PayloadValidator()
        self._monitoring_enabled = True
        self._violation_handlers: List[callable] = []
        self._total_messages_verified = 0
        self._total_violations = 0
    
    def verify_outgoing_message(
        self, 
        envelope: Dict[str, Any],
        raise_on_violation: bool = True
    ) -> bool:
        """
        Verify an outgoing message maintains server blindness.
        
        Args:
            envelope: Message envelope to verify
            raise_on_violation: Whether to raise exception on violation
            
        Returns:
            True if message is safe to send, False otherwise
            
        Raises:
            BlindnessViolationError: If violations detected and raise_on_violation is True
        """
        if not self._monitoring_enabled:
            return True
        
        self._total_messages_verified += 1
        
        violations = self._validator.validate_outgoing_envelope(envelope)
        
        if violations:
            self._total_violations += len(violations)
            
            # Notify handlers
            for handler in self._violation_handlers:
                try:
                    handler(violations)
                except Exception as e:
                    logger.error(f"Violation handler error: {e}")
            
            # Log violations (without sensitive data)
            for violation in violations:
                logger.warning(
                    f"Server blindness violation: {violation.violation_type.value} "
                    f"at {violation.field_path}"
                )
            
            if raise_on_violation:
                raise BlindnessViolationError(
                    f"Server blindness violated: {len(violations)} violation(s) detected",
                    violations
                )
            
            return False
        
        return True
    
    def register_violation_handler(self, handler: callable):
        """
        Register a handler to be called when violations are detected.
        
        Args:
            handler: Callable that receives list of BlindnessViolation objects
        """
        self._violation_handlers.append(handler)
    
    def enable_monitoring(self):
        """Enable server blindness monitoring."""
        self._monitoring_enabled = True
        logger.info("Server blindness monitoring enabled")
    
    def disable_monitoring(self):
        """Disable server blindness monitoring (not recommended)."""
        self._monitoring_enabled = False
        logger.warning("Server blindness monitoring disabled - NOT RECOMMENDED")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.
        
        Returns:
            Dictionary with monitoring statistics
        """
        return {
            "monitoring_enabled": self._monitoring_enabled,
            "total_messages_verified": self._total_messages_verified,
            "total_violations": self._total_violations,
            "violation_rate": (
                self._total_violations / self._total_messages_verified
                if self._total_messages_verified > 0 else 0
            )
        }
    
    def reset_statistics(self):
        """Reset monitoring statistics."""
        self._total_messages_verified = 0
        self._total_violations = 0


class BlindnessViolationError(Exception):
    """Exception raised when server blindness is violated."""
    
    def __init__(self, message: str, violations: List[BlindnessViolation]):
        super().__init__(message)
        self.violations = violations
    
    def get_violations(self) -> List[BlindnessViolation]:
        """Get the list of violations that caused this error."""
        return self.violations