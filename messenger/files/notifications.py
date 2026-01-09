"""Notification service for file sharing events."""

from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class NotificationType(Enum):
    """Types of file notifications."""
    FILE_VIEWED = "file_viewed"
    SCREENSHOT_ATTEMPT = "screenshot_attempt"
    FILE_EXPIRED = "file_expired"
    FILE_DELETED = "file_deleted"
    FORWARD_BLOCKED = "forward_blocked"


@dataclass
class FileNotification:
    """A file-related notification."""
    notification_type: NotificationType
    file_id: str
    sender: str
    recipient: str
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationService:
    """Service for managing file sharing notifications."""
    
    def __init__(self):
        self._notifications: List[FileNotification] = []
        self._callbacks: Dict[NotificationType, List[Callable]] = {}
        self._unread_count: Dict[str, int] = {}  # username -> count
    
    def register_callback(self, notification_type: NotificationType, callback: Callable) -> None:
        """Register a callback for a notification type."""
        if notification_type not in self._callbacks:
            self._callbacks[notification_type] = []
        self._callbacks[notification_type].append(callback)
    
    def _trigger_callbacks(self, notification: FileNotification) -> None:
        """Trigger registered callbacks for a notification."""
        callbacks = self._callbacks.get(notification.notification_type, [])
        for callback in callbacks:
            try:
                callback(notification)
            except Exception:
                pass
    
    def _add_notification(self, notification: FileNotification) -> None:
        """Add notification and update unread count."""
        self._notifications.append(notification)
        self._unread_count[notification.sender] = self._unread_count.get(notification.sender, 0) + 1
        self._trigger_callbacks(notification)

    
    def notify_file_viewed(self, file_id: str, sender: str, recipient: str, view_count: int = 1) -> FileNotification:
        """Notify sender that their file was viewed."""
        notification = FileNotification(
            notification_type=NotificationType.FILE_VIEWED,
            file_id=file_id,
            sender=sender,
            recipient=recipient,
            message=f"تم عرض ملفك من قبل {recipient}",
            metadata={"view_count": view_count}
        )
        self._add_notification(notification)
        return notification
    
    def notify_screenshot_attempt(self, file_id: str, sender: str, recipient: str, attempt_count: int = 1) -> FileNotification:
        """Notify sender of screenshot attempt."""
        notification = FileNotification(
            notification_type=NotificationType.SCREENSHOT_ATTEMPT,
            file_id=file_id,
            sender=sender,
            recipient=recipient,
            message=f"⚠️ محاولة لقطة شاشة من {recipient}!",
            metadata={"attempt_count": attempt_count}
        )
        self._add_notification(notification)
        return notification
    
    def notify_file_expired(self, file_id: str, sender: str, recipient: str, reason: str = "") -> FileNotification:
        """Notify sender that file expired."""
        notification = FileNotification(
            notification_type=NotificationType.FILE_EXPIRED,
            file_id=file_id,
            sender=sender,
            recipient=recipient,
            message=f"انتهت صلاحية ملفك" + (f": {reason}" if reason else ""),
            metadata={"reason": reason}
        )
        self._add_notification(notification)
        return notification
    
    def notify_file_deleted(self, file_id: str, sender: str, recipient: str) -> FileNotification:
        """Notify that file was deleted."""
        notification = FileNotification(
            notification_type=NotificationType.FILE_DELETED,
            file_id=file_id,
            sender=sender,
            recipient=recipient,
            message="تم حذف الملف"
        )
        self._add_notification(notification)
        return notification
    
    def notify_forward_blocked(self, file_id: str, sender: str, recipient: str) -> FileNotification:
        """Notify sender that forward attempt was blocked."""
        notification = FileNotification(
            notification_type=NotificationType.FORWARD_BLOCKED,
            file_id=file_id,
            sender=sender,
            recipient=recipient,
            message=f"⚠️ محاولة إعادة توجيه محظورة من {recipient}!"
        )
        self._add_notification(notification)
        return notification
    
    def get_notifications(self, username: str, limit: int = 50) -> List[FileNotification]:
        """Get notifications for a user (as sender)."""
        user_notifications = [n for n in self._notifications if n.sender == username]
        return sorted(user_notifications, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_unread_count(self, username: str) -> int:
        """Get unread notification count for a user."""
        return self._unread_count.get(username, 0)
    
    def mark_as_read(self, username: str) -> None:
        """Mark all notifications as read for a user."""
        self._unread_count[username] = 0
    
    def clear_notifications(self, username: str) -> None:
        """Clear all notifications for a user."""
        self._notifications = [n for n in self._notifications if n.sender != username]
        self._unread_count[username] = 0


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the singleton notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
