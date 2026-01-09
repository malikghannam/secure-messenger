"""Secure file service for uploading and downloading encrypted files."""

import os
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from messenger.files.models import (
    PolicyType,
    FilePolicy,
    SecureFile,
    SecureFileResult,
    SecureFileContent,
    FileValidationResult,
)
from messenger.files.validator import validate_file, validate_file_content, detect_mime_type
from messenger.files.encryption import encrypt_file_with_new_key, decrypt_file, generate_file_key
from messenger.files.policy_engine import PolicyEngine, AccessCheckResult


class SecureFileService:
    """Main service for secure file operations."""
    
    def __init__(self, transport_client=None, storage_path: str = None):
        """
        Initialize the secure file service.
        
        Args:
            transport_client: Optional transport client for server communication
            storage_path: Optional local storage path for files
        """
        self.transport_client = transport_client
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".secure_files")
        self.policy_engine = PolicyEngine()
        self._files: Dict[str, SecureFile] = {}
        self._file_keys: Dict[str, bytes] = {}
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _generate_file_id(self) -> str:
        """Generate a unique file identifier."""
        return str(uuid.uuid4())
    
    def upload_file(
        self,
        file_path: str,
        recipient: str,
        policies: List[FilePolicy],
        sender: str = "unknown"
    ) -> SecureFileResult:
        """
        Upload and encrypt a file with security policies.
        
        Args:
            file_path: Path to the file to upload
            recipient: Username of the recipient
            policies: List of security policies to apply
            sender: Username of the sender
            
        Returns:
            SecureFileResult with file_id and status
        """
        # Validate file
        validation = validate_file(file_path)
        if not validation.is_valid:
            return SecureFileResult(success=False, error=validation.error)
        
        # Validate policies
        policy_validation = self.policy_engine.validate_policies(policies)
        if not policy_validation.is_valid:
            return SecureFileResult(
                success=False,
                error=f"السياسات غير متوافقة: {', '.join(policy_validation.conflicts)}"
            )

        try:
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Generate file ID
            file_id = self._generate_file_id()
            
            # Encrypt file content
            encrypted_content, file_key = encrypt_file_with_new_key(content)
            
            # Store file key (in production, this would be encrypted with recipient's key)
            self._file_keys[file_id] = file_key
            
            # Create secure file object
            filename = os.path.basename(file_path)
            secure_file = SecureFile(
                file_id=file_id,
                filename=filename,
                file_type=validation.file_type,
                file_size=validation.file_size,
                encrypted_content=encrypted_content,
                encrypted_key=file_key,  # In production, encrypt with recipient's public key
                policies=policies,
                sender=sender,
                recipient=recipient,
                created_at=datetime.now()
            )
            
            # Store file
            self._files[file_id] = secure_file
            
            # Save to disk
            self._save_file_to_disk(file_id, secure_file)
            
            return SecureFileResult(success=True, file_id=file_id)
            
        except Exception as e:
            return SecureFileResult(success=False, error=f"فشل رفع الملف: {str(e)}")
    
    def upload_file_content(
        self,
        content: bytes,
        filename: str,
        recipient: str,
        policies: List[FilePolicy],
        sender: str = "unknown",
        mime_type: Optional[str] = None
    ) -> SecureFileResult:
        """
        Upload file content directly (without file path).
        
        Args:
            content: File content as bytes
            filename: Original filename
            recipient: Username of the recipient
            policies: List of security policies to apply
            sender: Username of the sender
            mime_type: Optional MIME type
            
        Returns:
            SecureFileResult with file_id and status
        """
        # Validate content
        validation = validate_file_content(content, filename, mime_type)
        if not validation.is_valid:
            return SecureFileResult(success=False, error=validation.error)
        
        # Validate policies
        policy_validation = self.policy_engine.validate_policies(policies)
        if not policy_validation.is_valid:
            return SecureFileResult(
                success=False,
                error=f"السياسات غير متوافقة: {', '.join(policy_validation.conflicts)}"
            )
        
        try:
            # Generate file ID
            file_id = self._generate_file_id()
            
            # Encrypt file content
            encrypted_content, file_key = encrypt_file_with_new_key(content)
            
            # Store file key
            self._file_keys[file_id] = file_key
            
            # Create secure file object
            secure_file = SecureFile(
                file_id=file_id,
                filename=filename,
                file_type=validation.file_type,
                file_size=validation.file_size,
                encrypted_content=encrypted_content,
                encrypted_key=file_key,
                policies=policies,
                sender=sender,
                recipient=recipient,
                created_at=datetime.now()
            )
            
            # Store file
            self._files[file_id] = secure_file
            
            return SecureFileResult(success=True, file_id=file_id)
            
        except Exception as e:
            return SecureFileResult(success=False, error=f"فشل رفع الملف: {str(e)}")

    
    def download_file(self, file_id: str) -> Optional[SecureFileContent]:
        """
        Download and decrypt a secure file.
        
        Args:
            file_id: Unique identifier of the file
            
        Returns:
            SecureFileContent with decrypted data and policies, or None if not found
        """
        # Get file
        secure_file = self._files.get(file_id)
        if not secure_file:
            # Try loading from disk
            secure_file = self._load_file_from_disk(file_id)
            if not secure_file:
                return None
        
        # Check if file is deleted
        if secure_file.is_deleted:
            return None
        
        # Check access based on policies
        access_result = self.policy_engine.check_access(file_id, secure_file.policies)
        if not access_result.allowed:
            return None
        
        try:
            # Get file key
            file_key = self._file_keys.get(file_id, secure_file.encrypted_key)
            
            # Decrypt content
            decrypted_content = decrypt_file(secure_file.encrypted_content, file_key)
            
            # Record view
            view_result = self.policy_engine.record_view(file_id, secure_file.policies)
            
            # Update tracking
            now = datetime.now()
            if secure_file.first_viewed_at is None:
                secure_file.first_viewed_at = now
            secure_file.last_viewed_at = now
            secure_file.view_count += 1
            
            # Check if should delete
            if view_result.should_delete:
                self._mark_for_deletion(file_id)
            
            return SecureFileContent(
                file_id=file_id,
                filename=secure_file.filename,
                file_type=secure_file.file_type,
                content=decrypted_content,
                policies=secure_file.policies,
                sender=secure_file.sender
            )
            
        except Exception as e:
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata without decrypting."""
        secure_file = self._files.get(file_id)
        if not secure_file:
            return None
        
        return {
            'file_id': secure_file.file_id,
            'filename': secure_file.filename,
            'file_type': secure_file.file_type,
            'file_size': secure_file.file_size,
            'sender': secure_file.sender,
            'recipient': secure_file.recipient,
            'created_at': secure_file.created_at.isoformat(),
            'policies': [p.to_dict() for p in secure_file.policies],
            'view_count': secure_file.view_count,
            'is_deleted': secure_file.is_deleted
        }
    
    def _mark_for_deletion(self, file_id: str) -> None:
        """Mark a file for deletion."""
        if file_id in self._files:
            self._files[file_id].is_deleted = True
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file permanently.
        
        Args:
            file_id: File identifier
            
        Returns:
            True if deleted, False if not found
        """
        if file_id in self._files:
            del self._files[file_id]
        if file_id in self._file_keys:
            del self._file_keys[file_id]
        
        # Delete from disk
        file_path = os.path.join(self.storage_path, f"{file_id}.enc")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def _save_file_to_disk(self, file_id: str, secure_file: SecureFile) -> None:
        """Save encrypted file to disk."""
        file_path = os.path.join(self.storage_path, f"{file_id}.enc")
        metadata_path = os.path.join(self.storage_path, f"{file_id}.meta")
        
        # Save encrypted content
        with open(file_path, 'wb') as f:
            f.write(secure_file.encrypted_content)
        
        # Save metadata
        metadata = {
            'file_id': secure_file.file_id,
            'filename': secure_file.filename,
            'file_type': secure_file.file_type,
            'file_size': secure_file.file_size,
            'sender': secure_file.sender,
            'recipient': secure_file.recipient,
            'created_at': secure_file.created_at.isoformat(),
            'policies': [p.to_dict() for p in secure_file.policies]
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False)
    
    def _load_file_from_disk(self, file_id: str) -> Optional[SecureFile]:
        """Load encrypted file from disk."""
        file_path = os.path.join(self.storage_path, f"{file_id}.enc")
        metadata_path = os.path.join(self.storage_path, f"{file_id}.meta")
        
        if not os.path.exists(file_path) or not os.path.exists(metadata_path):
            return None
        
        try:
            # Load encrypted content
            with open(file_path, 'rb') as f:
                encrypted_content = f.read()
            
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Reconstruct SecureFile
            policies = [FilePolicy.from_dict(p) for p in metadata['policies']]
            
            return SecureFile(
                file_id=metadata['file_id'],
                filename=metadata['filename'],
                file_type=metadata['file_type'],
                file_size=metadata['file_size'],
                encrypted_content=encrypted_content,
                encrypted_key=b'',  # Key should be stored separately
                policies=policies,
                sender=metadata['sender'],
                recipient=metadata['recipient'],
                created_at=datetime.fromisoformat(metadata['created_at'])
            )
        except Exception:
            return None
