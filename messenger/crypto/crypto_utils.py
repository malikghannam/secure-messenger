from __future__ import annotations

import os

try:
    from nacl import bindings
except Exception as e:
    bindings = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


def aead_encrypt_xchacha20poly1305(plaintext: bytes, *, key: bytes, aad: bytes = b"") -> bytes:
    if bindings is None:
        raise RuntimeError(f"PyNaCl required for XChaCha20-Poly1305. Import error: {_IMPORT_ERROR}")
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")
    nonce = os.urandom(bindings.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
    ct = bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, aad, nonce, key)
    return nonce + ct


def aead_decrypt_xchacha20poly1305(blob: bytes, *, key: bytes, aad: bytes = b"") -> bytes:
    if bindings is None:
        raise RuntimeError(f"PyNaCl required for XChaCha20-Poly1305. Import error: {_IMPORT_ERROR}")
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")
    nlen = bindings.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
    if len(blob) < nlen:
        raise ValueError("Ciphertext too short")
    nonce, ct = blob[:nlen], blob[nlen:]
    return bindings.crypto_aead_xchacha20poly1305_ietf_decrypt(ct, aad, nonce, key)