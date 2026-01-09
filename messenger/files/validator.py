"""File validation module for secure file sharing."""

import os
import mimetypes
from typing import Optional, Tuple

from messenger.files.models import FileValidationResult
from messenger.files.config import SUPPORTED_FILE_TYPES, get_max_size_for_type


def detect_mime_type(file_path: str) -> Optional[str]:
    """
    Detect MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string or None if detection fails
    """
    # First try using mimetypes module based on extension
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def detect_mime_type_from_content(content: bytes, filename: str = "") -> Optional[str]:
    """
    Detect MIME type from file content using magic bytes.
    
    Args:
        content: File content as bytes
        filename: Optional filename for extension-based fallback
        
    Returns:
        MIME type string or None if detection fails
    """
    # Magic bytes signatures for common file types
    signatures = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xff\xd8\xff': 'image/jpeg',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'RIFF': 'image/webp',  # WebP starts with RIFF....WEBP
        b'%PDF': 'application/pdf',
        b'ID3': 'audio/mpeg',
        b'\xff\xfb': 'audio/mpeg',
        b'\xff\xfa': 'audio/mpeg',
        b'RIFF': 'audio/wav',  # WAV also starts with RIFF
        b'OggS': 'audio/ogg',
    }
    
    # Check magic bytes
    for signature, mime_type in signatures.items():
        if content.startswith(signature):
            # Special handling for RIFF format (WebP vs WAV)
            if signature == b'RIFF' and len(content) >= 12:
                if content[8:12] == b'WEBP':
                    return 'image/webp'
                elif content[8:12] == b'WAVE':
                    return 'audio/wav'
            return mime_type
    
    # Fallback to extension-based detection
    if filename:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type
    
    # Check if it's plain text
    try:
        content[:1024].decode('utf-8')
        return 'text/plain'
    except UnicodeDecodeError:
        pass
    
    return None



def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def validate_file(file_path: str) -> FileValidationResult:
    """
    Validate a file for upload.
    
    Checks:
    1. File exists
    2. MIME type is supported
    3. File size is within limits
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        FileValidationResult with validation status and details
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return FileValidationResult(
            is_valid=False,
            error="الملف غير موجود"
        )
    
    if not os.path.isfile(file_path):
        return FileValidationResult(
            is_valid=False,
            error="المسار ليس ملفاً"
        )
    
    # Detect MIME type
    mime_type = detect_mime_type(file_path)
    
    if mime_type is None:
        return FileValidationResult(
            is_valid=False,
            error="تعذر تحديد نوع الملف"
        )
    
    # Check if MIME type is supported
    if mime_type not in SUPPORTED_FILE_TYPES:
        supported_types = ", ".join(SUPPORTED_FILE_TYPES.keys())
        return FileValidationResult(
            is_valid=False,
            file_type=mime_type,
            error=f"نوع الملف غير مدعوم: {mime_type}. الأنواع المدعومة: صور، PDF، صوت، نص"
        )
    
    # Get file size
    file_size = get_file_size(file_path)
    max_size = get_max_size_for_type(mime_type)
    
    # Check file size
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return FileValidationResult(
            is_valid=False,
            file_type=mime_type,
            file_size=file_size,
            error=f"حجم الملف يتجاوز الحد المسموح ({max_size_mb:.0f} MB)"
        )
    
    # All checks passed
    return FileValidationResult(
        is_valid=True,
        file_type=mime_type,
        file_size=file_size
    )


def validate_file_content(
    content: bytes, 
    filename: str, 
    mime_type: Optional[str] = None
) -> FileValidationResult:
    """
    Validate file content directly (without file path).
    
    Args:
        content: File content as bytes
        filename: Original filename
        mime_type: Optional MIME type (will be detected if not provided)
        
    Returns:
        FileValidationResult with validation status and details
    """
    # Detect MIME type if not provided
    if mime_type is None:
        mime_type = detect_mime_type_from_content(content, filename)
    
    if mime_type is None:
        return FileValidationResult(
            is_valid=False,
            error="تعذر تحديد نوع الملف"
        )
    
    # Check if MIME type is supported
    if mime_type not in SUPPORTED_FILE_TYPES:
        return FileValidationResult(
            is_valid=False,
            file_type=mime_type,
            error=f"نوع الملف غير مدعوم: {mime_type}. الأنواع المدعومة: صور، PDF، صوت، نص"
        )
    
    # Get file size
    file_size = len(content)
    max_size = get_max_size_for_type(mime_type)
    
    # Check file size
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return FileValidationResult(
            is_valid=False,
            file_type=mime_type,
            file_size=file_size,
            error=f"حجم الملف يتجاوز الحد المسموح ({max_size_mb:.0f} MB)"
        )
    
    # All checks passed
    return FileValidationResult(
        is_valid=True,
        file_type=mime_type,
        file_size=file_size
    )
