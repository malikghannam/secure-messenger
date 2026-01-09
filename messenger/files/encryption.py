"""File encryption module using XChaCha20-Poly1305."""

import os
from typing import Tuple

from messenger.crypto.crypto_utils import (
    aead_encrypt_xchacha20poly1305,
    aead_decrypt_xchacha20poly1305,
)


# Key size for XChaCha20-Poly1305
KEY_SIZE = 32


def generate_file_key() -> bytes:
    """
    Generate a unique encryption key for a file.
    
    Returns:
        32-byte random key
    """
    return os.urandom(KEY_SIZE)


def encrypt_file(content: bytes, key: bytes, aad: bytes = b"") -> bytes:
    """
    Encrypt file content using XChaCha20-Poly1305.
    
    Args:
        content: File content to encrypt
        key: 32-byte encryption key
        aad: Additional authenticated data (optional)
        
    Returns:
        Encrypted content (nonce + ciphertext + tag)
    """
    return aead_encrypt_xchacha20poly1305(content, key=key, aad=aad)


def decrypt_file(encrypted_content: bytes, key: bytes, aad: bytes = b"") -> bytes:
    """
    Decrypt file content using XChaCha20-Poly1305.
    
    Args:
        encrypted_content: Encrypted content (nonce + ciphertext + tag)
        key: 32-byte encryption key
        aad: Additional authenticated data (must match encryption)
        
    Returns:
        Decrypted file content
        
    Raises:
        ValueError: If decryption fails (wrong key or tampered data)
    """
    try:
        return aead_decrypt_xchacha20poly1305(encrypted_content, key=key, aad=aad)
    except Exception as e:
        raise ValueError(f"فشل فك تشفير الملف: {e}")


def encrypt_file_with_new_key(content: bytes, aad: bytes = b"") -> Tuple[bytes, bytes]:
    """
    Encrypt file content with a newly generated key.
    
    Args:
        content: File content to encrypt
        aad: Additional authenticated data (optional)
        
    Returns:
        Tuple of (encrypted_content, file_key)
    """
    key = generate_file_key()
    encrypted = encrypt_file(content, key, aad)
    return encrypted, key
