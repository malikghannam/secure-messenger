"""
Payload Inspector

This module provides tools for inspecting and validating encrypted payloads
to ensure they conform to expected formats and don't contain plaintext data.
It supports verification of message envelopes before transmission to the
relay server.

This is a verification tool for development and security auditing purposes.
"""

import re
import base64
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class InspectionResultType(Enum):
    """Types of inspection results."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SensitiveDataPattern:
    """
    Pattern for detecting sensitive data in payloads.
    
    Attributes:
        name: Name of the pattern
        pattern: Regex pattern to match
        description: Description of what this pattern detects
        severity: Severity if pattern is found
    """
    name: str
    pattern: str
    description: str
    severity: InspectionResultType = InspectionResultType.WARNING
    
    def matches(self, value: str) -> bool:
        """Check if the pattern matches the given value."""
        return bool(re.search(self.pattern, value, re.IGNORECASE))


@dataclass
class InspectionResult:
    """
    Result of a payload inspection.
    
    Attributes:
        result_type: Type of result (valid, warning, error, critical)
        field_path: Path to the inspected field
        message: Description of the finding
        pattern_name: Name of pattern that matched (if applicable)
        timestamp: When the inspection was performed
    """
    result_type: InspectionResultType
    field_path: str
    message: str
    pattern_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "result_type": self.result_type.value,
            "field_path": self.field_path,
            "message": self.message,
            "pattern_name": self.pattern_name,
            "timestamp": self.timestamp.isoformat()
        }


class PayloadInspector:
    """
    Inspector for validating encrypted message payloads.
    
    This class provides comprehensive inspection of message envelopes to
    ensure they contain only properly encrypted data and don't leak
    sensitive information to the relay server.
    """
    
    # Default patterns for detecting sensitive data
    DEFAULT_PATTERNS = [
        SensitiveDataPattern(
            name="private_key_pem",
            pattern=r"-----BEGIN\s+(RSA\s+|EC\s+)?PRIVATE\s+KEY-----",
            description="PEM-encoded private key detected",
            severity=InspectionResultType.CRITICAL
        ),
        SensitiveDataPattern(
            name="private_key_marker",
            pattern=r"(priv_key|private_key|privateKey|privKey)",
            description="Private key field name detected",
            severity=InspectionResultType.CRITICAL
        ),
        SensitiveDataPattern(
            name="session_secret",
            pattern=r"(shared_secret|sharedSecret|session_key|sessionKey)",
            description="Session secret field name detected",
            severity=InspectionResultType.CRITICAL
        ),
        SensitiveDataPattern(
            name="ratchet_state",
            pattern=r"(root_key|rootKey|chain_key|chainKey|message_key|messageKey)",
            description="Ratchet state field name detected",
            severity=InspectionResultType.CRITICAL
        ),
        SensitiveDataPattern(
            name="plaintext_marker",
            pattern=r"(plaintext|decrypted|cleartext)",
            description="Plaintext field name detected",
            severity=InspectionResultType.ERROR
        ),
        SensitiveDataPattern(
            name="password_field",
            pattern=r"(password|passwd|pwd)[\"\']?\s*[:=]",
            description="Password field detected",
            severity=InspectionResultType.CRITICAL
        ),
        SensitiveDataPattern(
            name="long_readable_text",
            pattern=r"^[A-Za-z\s,\.!?]{50,}$",
            description="Long readable text (possible plaintext message)",
            severity=InspectionResultType.WARNING
        ),
    ]
    
    # Expected structure for encrypted message envelopes
    EXPECTED_ENVELOPE_FIELDS = {
        "type": {"required": True, "allowed_values": ["prekey", "msg"]},
        "from": {"required": True, "type": str},
        "to": {"required": True, "type": str},
        "ts": {"required": True, "type": str},
        "payload": {"required": True, "type": dict},
    }
    
    PREKEY_ADDITIONAL_FIELDS = {
        "ek_pub": {"required": True, "type": str, "base64": True},
        "kyber_ct": {"required": True, "type": str, "base64": True},
        "opk_id": {"required": False, "type": int},
        "from_ik_pub": {"required": True, "type": str, "base64": True},
    }
    
    def __init__(self, custom_patterns: Optional[List[SensitiveDataPattern]] = None):
        """
        Initialize the payload inspector.
        
        Args:
            custom_patterns: Additional patterns to check for
        """
        self._patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self._patterns.extend(custom_patterns)
        
        self._inspection_count = 0
        self._findings: List[InspectionResult] = []
    
    def inspect_envelope(
        self, 
        envelope: Dict[str, Any]
    ) -> List[InspectionResult]:
        """
        Perform comprehensive inspection of a message envelope.
        
        Args:
            envelope: Message envelope to inspect
            
        Returns:
            List of inspection results
        """
        self._inspection_count += 1
        results = []
        
        # Check envelope structure
        results.extend(self._check_envelope_structure(envelope))
        
        # Check for sensitive patterns
        results.extend(self._check_sensitive_patterns(envelope))
        
        # Validate encrypted fields
        results.extend(self._validate_encrypted_fields(envelope))
        
        # Check payload structure
        if "payload" in envelope:
            results.extend(self._inspect_payload(envelope["payload"]))
        
        # Store findings
        self._findings.extend(results)
        
        return results
    
    def _check_envelope_structure(
        self, 
        envelope: Dict[str, Any]
    ) -> List[InspectionResult]:
        """Check that envelope has expected structure."""
        results = []
        
        # Check required fields
        for field_name, spec in self.EXPECTED_ENVELOPE_FIELDS.items():
            if spec.get("required") and field_name not in envelope:
                results.append(InspectionResult(
                    result_type=InspectionResultType.ERROR,
                    field_path=field_name,
                    message=f"Required field '{field_name}' is missing"
                ))
            elif field_name in envelope:
                value = envelope[field_name]
                expected_type = spec.get("type")
                if expected_type and not isinstance(value, expected_type):
                    results.append(InspectionResult(
                        result_type=InspectionResultType.WARNING,
                        field_path=field_name,
                        message=f"Field '{field_name}' has unexpected type"
                    ))
                
                # Check allowed values
                allowed = spec.get("allowed_values")
                if allowed and value not in allowed:
                    results.append(InspectionResult(
                        result_type=InspectionResultType.WARNING,
                        field_path=field_name,
                        message=f"Field '{field_name}' has unexpected value"
                    ))
        
        # Check prekey-specific fields
        if envelope.get("type") == "prekey":
            for field_name, spec in self.PREKEY_ADDITIONAL_FIELDS.items():
                if spec.get("required") and field_name not in envelope:
                    results.append(InspectionResult(
                        result_type=InspectionResultType.ERROR,
                        field_path=field_name,
                        message=f"Required prekey field '{field_name}' is missing"
                    ))
        
        return results
    
    def _check_sensitive_patterns(
        self, 
        data: Any,
        path: str = ""
    ) -> List[InspectionResult]:
        """Recursively check for sensitive data patterns."""
        results = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check key name for sensitive patterns
                for pattern in self._patterns:
                    if pattern.matches(key):
                        results.append(InspectionResult(
                            result_type=pattern.severity,
                            field_path=current_path,
                            message=pattern.description,
                            pattern_name=pattern.name
                        ))
                
                # Recursively check value
                results.extend(self._check_sensitive_patterns(value, current_path))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                results.extend(self._check_sensitive_patterns(item, current_path))
                
        elif isinstance(data, str):
            # Check string value for sensitive patterns
            for pattern in self._patterns:
                if pattern.matches(data):
                    results.append(InspectionResult(
                        result_type=pattern.severity,
                        field_path=path,
                        message=f"Value matches sensitive pattern: {pattern.description}",
                        pattern_name=pattern.name
                    ))
        
        return results
    
    def _validate_encrypted_fields(
        self, 
        envelope: Dict[str, Any]
    ) -> List[InspectionResult]:
        """Validate that encrypted fields contain valid base64 data."""
        results = []
        
        encrypted_fields = ["ek_pub", "kyber_ct", "from_ik_pub"]
        
        for field_name in encrypted_fields:
            if field_name in envelope:
                value = envelope[field_name]
                if isinstance(value, str):
                    if not self._is_valid_base64(value):
                        results.append(InspectionResult(
                            result_type=InspectionResultType.ERROR,
                            field_path=field_name,
                            message=f"Field '{field_name}' is not valid base64"
                        ))
                    elif len(value) < 10:
                        results.append(InspectionResult(
                            result_type=InspectionResultType.WARNING,
                            field_path=field_name,
                            message=f"Field '{field_name}' seems too short for encrypted data"
                        ))
        
        return results
    
    def _inspect_payload(
        self, 
        payload: Dict[str, Any]
    ) -> List[InspectionResult]:
        """Inspect the encrypted payload structure."""
        results = []
        
        # Payload should contain encrypted data, not plaintext
        if isinstance(payload, dict):
            # Check for expected encrypted payload structure
            # Double Ratchet payloads typically have specific fields
            has_encrypted_structure = any(
                key in payload for key in ["ct", "ciphertext", "header", "nonce", "tag"]
            )
            
            if not has_encrypted_structure and payload:
                # Check if payload looks like it might be plaintext
                for key, value in payload.items():
                    if isinstance(value, str) and len(value) > 20:
                        if not self._is_valid_base64(value):
                            results.append(InspectionResult(
                                result_type=InspectionResultType.WARNING,
                                field_path=f"payload.{key}",
                                message="Payload field may contain non-encrypted data"
                            ))
        
        return results
    
    def _is_valid_base64(self, value: str) -> bool:
        """Check if a string is valid base64."""
        try:
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', value):
                return False
            base64.b64decode(value)
            return True
        except Exception:
            return False
    
    def add_pattern(self, pattern: SensitiveDataPattern):
        """
        Add a custom pattern to check for.
        
        Args:
            pattern: Pattern to add
        """
        self._patterns.append(pattern)
    
    def remove_pattern(self, pattern_name: str) -> bool:
        """
        Remove a pattern by name.
        
        Args:
            pattern_name: Name of pattern to remove
            
        Returns:
            True if pattern was removed
        """
        for i, pattern in enumerate(self._patterns):
            if pattern.name == pattern_name:
                self._patterns.pop(i)
                return True
        return False
    
    def get_patterns(self) -> List[SensitiveDataPattern]:
        """Get all registered patterns."""
        return self._patterns.copy()
    
    def get_findings(
        self, 
        severity: Optional[InspectionResultType] = None
    ) -> List[InspectionResult]:
        """
        Get inspection findings.
        
        Args:
            severity: Filter by severity level
            
        Returns:
            List of inspection results
        """
        if severity:
            return [f for f in self._findings if f.result_type == severity]
        return self._findings.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get inspection statistics."""
        severity_counts = {}
        for finding in self._findings:
            severity = finding.result_type.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_inspections": self._inspection_count,
            "total_findings": len(self._findings),
            "findings_by_severity": severity_counts,
            "patterns_registered": len(self._patterns)
        }
    
    def clear_findings(self):
        """Clear all stored findings."""
        self._findings.clear()
    
    def generate_report(self) -> str:
        """
        Generate a human-readable inspection report.
        
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "PAYLOAD INSPECTION REPORT",
            "=" * 60,
            f"Total Inspections: {self._inspection_count}",
            f"Total Findings: {len(self._findings)}",
            ""
        ]
        
        # Group findings by severity
        by_severity = {}
        for finding in self._findings:
            severity = finding.result_type.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(finding)
        
        for severity in ["critical", "error", "warning", "valid"]:
            if severity in by_severity:
                lines.append(f"\n{severity.upper()} ({len(by_severity[severity])}):")
                lines.append("-" * 40)
                for finding in by_severity[severity][:10]:  # Limit to 10 per severity
                    lines.append(f"  [{finding.field_path}] {finding.message}")
                if len(by_severity[severity]) > 10:
                    lines.append(f"  ... and {len(by_severity[severity]) - 10} more")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)