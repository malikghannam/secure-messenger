"""
TOTP Client Module

Client-side TOTP management for two-factor authentication.
Handles setup flow, verification during login, and TOTP management.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import requests

logger = logging.getLogger(__name__)


class TOTPClientError(Exception):
    """Base exception for TOTP client errors."""
    pass


class TOTPClient:
    """
    Client-side TOTP management.
    
    Provides methods for:
    - Setting up TOTP (init, verify, get backup codes)
    - Verifying TOTP during login
    - Managing TOTP (disable, regenerate, status)
    """
    
    def __init__(self, relay_url: str = "http://127.0.0.1:5000", timeout: int = 30):
        """
        Initialize TOTP client.
        
        Args:
            relay_url: Base URL of the relay server
            timeout: Request timeout in seconds
        """
        self.relay_url = relay_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SecureMessenger-TOTP/1.0'
        })
        
        # Store pending setup session
        self._pending_session_id: Optional[str] = None
        self._pending_secret: Optional[str] = None
        self._pending_qr_uri: Optional[str] = None
        
        # Store pending login token
        self._pending_login_token: Optional[str] = None
        
        logger.info("TOTPClient initialized")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to TOTP API."""
        url = urljoin(self.relay_url + '/', endpoint.lstrip('/'))
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TOTP request failed: {type(e).__name__}")
            raise TOTPClientError(f"Network error: {type(e).__name__}")
        except Exception as e:
            logger.error(f"TOTP request error: {e}")
            raise TOTPClientError(str(e))
    
    # =========================
    # TOTP SETUP
    # =========================
    
    def setup_totp(self, username: str, password: str) -> Dict[str, Any]:
        """
        Initialize TOTP setup.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Dict with: secret, qr_uri, session_id, message
            
        Raises:
            TOTPClientError: If setup fails
        """
        response = self._make_request("POST", "/api/totp/setup/init", {
            "username": username,
            "password": password
        })
        
        if not response.get("ok"):
            error = response.get("error", "Setup failed")
            raise TOTPClientError(error)
        
        # Store pending setup info
        self._pending_session_id = response.get("session_id")
        self._pending_secret = response.get("secret")
        self._pending_qr_uri = response.get("qr_uri")
        
        logger.info(f"TOTP setup initiated for {username}")
        
        return {
            "secret": self._pending_secret,
            "qr_uri": self._pending_qr_uri,
            "session_id": self._pending_session_id,
            "message": response.get("message", "Scan QR code with authenticator app")
        }
    
    def confirm_setup(self, code: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Confirm TOTP setup with verification code.
        
        Args:
            code: 6-digit TOTP code from authenticator app
            session_id: Setup session ID (uses stored if not provided)
            
        Returns:
            Dict with: success, backup_codes, message
            
        Raises:
            TOTPClientError: If verification fails
        """
        sid = session_id or self._pending_session_id
        if not sid:
            raise TOTPClientError("No pending setup session")
        
        response = self._make_request("POST", "/api/totp/setup/verify", {
            "session_id": sid,
            "code": code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Verification failed")
            raise TOTPClientError(error)
        
        # Clear pending setup
        self._pending_session_id = None
        self._pending_secret = None
        self._pending_qr_uri = None
        
        logger.info("TOTP setup completed successfully")
        
        return {
            "success": True,
            "backup_codes": response.get("backup_codes", []),
            "message": response.get("message", "TOTP enabled!")
        }
    
    def get_pending_setup_info(self) -> Optional[Dict[str, Any]]:
        """Get info about pending TOTP setup."""
        if not self._pending_session_id:
            return None
        return {
            "session_id": self._pending_session_id,
            "secret": self._pending_secret,
            "qr_uri": self._pending_qr_uri
        }
    
    # =========================
    # TOTP LOGIN VERIFICATION
    # =========================
    
    def set_pending_login_token(self, token: str):
        """Store pending login token for TOTP verification."""
        self._pending_login_token = token
    
    def verify_login(
        self, 
        code: str, 
        login_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify TOTP code during login.
        
        Args:
            code: 6-digit TOTP code
            login_token: Login token (uses stored if not provided)
            
        Returns:
            Dict with: success, message, backup_codes_remaining (if backup used)
            
        Raises:
            TOTPClientError: If verification fails
        """
        token = login_token or self._pending_login_token
        if not token:
            raise TOTPClientError("No pending login token")
        
        response = self._make_request("POST", "/api/totp/verify", {
            "login_token": token,
            "code": code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Verification failed")
            raise TOTPClientError(error)
        
        # Clear pending login token
        self._pending_login_token = None
        
        logger.info("TOTP login verification successful")
        
        result = {
            "success": True,
            "message": response.get("message", "Login successful")
        }
        
        if "backup_codes_remaining" in response:
            result["backup_codes_remaining"] = response["backup_codes_remaining"]
        if "warning" in response:
            result["warning"] = response["warning"]
        
        return result
    
    def verify_login_with_backup(
        self, 
        backup_code: str, 
        login_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify login using backup code.
        
        Args:
            backup_code: 8-character backup code
            login_token: Login token (uses stored if not provided)
            
        Returns:
            Dict with: success, message, backup_codes_remaining, warning
            
        Raises:
            TOTPClientError: If verification fails
        """
        token = login_token or self._pending_login_token
        if not token:
            raise TOTPClientError("No pending login token")
        
        response = self._make_request("POST", "/api/totp/verify", {
            "login_token": token,
            "backup_code": backup_code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Verification failed")
            raise TOTPClientError(error)
        
        # Clear pending login token
        self._pending_login_token = None
        
        logger.info("TOTP login verification with backup code successful")
        
        return {
            "success": True,
            "message": response.get("message", "Login successful"),
            "backup_codes_remaining": response.get("backup_codes_remaining", 0),
            "warning": response.get("warning")
        }
    
    # =========================
    # TOTP MANAGEMENT
    # =========================
    
    def get_status(self, username: str) -> Dict[str, Any]:
        """
        Get TOTP status for a user.
        
        Args:
            username: User's username
            
        Returns:
            Dict with: enabled, backup_codes_count
        """
        response = self._make_request("POST", "/api/totp/status", {
            "username": username
        })
        
        if not response.get("ok"):
            error = response.get("error", "Failed to get status")
            raise TOTPClientError(error)
        
        return {
            "enabled": response.get("enabled", False),
            "backup_codes_count": response.get("backup_codes_count", 0)
        }
    
    def disable_totp(
        self, 
        username: str, 
        password: str, 
        code: str
    ) -> Dict[str, Any]:
        """
        Disable TOTP for a user.
        
        Args:
            username: User's username
            password: User's password
            code: Current TOTP code
            
        Returns:
            Dict with: success, message
            
        Raises:
            TOTPClientError: If disable fails
        """
        response = self._make_request("POST", "/api/totp/disable", {
            "username": username,
            "password": password,
            "code": code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Failed to disable TOTP")
            raise TOTPClientError(error)
        
        logger.info(f"TOTP disabled for {username}")
        
        return {
            "success": True,
            "message": response.get("message", "TOTP disabled")
        }
    
    def regenerate_backup_codes(
        self, 
        username: str, 
        password: str, 
        code: str
    ) -> Dict[str, Any]:
        """
        Regenerate backup codes.
        
        Args:
            username: User's username
            password: User's password
            code: Current TOTP code
            
        Returns:
            Dict with: success, backup_codes, message
            
        Raises:
            TOTPClientError: If regeneration fails
        """
        response = self._make_request("POST", "/api/totp/backup/regenerate", {
            "username": username,
            "password": password,
            "code": code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Failed to regenerate backup codes")
            raise TOTPClientError(error)
        
        logger.info(f"Backup codes regenerated for {username}")
        
        return {
            "success": True,
            "backup_codes": response.get("backup_codes", []),
            "message": response.get("message", "New backup codes generated")
        }
    
    def regenerate_totp(
        self, 
        username: str, 
        password: str, 
        code: str
    ) -> Dict[str, Any]:
        """
        Regenerate TOTP secret (creates new secret, invalidates old one).
        
        Args:
            username: User's username
            password: User's password
            code: Current TOTP code
            
        Returns:
            Dict with: success, secret, qr_uri, backup_codes, message
            
        Raises:
            TOTPClientError: If regeneration fails
        """
        response = self._make_request("POST", "/api/totp/regenerate", {
            "username": username,
            "password": password,
            "code": code
        })
        
        if not response.get("ok"):
            error = response.get("error", "Failed to regenerate TOTP")
            raise TOTPClientError(error)
        
        logger.info(f"TOTP regenerated for {username}")
        
        return {
            "success": True,
            "secret": response.get("secret"),
            "qr_uri": response.get("qr_uri"),
            "backup_codes": response.get("backup_codes", []),
            "message": response.get("message", "TOTP regenerated")
        }
    
    def close(self):
        """Close the client and clean up resources."""
        if self.session:
            self.session.close()
            logger.info("TOTPClient closed")


# Global instance
_totp_client: Optional[TOTPClient] = None


def get_totp_client(relay_url: str = "http://127.0.0.1:5000") -> TOTPClient:
    """Get or create the global TOTP client instance."""
    global _totp_client
    if _totp_client is None:
        _totp_client = TOTPClient(relay_url)
    return _totp_client
