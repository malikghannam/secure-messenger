"""
PQ Backend Layer

Provides abstraction over post-quantum cryptographic operations, specifically
Kyber512 key encapsulation mechanism. This layer isolates oqs-python dependencies
and enables future backend replacement.
"""

from .backend import PQBackend, OQSKyberBackend, get_default_backend

__all__ = ['PQBackend', 'OQSKyberBackend', 'get_default_backend']