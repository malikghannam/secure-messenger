"""
Production-Ready Secure Messenger

A secure messaging application with end-to-end encryption using PQX3DH + Double Ratchet.
This package provides a layered architecture separating concerns into distinct modules.
"""

__version__ = "1.0.0"
__author__ = "Secure Messenger Team"

# Layer imports for clean API
from . import crypto
from . import pq_backend
from . import message
from . import transport
from . import ui
from . import extensions
from . import security