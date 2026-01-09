"""
Multi-Device Extension Interface

This module defines interfaces for future multi-device support capabilities.
The interfaces are designed to extend the existing session management without
modifying the frozen cryptographic layer.

These interfaces are NOT implemented - they provide architectural hooks for
future development.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime


class DeviceStatus(Enum):
    """Status of registered devices."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    PENDING = "pending"


class SyncStatus(Enum):
    """Status of device synchronization."""
    IN_SYNC = "in_sync"
    SYNCING = "syncing"
    OUT_OF_SYNC = "out_of_sync"
    SYNC_FAILED = "sync_failed"


class MultiDeviceInterface(ABC):
    """
    Interface for multi-device session management.
    
    This interface defines how multiple devices would share encrypted sessions
    while maintaining the security properties of the existing E2EE system.
    Device synchronization would use the same cryptographic primitives as
    regular messaging.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    @abstractmethod
    def register_device(
        self, 
        device_name: str, 
        device_public_key: bytes,
        device_metadata: Dict[str, Any]
    ) -> str:
        """
        Register a new device for the current user.
        
        Args:
            device_name: Human-readable name for the device
            device_public_key: Public key for the device
            device_metadata: Additional device information
            
        Returns:
            Device ID for the registered device
            
        Note: Would use existing identity key infrastructure
        """
        pass
    
    @abstractmethod
    def revoke_device(self, device_id: str) -> bool:
        """
        Revoke access for a registered device.
        
        Args:
            device_id: ID of the device to revoke
            
        Returns:
            True if device was revoked successfully
        """
        pass
    
    @abstractmethod
    def get_registered_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered devices for the current user.
        
        Returns:
            List of device information dictionaries
        """
        pass
    
    @abstractmethod
    def sync_sessions_to_device(
        self, 
        device_id: str, 
        session_data: Dict[str, Any]
    ) -> bool:
        """
        Synchronize session data to another device.
        
        Args:
            device_id: ID of the target device
            session_data: Encrypted session data to sync
            
        Returns:
            True if sync was initiated successfully
            
        Note: Would encrypt session data for the target device
        """
        pass
    
    @abstractmethod
    def receive_session_sync(
        self, 
        from_device_id: str, 
        encrypted_session_data: bytes
    ) -> bool:
        """
        Receive and process synchronized session data.
        
        Args:
            from_device_id: ID of the source device
            encrypted_session_data: Encrypted session data
            
        Returns:
            True if sync was processed successfully
            
        Note: Would decrypt and integrate session data
        """
        pass
    
    @abstractmethod
    def get_device_sync_status(self, device_id: str) -> SyncStatus:
        """
        Get synchronization status for a device.
        
        Args:
            device_id: ID of the device to check
            
        Returns:
            Current sync status of the device
        """
        pass
    
    @abstractmethod
    def request_session_history(
        self, 
        peer: str, 
        from_device_id: str,
        since_timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Request message history from another device.
        
        Args:
            peer: Peer to get history for
            from_device_id: Device to request history from
            since_timestamp: Only get messages after this time
            
        Returns:
            True if request was sent successfully
        """
        pass


class MultiDeviceHooks:
    """
    Hook system for multi-device events.
    
    This class provides hooks that would be called during multi-device
    operations, allowing the UI and other components to respond to device
    management events without tight coupling.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    def __init__(self):
        """Initialize multi-device hooks."""
        self._callbacks = {
            'device_registered': None,
            'device_revoked': None,
            'sync_started': None,
            'sync_completed': None,
            'sync_failed': None,
            'session_received': None,
            'history_received': None
        }
    
    def register_device_registered_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for when a device is registered.
        
        Args:
            callback: Function called with (device_id, device_name)
        """
        self._callbacks['device_registered'] = callback
    
    def register_device_revoked_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for when a device is revoked.
        
        Args:
            callback: Function called with (device_id,)
        """
        self._callbacks['device_revoked'] = callback
    
    def register_sync_started_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for when sync starts.
        
        Args:
            callback: Function called with (device_id, sync_type)
        """
        self._callbacks['sync_started'] = callback
    
    def register_sync_completed_hook(
        self, 
        callback: Callable[[str, int], None]
    ):
        """
        Register callback for when sync completes.
        
        Args:
            callback: Function called with (device_id, items_synced)
        """
        self._callbacks['sync_completed'] = callback
    
    def register_sync_failed_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for when sync fails.
        
        Args:
            callback: Function called with (device_id, error_message)
        """
        self._callbacks['sync_failed'] = callback