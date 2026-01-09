"""
Message Layer

Handles session management, message history, and coordination between crypto
operations and transport. This layer manages the application's messaging state
and business logic.
"""

from .session_manager import SessionManager

__all__ = ['SessionManager']