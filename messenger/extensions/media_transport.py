"""
Media Transport Extension Interface

This module defines interfaces for future voice/video call capabilities.
The interfaces are designed to extend the existing transport layer without
modifying the core messaging or cryptographic systems.

These interfaces are NOT implemented - they provide architectural hooks for
future development.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum


class MediaType(Enum):
    """Types of media streams."""
    AUDIO = "audio"
    VIDEO = "video"
    SCREEN_SHARE = "screen_share"


class CallStatus(Enum):
    """Status of voice/video calls."""
    INITIATING = "initiating"
    RINGING = "ringing"
    CONNECTED = "connected"
    ON_HOLD = "on_hold"
    ENDED = "ended"
    FAILED = "failed"


class MediaTransportInterface(ABC):
    """
    Interface for voice/video call transport capabilities.
    
    This interface defines how media calls would extend the existing transport
    layer. Media streams would use separate encrypted channels while leveraging
    the same authentication and session management as text messages.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    @abstractmethod
    def initiate_call(
        self, 
        peer: str, 
        media_types: List[MediaType],
        call_metadata: Dict[str, Any]
    ) -> str:
        """
        Initiate a voice/video call with a peer.
        
        Args:
            peer: Username of the call recipient
            media_types: Types of media to include (audio, video, etc.)
            call_metadata: Additional call parameters
            
        Returns:
            Call ID for tracking the call session
            
        Note: Would leverage existing session authentication
        """
        pass
    
    @abstractmethod
    def accept_call(self, call_id: str, media_types: List[MediaType]) -> bool:
        """
        Accept an incoming call.
        
        Args:
            call_id: ID of the incoming call
            media_types: Media types to accept
            
        Returns:
            True if call was accepted successfully
        """
        pass
    
    @abstractmethod
    def reject_call(self, call_id: str, reason: Optional[str] = None) -> bool:
        """
        Reject an incoming call.
        
        Args:
            call_id: ID of the call to reject
            reason: Optional rejection reason
            
        Returns:
            True if call was rejected successfully
        """
        pass
    
    @abstractmethod
    def end_call(self, call_id: str) -> bool:
        """
        End an active call.
        
        Args:
            call_id: ID of the call to end
            
        Returns:
            True if call was ended successfully
        """
        pass
    
    @abstractmethod
    def get_call_status(self, call_id: str) -> CallStatus:
        """
        Get the current status of a call.
        
        Args:
            call_id: ID of the call to check
            
        Returns:
            Current status of the call
        """
        pass
    
    @abstractmethod
    def mute_media(self, call_id: str, media_type: MediaType) -> bool:
        """
        Mute a specific media type in an active call.
        
        Args:
            call_id: ID of the active call
            media_type: Type of media to mute
            
        Returns:
            True if media was muted successfully
        """
        pass
    
    @abstractmethod
    def unmute_media(self, call_id: str, media_type: MediaType) -> bool:
        """
        Unmute a specific media type in an active call.
        
        Args:
            call_id: ID of the active call
            media_type: Type of media to unmute
            
        Returns:
            True if media was unmuted successfully
        """
        pass


class MediaTransportHooks:
    """
    Hook system for media transport events.
    
    This class provides hooks that would be called during voice/video call
    operations, allowing the UI and other components to respond to call events
    without tight coupling to the media transport implementation.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    def __init__(self):
        """Initialize media transport hooks."""
        self._callbacks = {
            'call_initiated': None,
            'call_received': None,
            'call_accepted': None,
            'call_rejected': None,
            'call_connected': None,
            'call_ended': None,
            'call_failed': None,
            'media_muted': None,
            'media_unmuted': None
        }
    
    def register_call_initiated_hook(
        self, 
        callback: Callable[[str, str, List[MediaType]], None]
    ):
        """
        Register callback for when a call is initiated.
        
        Args:
            callback: Function called with (call_id, peer, media_types)
        """
        self._callbacks['call_initiated'] = callback
    
    def register_call_received_hook(
        self, 
        callback: Callable[[str, str, List[MediaType]], None]
    ):
        """
        Register callback for when a call is received.
        
        Args:
            callback: Function called with (call_id, peer, media_types)
        """
        self._callbacks['call_received'] = callback
    
    def register_call_connected_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for when a call connects.
        
        Args:
            callback: Function called with (call_id,)
        """
        self._callbacks['call_connected'] = callback
    
    def register_call_ended_hook(
        self, 
        callback: Callable[[str, str], None]
    ):
        """
        Register callback for when a call ends.
        
        Args:
            callback: Function called with (call_id, reason)
        """
        self._callbacks['call_ended'] = callback