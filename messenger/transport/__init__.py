"""
Transport Layer

Manages HTTP/WebSocket communication with the relay server. Handles network
errors, retries, and connection state management. This layer is crypto-agnostic
and treats all message envelopes as opaque data structures.
"""

from .transport_client import TransportClient, NetworkError

__all__ = ['TransportClient', 'NetworkError']