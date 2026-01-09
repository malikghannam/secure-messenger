"""
Security Audit Logger

This module provides audit logging for security-critical operations in the
Production-Ready Secure Messenger. It logs cryptographic operations, 
authentication events, and security-relevant activities without exposing
sensitive data.

The audit logger ensures compliance with security monitoring requirements
while maintaining the confidentiality of cryptographic material.
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of security audit events."""
    # Authentication events
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    REGISTRATION = "registration"
    
    # Cryptographic events
    KEY_GENERATION = "key_generation"
    SESSION_INITIATION = "session_initiation"
    SESSION_RESPONSE = "session_response"
    MESSAGE_ENCRYPTION = "message_encryption"
    MESSAGE_DECRYPTION = "message_decryption"
    KEY_ROTATION = "key_rotation"
    
    # Security events
    BLINDNESS_VIOLATION = "blindness_violation"
    REPLAY_ATTACK_DETECTED = "replay_attack_detected"
    DECRYPTION_FAILURE = "decryption_failure"
    SIGNATURE_VERIFICATION_FAILURE = "signature_verification_failure"
    INVALID_MESSAGE_FORMAT = "invalid_message_format"
    
    # Storage events
    STATE_SAVE = "state_save"
    STATE_LOAD = "state_load"
    STATE_CORRUPTION_DETECTED = "state_corruption_detected"
    STATE_RECOVERY = "state_recovery"
    
    # Network events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    BUNDLE_UPLOADED = "bundle_uploaded"
    BUNDLE_RETRIEVED = "bundle_retrieved"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Represents a security audit event.
    
    Attributes:
        event_type: Type of audit event
        timestamp: When the event occurred
        username: User associated with the event (if applicable)
        peer: Peer involved in the event (if applicable)
        severity: Severity level of the event
        success: Whether the operation succeeded
        details: Additional event details (sanitized)
        event_id: Unique identifier for the event
    """
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    username: Optional[str] = None
    peer: Optional[str] = None
    severity: AuditSeverity = AuditSeverity.INFO
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        """Generate event ID if not provided."""
        if not self.event_id:
            # Generate deterministic event ID
            id_data = f"{self.event_type.value}:{self.timestamp.isoformat()}:{self.username}"
            self.event_id = hashlib.sha256(id_data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging/storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "username": self.username,
            "peer": self.peer,
            "severity": self.severity.value,
            "success": self.success,
            "details": self.details
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class SecurityAuditLogger:
    """
    Security audit logger for cryptographic and security operations.
    
    This logger records security-relevant events without exposing sensitive
    cryptographic material. It provides a complete audit trail for security
    analysis and compliance purposes.
    """
    
    # Fields that should never be logged
    SENSITIVE_FIELDS = {
        "password", "private_key", "secret", "key", "plaintext",
        "decrypted", "master_key", "session_key", "root_key",
        "chain_key", "message_key", "shared_secret"
    }
    
    def __init__(
        self, 
        log_file: Optional[Path] = None,
        max_events_in_memory: int = 1000
    ):
        """
        Initialize the security audit logger.
        
        Args:
            log_file: Optional path to audit log file
            max_events_in_memory: Maximum events to keep in memory
        """
        self._log_file = log_file
        self._max_events = max_events_in_memory
        self._events: List[AuditEvent] = []
        self._event_handlers: List[callable] = []
        
        # Statistics
        self._event_counts: Dict[str, int] = {}
        self._security_alerts: List[AuditEvent] = []
    
    def log_event(self, event: AuditEvent):
        """
        Log a security audit event.
        
        Args:
            event: The audit event to log
        """
        # Sanitize event details
        event.details = self._sanitize_details(event.details)
        
        # Store in memory
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)
        
        # Update statistics
        event_type = event.event_type.value
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1
        
        # Track security alerts
        if event.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            self._security_alerts.append(event)
        
        # Write to log file if configured
        if self._log_file:
            self._write_to_file(event)
        
        # Notify handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Audit event handler error: {e}")
        
        # Log to standard logger
        log_level = self._get_log_level(event.severity)
        logger.log(
            log_level,
            f"AUDIT: {event.event_type.value} - user={event.username} "
            f"peer={event.peer} success={event.success}"
        )
    
    def log_authentication(
        self, 
        event_type: AuditEventType,
        username: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an authentication event.
        
        Args:
            event_type: Type of authentication event
            username: Username involved
            success: Whether authentication succeeded
            details: Additional details (will be sanitized)
        """
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
        
        event = AuditEvent(
            event_type=event_type,
            username=username,
            severity=severity,
            success=success,
            details=details or {}
        )
        
        self.log_event(event)
    
    def log_cryptographic_operation(
        self,
        event_type: AuditEventType,
        username: str,
        peer: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a cryptographic operation.
        
        Args:
            event_type: Type of cryptographic event
            username: User performing the operation
            peer: Peer involved (if applicable)
            success: Whether operation succeeded
            details: Additional details (will be sanitized)
        """
        severity = AuditSeverity.INFO if success else AuditSeverity.ERROR
        
        event = AuditEvent(
            event_type=event_type,
            username=username,
            peer=peer,
            severity=severity,
            success=success,
            details=details or {}
        )
        
        self.log_event(event)
    
    def log_security_alert(
        self,
        event_type: AuditEventType,
        username: Optional[str] = None,
        peer: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a security alert.
        
        Args:
            event_type: Type of security event
            username: User involved (if applicable)
            peer: Peer involved (if applicable)
            details: Additional details (will be sanitized)
        """
        event = AuditEvent(
            event_type=event_type,
            username=username,
            peer=peer,
            severity=AuditSeverity.CRITICAL,
            success=False,
            details=details or {}
        )
        
        self.log_event(event)
    
    def log_network_event(
        self,
        event_type: AuditEventType,
        username: str,
        peer: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a network event.
        
        Args:
            event_type: Type of network event
            username: User involved
            peer: Peer involved (if applicable)
            success: Whether operation succeeded
            details: Additional details (will be sanitized)
        """
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
        
        event = AuditEvent(
            event_type=event_type,
            username=username,
            peer=peer,
            severity=severity,
            success=success,
            details=details or {}
        )
        
        self.log_event(event)
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize event details to remove sensitive information.
        
        Args:
            details: Raw event details
            
        Returns:
            Sanitized details safe for logging
        """
        sanitized = {}
        
        for key, value in details.items():
            # Check if key contains sensitive terms
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, str) and len(value) > 100:
                # Truncate long strings that might contain sensitive data
                sanitized[key] = f"{value[:20]}...[TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _write_to_file(self, event: AuditEvent):
        """Write event to audit log file."""
        try:
            with open(self._log_file, "a") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")
    
    def _get_log_level(self, severity: AuditSeverity) -> int:
        """Convert audit severity to logging level."""
        mapping = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.INFO)
    
    def register_event_handler(self, handler: callable):
        """
        Register a handler to be called for each audit event.
        
        Args:
            handler: Callable that receives AuditEvent objects
        """
        self._event_handlers.append(handler)
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        username: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit events.
        
        Args:
            event_type: Filter by event type
            username: Filter by username
            since: Filter events after this time
            limit: Maximum events to return
            
        Returns:
            List of matching audit events
        """
        results = []
        
        for event in reversed(self._events):
            if event_type and event.event_type != event_type:
                continue
            if username and event.username != username:
                continue
            if since and event.timestamp < since:
                continue
            
            results.append(event)
            if len(results) >= limit:
                break
        
        return results
    
    def get_security_alerts(self, limit: int = 50) -> List[AuditEvent]:
        """
        Get recent security alerts.
        
        Args:
            limit: Maximum alerts to return
            
        Returns:
            List of security alert events
        """
        return self._security_alerts[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit logging statistics.
        
        Returns:
            Dictionary with audit statistics
        """
        return {
            "total_events": len(self._events),
            "event_counts": self._event_counts.copy(),
            "security_alerts": len(self._security_alerts),
            "events_in_memory": len(self._events),
            "max_events": self._max_events
        }
    
    def clear_events(self):
        """Clear all events from memory (does not affect log file)."""
        self._events.clear()
        self._security_alerts.clear()
        self._event_counts.clear()