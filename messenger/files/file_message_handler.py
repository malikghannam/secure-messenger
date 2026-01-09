"""
File Message Handler

Integrates secure file sharing with the messaging system.
Handles file message encryption, sending, receiving, and policy enforcement.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from messenger.files.models import PolicyType, FilePolicy, SecureFileResult
from messenger.files.secure_file_service import SecureFileService
from messenger.files.policy_engine import PolicyEngine
from messenger.files.viewer import FileViewer
from messenger.files.expiration_manager import ExpirationManager
from messenger.files.notifications import get_notification_service, NotificationType

logger = logging.getLogger(__name__)


class FileMessageHandler:
    """
    Handles file messages within the secure messenger.
    
    Integrates with SessionManager for encryption and TransportClient for
    server communication.
    """
    
    def __init__(self, transport_client=None):
        """
        Initialize the file message handler.
        
        Args:
            transport_client: TransportClient instance for server communication
        """
        self.transport = transport_client
        self.file_service = SecureFileService()
        self.policy_engine = PolicyEngine()
        self.file_viewer = FileViewer()
        self.expiration_manager = ExpirationManager()
        self.notification_service = get_notification_service()
        
        # Track pending file downloads
        self._pending_files: Dict[str, Dict[str, Any]] = {}
        
        logger.info("FileMessageHandler initialized")
    
    def set_transport(self, transport_client) -> None:
        """Set or update the transport client."""
        self.transport = transport_client
    
    def send_file(
        self,
        sender: str,
        recipient: str,
        file_content: bytes,
        filename: str,
        policies: Optional[List[Dict[str, Any]]] = None
    ) -> SecureFileResult:
        """
        Send a file with security policies.
        
        Args:
            sender: Sender username
            recipient: Recipient username
            file_content: Raw file content
            filename: Original filename
            policies: List of policy dicts with type and parameters
            
        Returns:
            SecureFileResult with success status and file_id
        """
        # Convert policy dicts to FilePolicy objects
        file_policies = []
        if policies:
            for p in policies:
                policy_type = PolicyType(p.get('type', 'view_count'))
                file_policy = self.policy_engine.create_policy(
                    policy_type=policy_type,
                    duration_seconds=p.get('duration_seconds'),
                    max_views=p.get('max_views'),
                    expiry_date=datetime.fromisoformat(p['expiry_date'].replace('Z', '+00:00')) 
                        if p.get('expiry_date') else None,
                    recipient=recipient if policy_type == PolicyType.RECIPIENT_ONLY else None
                )
                file_policies.append(file_policy)
        
        # Validate policy compatibility
        if file_policies:
            validation = self.policy_engine.validate_policies(file_policies)
            if not validation.is_valid:
                return SecureFileResult(
                    success=False,
                    error=f"سياسات غير متوافقة: {', '.join(validation.conflicts)}"
                )
        
        # Upload file through secure file service
        result = self.file_service.upload_file_content(
            content=file_content,
            filename=filename,
            recipient=recipient,
            policies=file_policies,
            sender=sender
        )
        
        if not result.success:
            return result
        
        # Upload to server if transport available
        if self.transport and result.encrypted_content:
            policies_json = json.dumps([p.to_dict() for p in file_policies])
            
            # Calculate expiry for server
            expires_at = None
            for p in file_policies:
                if p.policy_type == PolicyType.EXPIRY_DATE and p.expiry_date:
                    expires_at = p.expiry_date.isoformat()
                    break
            
            upload_result = self.transport.upload_file(
                file_id=result.file_id,
                filename=filename,
                file_type=result.file_type or 'application/octet-stream',
                file_size=len(file_content),
                sender=sender,
                recipient=recipient,
                encrypted_content=result.encrypted_content,
                policies_json=policies_json,
                expires_at=expires_at
            )
            
            if not upload_result.get('ok'):
                return SecureFileResult(
                    success=False,
                    error=upload_result.get('error', 'فشل رفع الملف للخادم')
                )
        
        logger.info(f"File sent: {result.file_id} from {sender} to {recipient}")
        return result
    
    def receive_file(
        self,
        file_id: str,
        recipient: str
    ) -> Optional[Dict[str, Any]]:
        """
        Receive and decrypt a file.
        
        Args:
            file_id: File identifier
            recipient: Recipient username (for policy verification)
            
        Returns:
            Dict with file content and metadata, or None if failed
        """
        if not self.transport:
            logger.error("No transport client available")
            return None
        
        # Download from server
        download_result = self.transport.download_file(file_id)
        if not download_result.get('ok'):
            logger.error(f"Failed to download file {file_id}: {download_result.get('error')}")
            return None
        
        # Parse policies
        policies_json = download_result.get('policies_json', '[]')
        try:
            policies_data = json.loads(policies_json)
            policies = [FilePolicy.from_dict(p) for p in policies_data]
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse policies: {e}")
            policies = []
        
        # Check recipient-only policy
        for policy in policies:
            if policy.policy_type == PolicyType.RECIPIENT_ONLY:
                if policy.recipient and policy.recipient != recipient:
                    logger.warning(f"Recipient mismatch for file {file_id}")
                    return None
        
        # Check access
        access_result = self.policy_engine.check_access(policies, recipient)
        if not access_result.allowed:
            logger.warning(f"Access denied for file {file_id}: {access_result.reason}")
            return None
        
        # Decrypt file
        encrypted_content = download_result.get('encrypted_content', b'')
        decrypted = self.file_service.download_file(file_id)
        
        if not decrypted:
            logger.error(f"Failed to decrypt file {file_id}")
            return None
        
        # Record view
        self.policy_engine.record_view(policies)
        
        # Notify sender
        sender = download_result.get('sender', '')
        if sender:
            self.notification_service.notify_file_viewed(
                file_id=file_id,
                sender=sender,
                recipient=recipient,
                view_count=download_result.get('view_count', 1)
            )
        
        # Check if file should be deleted after view
        should_delete = False
        for policy in policies:
            if policy.policy_type == PolicyType.VIEW_ONCE:
                should_delete = True
                break
            if policy.policy_type == PolicyType.VIEW_COUNT:
                if policy.current_views and policy.max_views:
                    if policy.current_views >= policy.max_views:
                        should_delete = True
                        break
        
        if should_delete:
            self.expiration_manager.schedule_immediate_deletion(file_id)
            if sender:
                self.notification_service.notify_file_expired(
                    file_id=file_id,
                    sender=sender,
                    recipient=recipient,
                    reason="تم الوصول للحد الأقصى من المشاهدات"
                )
        
        return {
            'file_id': file_id,
            'filename': download_result.get('filename'),
            'file_type': download_result.get('file_type'),
            'file_size': download_result.get('file_size'),
            'sender': sender,
            'content': decrypted.content,
            'policies': policies
        }
    
    def open_file_viewer(
        self,
        file_id: str,
        filename: str,
        file_type: str,
        content: bytes,
        policies: List[FilePolicy],
        sender: str
    ) -> Optional[str]:
        """
        Open a file in the secure viewer.
        
        Args:
            file_id: File identifier
            filename: Filename
            file_type: MIME type
            content: Decrypted content
            policies: File policies
            sender: Sender username
            
        Returns:
            Session ID if opened successfully
        """
        from messenger.files.models import SecureFileContent
        
        secure_content = SecureFileContent(
            file_id=file_id,
            filename=filename,
            file_type=file_type,
            content=content,
            policies=policies,
            sender=sender
        )
        
        session = self.file_viewer.open_file(secure_content)
        return session.session_id if session else None
    
    def close_file_viewer(self, session_id: str) -> bool:
        """
        Close a file viewer session.
        
        Args:
            session_id: Viewer session ID
            
        Returns:
            True if closed successfully
        """
        result = self.file_viewer.close_file(session_id)
        return result.success if result else False
    
    def report_screenshot_attempt(
        self,
        file_id: str,
        sender: str,
        recipient: str
    ) -> None:
        """Report a screenshot attempt for a protected file."""
        self.notification_service.notify_screenshot_attempt(
            file_id=file_id,
            sender=sender,
            recipient=recipient
        )
        logger.warning(f"Screenshot attempt reported for file {file_id} by {recipient}")
    
    def get_remaining_time(self, session_id: str) -> Optional[int]:
        """Get remaining viewing time for a time-limited file."""
        return self.file_viewer.get_remaining_time(session_id)
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from local storage and server."""
        # Delete locally
        local_deleted = self.file_service.delete_file(file_id)
        
        # Delete from server
        server_deleted = False
        if self.transport:
            server_deleted = self.transport.delete_file(file_id)
        
        return local_deleted or server_deleted
    
    def cleanup_expired_files(self) -> int:
        """Run cleanup for expired files."""
        result = self.expiration_manager.run_cleanup()
        return result.deleted_count if result else 0
    
    def create_file_message_envelope(
        self,
        file_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        sender: str,
        recipient: str,
        policies: List[FilePolicy]
    ) -> Dict[str, Any]:
        """
        Create a file message envelope for sending via WebSocket.
        
        Args:
            file_id: File identifier
            filename: Original filename
            file_type: MIME type
            file_size: File size in bytes
            sender: Sender username
            recipient: Recipient username
            policies: List of file policies
            
        Returns:
            Message envelope dict
        """
        return {
            "type": "file",
            "file_id": file_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "from": sender,
            "to": recipient,
            "policies": [p.to_dict() for p in policies],
            "ts": datetime.utcnow().isoformat() + "Z"
        }


# Singleton instance
_file_handler: Optional[FileMessageHandler] = None


def get_file_handler(transport_client=None) -> FileMessageHandler:
    """Get the singleton file message handler instance."""
    global _file_handler
    if _file_handler is None:
        _file_handler = FileMessageHandler(transport_client)
    elif transport_client:
        _file_handler.set_transport(transport_client)
    return _file_handler
