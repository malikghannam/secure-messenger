"""
Post-Quantum Backend Abstraction Layer

This module provides a clean abstraction over post-quantum cryptographic operations,
specifically Kyber512 key encapsulation mechanism (KEM). It isolates all direct
oqs-python dependencies to enable future backend replacement without affecting
other components.

The abstraction maintains compatibility with different oqs-python versions while
providing a consistent interface for the rest of the application.
"""

from abc import ABC, abstractmethod
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class PQBackend(ABC):
    """Abstract interface for post-quantum key encapsulation operations."""
    
    @abstractmethod
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate a new Kyber512 keypair.
        
        Returns:
            Tuple of (public_key, private_key) as bytes
        """
        pass
    
    @abstractmethod
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """
        Encapsulate a shared secret using the given public key.
        
        Args:
            public_key: The recipient's Kyber512 public key
            
        Returns:
            Tuple of (ciphertext, shared_secret) as bytes
        """
        pass
    
    @abstractmethod
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulate a shared secret using the private key and ciphertext.
        
        Args:
            private_key: The recipient's Kyber512 private key
            ciphertext: The Kyber512 ciphertext from encapsulation
            
        Returns:
            The shared secret as bytes
        """
        pass


class OQSKyberBackend(PQBackend):
    """
    OQS-based implementation of the PQ backend using Kyber512.
    
    This implementation wraps oqs-python and handles version compatibility
    across different releases of the library.
    """
    
    def __init__(self):
        """Initialize the OQS Kyber backend."""
        try:
            import oqs
            self._oqs = oqs
            logger.debug("OQS Kyber backend initialized successfully")
        except ImportError as e:
            logger.error("Failed to import oqs-python: %s", e)
            raise RuntimeError(
                "oqs-python is required for Kyber512 operations. "
                "Please install it with: pip install oqs-python"
            ) from e
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate a new Kyber512 keypair using oqs-python."""
        try:
            with self._oqs.KeyEncapsulation("Kyber512") as kem:
                public_key = kem.generate_keypair()
                private_key = kem.export_secret_key()
                logger.debug("Generated new Kyber512 keypair")
                return public_key, private_key
        except Exception as e:
            logger.error("Failed to generate Kyber512 keypair: %s", e)
            raise RuntimeError("Kyber512 keypair generation failed") from e
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate a shared secret using Kyber512."""
        try:
            with self._oqs.KeyEncapsulation("Kyber512") as kem:
                ciphertext, shared_secret = kem.encap_secret(public_key)
                logger.debug("Kyber512 encapsulation completed")
                return ciphertext, shared_secret
        except Exception as e:
            logger.error("Failed to encapsulate with Kyber512: %s", e)
            raise RuntimeError("Kyber512 encapsulation failed") from e
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulate a shared secret using Kyber512.
        
        This method handles version compatibility across different oqs-python releases
        by trying multiple API patterns for importing the private key.
        """
        try:
            with self._oqs.KeyEncapsulation("Kyber512") as kem:
                # Try different API patterns for version compatibility
                shared_secret = self._decapsulate_with_version_compatibility(
                    kem, private_key, ciphertext
                )
                logger.debug("Kyber512 decapsulation completed")
                return shared_secret
        except Exception as e:
            logger.error("Failed to decapsulate with Kyber512: %s", e)
            raise RuntimeError("Kyber512 decapsulation failed") from e
    
    def _decapsulate_with_version_compatibility(
        self, 
        kem, 
        private_key: bytes, 
        ciphertext: bytes
    ) -> bytes:
        """
        Handle version compatibility for private key import and decapsulation.
        
        This method tries different API patterns used across oqs-python versions:
        1. import_secret_key() - newer versions
        2. set_secret_key() - intermediate versions  
        3. Constructor with secret_key parameter - older versions
        """
        # Try newer oqs-python API
        if hasattr(kem, "import_secret_key"):
            logger.debug("Using import_secret_key API (newer oqs-python)")
            kem.import_secret_key(private_key)
            return kem.decap_secret(ciphertext)
        
        # Try intermediate oqs-python API
        if hasattr(kem, "set_secret_key"):
            logger.debug("Using set_secret_key API (intermediate oqs-python)")
            kem.set_secret_key(private_key)
            return kem.decap_secret(ciphertext)
        
        # Try older oqs-python API with constructor
        logger.debug("Using constructor API (older oqs-python)")
        try:
            kem2 = self._oqs.KeyEncapsulation("Kyber512", secret_key=private_key)
            shared_secret = kem2.decap_secret(ciphertext)
            kem2.free()
            return shared_secret
        except Exception as e:
            raise RuntimeError(
                "Kyber secret key import not supported by this oqs build. "
                "Please upgrade liboqs / oqs-python."
            ) from e


def get_default_backend() -> PQBackend:
    """
    Get the default PQ backend implementation.
    
    Returns:
        An instance of the default PQ backend (OQSKyberBackend)
    """
    return OQSKyberBackend()