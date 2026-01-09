"""Policy engine for managing and enforcing security policies on files."""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from messenger.files.models import PolicyType, FilePolicy


@dataclass
class PolicyValidationResult:
    """Result of policy validation."""
    is_valid: bool
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


@dataclass
class AccessCheckResult:
    """Result of access check."""
    allowed: bool
    reason: Optional[str] = None


@dataclass
class ViewRecordResult:
    """Result of recording a view."""
    remaining_views: Optional[int] = None
    should_delete: bool = False


# Valid duration values for TIME_LIMITED policy
VALID_DURATIONS = [5, 10, 30, 60]

# Valid view count range
MIN_VIEW_COUNT = 1
MAX_VIEW_COUNT = 10


class PolicyEngine:
    """Engine for managing and enforcing security policies."""
    
    def __init__(self):
        """Initialize the policy engine."""
        self._file_policies: Dict[str, List[FilePolicy]] = {}
        self._view_counts: Dict[str, int] = {}
    
    def create_policy(self, policy_type: PolicyType, **params) -> FilePolicy:
        """
        Create a new security policy.
        
        Args:
            policy_type: Type of policy
            **params: Policy-specific parameters
            
        Returns:
            FilePolicy object
            
        Raises:
            ValueError: If parameters are invalid
        """
        kwargs = {
            'policy_type': policy_type,
            'created_at': datetime.now()
        }
        
        if policy_type == PolicyType.VIEW_ONCE:
            # No additional parameters needed
            pass
            
        elif policy_type == PolicyType.TIME_LIMITED:
            duration = params.get('duration_seconds')
            if duration not in VALID_DURATIONS:
                raise ValueError(f"مدة العرض يجب أن تكون {VALID_DURATIONS}")
            kwargs['duration_seconds'] = duration
            
        elif policy_type == PolicyType.VIEW_COUNT:
            max_views = params.get('max_views')
            if not isinstance(max_views, int) or not (MIN_VIEW_COUNT <= max_views <= MAX_VIEW_COUNT):
                raise ValueError(f"عدد المشاهدات يجب أن يكون بين {MIN_VIEW_COUNT} و {MAX_VIEW_COUNT}")
            kwargs['max_views'] = max_views
            
        elif policy_type == PolicyType.SCREENSHOT_BLOCKED:
            # No additional parameters needed
            pass

        elif policy_type == PolicyType.EXPIRY_DATE:
            expiry_date = params.get('expiry_date')
            if not isinstance(expiry_date, datetime):
                raise ValueError("تاريخ الانتهاء يجب أن يكون من نوع datetime")
            if expiry_date <= datetime.now():
                raise ValueError("تاريخ الانتهاء يجب أن يكون في المستقبل")
            kwargs['expiry_date'] = expiry_date
            
        elif policy_type == PolicyType.BURN_AFTER_READ:
            # Combines VIEW_ONCE with optional TIME_LIMITED
            duration = params.get('duration_seconds')
            if duration is not None and duration not in VALID_DURATIONS:
                raise ValueError(f"مدة العرض يجب أن تكون {VALID_DURATIONS}")
            if duration:
                kwargs['duration_seconds'] = duration
            # Also set expiry based on duration if provided
            if duration:
                kwargs['expiry_date'] = datetime.now() + timedelta(seconds=duration)
                
        elif policy_type == PolicyType.RECIPIENT_ONLY:
            recipient_key = params.get('recipient_public_key')
            if not isinstance(recipient_key, bytes):
                raise ValueError("مفتاح المستلم يجب أن يكون من نوع bytes")
            kwargs['recipient_public_key'] = recipient_key
        
        return FilePolicy(**kwargs)
    
    def validate_policies(self, policies: List[FilePolicy]) -> PolicyValidationResult:
        """
        Validate policy compatibility.
        
        Args:
            policies: List of policies to validate
            
        Returns:
            PolicyValidationResult with is_valid and conflicts
        """
        conflicts = []
        policy_types = [p.policy_type for p in policies]
        
        # Check VIEW_ONCE and VIEW_COUNT conflict
        if PolicyType.VIEW_ONCE in policy_types and PolicyType.VIEW_COUNT in policy_types:
            conflicts.append("VIEW_ONCE و VIEW_COUNT غير متوافقين - كلاهما يتحكم بعدد المشاهدات")
        
        # Check multiple TIME_LIMITED policies
        time_limited_count = policy_types.count(PolicyType.TIME_LIMITED)
        if time_limited_count > 1:
            conflicts.append("لا يمكن تطبيق أكثر من سياسة TIME_LIMITED واحدة")
        
        # Check BURN_AFTER_READ with VIEW_ONCE (redundant)
        if PolicyType.BURN_AFTER_READ in policy_types and PolicyType.VIEW_ONCE in policy_types:
            conflicts.append("BURN_AFTER_READ يتضمن VIEW_ONCE بالفعل")
        
        # Check BURN_AFTER_READ with VIEW_COUNT
        if PolicyType.BURN_AFTER_READ in policy_types and PolicyType.VIEW_COUNT in policy_types:
            conflicts.append("BURN_AFTER_READ و VIEW_COUNT غير متوافقين")
        
        return PolicyValidationResult(
            is_valid=len(conflicts) == 0,
            conflicts=conflicts
        )

    
    def check_access(self, file_id: str, policies: List[FilePolicy]) -> AccessCheckResult:
        """
        Check if file access is allowed based on policies.
        
        Args:
            file_id: File identifier
            policies: List of policies to check
            
        Returns:
            AccessCheckResult with allowed and reason
        """
        for policy in policies:
            # Check expiry date
            if policy.policy_type == PolicyType.EXPIRY_DATE:
                if policy.is_expired():
                    return AccessCheckResult(
                        allowed=False,
                        reason="انتهت صلاحية هذا الملف"
                    )
            
            # Check view count
            if policy.policy_type == PolicyType.VIEW_COUNT:
                if policy.is_expired():
                    return AccessCheckResult(
                        allowed=False,
                        reason="تم الوصول للحد الأقصى من المشاهدات"
                    )
            
            # Check view once
            if policy.policy_type == PolicyType.VIEW_ONCE:
                if policy.current_views > 0:
                    return AccessCheckResult(
                        allowed=False,
                        reason="هذا الملف للعرض مرة واحدة فقط وقد تم عرضه"
                    )
            
            # Check burn after read
            if policy.policy_type == PolicyType.BURN_AFTER_READ:
                if policy.is_expired():
                    return AccessCheckResult(
                        allowed=False,
                        reason="تم حذف هذا الملف بعد القراءة"
                    )
        
        return AccessCheckResult(allowed=True)
    
    def record_view(self, file_id: str, policies: List[FilePolicy]) -> ViewRecordResult:
        """
        Record a file view and update policy state.
        
        Args:
            file_id: File identifier
            policies: List of policies to update
            
        Returns:
            ViewRecordResult with remaining_views and should_delete
        """
        should_delete = False
        remaining_views = None
        
        for policy in policies:
            policy.current_views += 1
            
            if policy.policy_type == PolicyType.VIEW_ONCE:
                should_delete = True
                
            elif policy.policy_type == PolicyType.VIEW_COUNT:
                if policy.max_views:
                    remaining_views = policy.max_views - policy.current_views
                    if remaining_views <= 0:
                        should_delete = True
                        remaining_views = 0
                        
            elif policy.policy_type == PolicyType.BURN_AFTER_READ:
                should_delete = True
        
        return ViewRecordResult(
            remaining_views=remaining_views,
            should_delete=should_delete
        )
    
    def is_expired(self, policies: List[FilePolicy]) -> bool:
        """Check if any policy has expired."""
        return any(p.is_expired() for p in policies)
    
    def serialize_policy(self, policy: FilePolicy) -> str:
        """Serialize policy to JSON string."""
        return json.dumps(policy.to_dict(), ensure_ascii=False)
    
    def deserialize_policy(self, json_str: str) -> FilePolicy:
        """Deserialize policy from JSON string."""
        data = json.loads(json_str)
        return FilePolicy.from_dict(data)
    
    def serialize_policies(self, policies: List[FilePolicy]) -> str:
        """Serialize multiple policies to JSON string."""
        return json.dumps([p.to_dict() for p in policies], ensure_ascii=False)
    
    def deserialize_policies(self, json_str: str) -> List[FilePolicy]:
        """Deserialize multiple policies from JSON string."""
        data = json.loads(json_str)
        return [FilePolicy.from_dict(p) for p in data]
