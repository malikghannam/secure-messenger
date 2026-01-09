"""Data models for secure file sharing with security policies."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


class PolicyType(Enum):
    """Security policy types for file sharing."""
    VIEW_ONCE = "view_once"
    TIME_LIMITED = "time_limited"
    VIEW_COUNT = "view_count"
    SCREENSHOT_BLOCKED = "screenshot_blocked"
    EXPIRY_DATE = "expiry_date"
    BURN_AFTER_READ = "burn_after_read"
    RECIPIENT_ONLY = "recipient_only"


@dataclass
class FilePolicy:
    """Security policy for a file."""
    policy_type: PolicyType
    created_at: datetime = field(default_factory=datetime.now)
    
    # Time Limited specific
    duration_seconds: Optional[int] = None  # 5, 10, 30, 60
    
    # View Count specific
    max_views: Optional[int] = None  # 1-10
    current_views: int = 0
    
    # Expiry Date specific
    expiry_date: Optional[datetime] = None
    
    # Screenshot Blocked specific
    screenshot_attempts: int = 0
    
    # Recipient Only specific
    recipient_public_key: Optional[bytes] = None
    
    def is_expired(self) -> bool:
        """Check if policy has expired."""
        if self.policy_type == PolicyType.EXPIRY_DATE and self.expiry_date:
            return datetime.now() > self.expiry_date
        if self.policy_type == PolicyType.VIEW_COUNT and self.max_views:
            return self.current_views >= self.max_views
        if self.policy_type == PolicyType.VIEW_ONCE and self.current_views > 0:
            return True
        if self.policy_type == PolicyType.BURN_AFTER_READ:
            if self.current_views > 0:
                return True
            if self.expiry_date and datetime.now() > self.expiry_date:
                return True
        return False

    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary for JSON serialization."""
        result = {
            'policy_type': self.policy_type.value,
            'created_at': self.created_at.isoformat(),
            'current_views': self.current_views,
            'screenshot_attempts': self.screenshot_attempts,
        }
        
        if self.duration_seconds is not None:
            result['duration_seconds'] = self.duration_seconds
        
        if self.max_views is not None:
            result['max_views'] = self.max_views
        
        if self.expiry_date is not None:
            result['expiry_date'] = self.expiry_date.isoformat()
        
        if self.recipient_public_key is not None:
            import base64
            result['recipient_public_key'] = base64.b64encode(self.recipient_public_key).decode('utf-8')
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilePolicy':
        """Create policy from dictionary."""
        policy_type = PolicyType(data['policy_type'])
        created_at = datetime.fromisoformat(data['created_at'])
        
        kwargs = {
            'policy_type': policy_type,
            'created_at': created_at,
            'current_views': data.get('current_views', 0),
            'screenshot_attempts': data.get('screenshot_attempts', 0),
        }
        
        if 'duration_seconds' in data:
            kwargs['duration_seconds'] = data['duration_seconds']
        
        if 'max_views' in data:
            kwargs['max_views'] = data['max_views']
        
        if 'expiry_date' in data:
            kwargs['expiry_date'] = datetime.fromisoformat(data['expiry_date'])
        
        if 'recipient_public_key' in data:
            import base64
            kwargs['recipient_public_key'] = base64.b64decode(data['recipient_public_key'])
        
        return cls(**kwargs)



@dataclass
class SecureFile:
    """Encrypted file with metadata."""
    file_id: str
    filename: str
    file_type: str
    file_size: int
    encrypted_content: bytes
    encrypted_key: bytes
    policies: List[FilePolicy]
    sender: str
    recipient: str
    created_at: datetime = field(default_factory=datetime.now)
    
    # Tracking
    first_viewed_at: Optional[datetime] = None
    last_viewed_at: Optional[datetime] = None
    view_count: int = 0
    is_deleted: bool = False


@dataclass
class SecureFileResult:
    """Result of file upload operation."""
    success: bool
    file_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SecureFileContent:
    """Decrypted file content with policies."""
    file_id: str
    filename: str
    file_type: str
    content: bytes
    policies: List[FilePolicy]
    sender: str


@dataclass
class FileValidationResult:
    """Result of file validation."""
    is_valid: bool
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None
