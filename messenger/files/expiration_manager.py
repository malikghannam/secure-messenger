"""Expiration manager for automatic file cleanup based on policies."""

import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass


@dataclass
class DeletionResult:
    """Result of file deletion."""
    success: bool
    file_id: str
    error: Optional[str] = None


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    files_checked: int
    files_deleted: int
    errors: List[str]


@dataclass
class ExpirationStatus:
    """Expiration status for a file."""
    file_id: str
    is_expired: bool
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


class ExpirationManager:
    """Manager for file expiration and cleanup."""
    
    CLEANUP_INTERVAL = 300  # 5 minutes
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".secure_files"
        )
        self._scheduled_deletions: Dict[str, datetime] = {}
        self._deleted_files: Set[str] = set()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_file_deleted: Optional[Callable[[str], None]] = None
        self._on_file_expired: Optional[Callable[[str], None]] = None
    
    def set_deletion_callback(self, callback: Callable[[str], None]) -> None:
        self._on_file_deleted = callback
    
    def set_expiration_callback(self, callback: Callable[[str], None]) -> None:
        self._on_file_expired = callback
