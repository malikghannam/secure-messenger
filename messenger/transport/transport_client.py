"""
Transport Client

Crypto-agnostic transport layer for relay server communication.
"""

import time
import logging
import json
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Base exception for network-related errors."""
    pass


class TransportClient:
    """Crypto-agnostic transport client for relay server communication."""
    
    def __init__(
        self, 
        relay_url: str = "http://127.0.0.1:5000",
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ):
        self.relay_url = relay_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SecureMessenger-Transport/1.0'
        })
        
        self._last_successful_request = time.time()
        self._consecutive_failures = 0
        self._offline_mode = False
        
        logger.info(f"TransportClient initialized for relay: {relay_url}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = urljoin(self.relay_url + '/', endpoint.lstrip('/'))
        
        try:
            logger.debug(f"{method} {endpoint} - Making request")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from {endpoint}: {e}")
                raise NetworkError(f"Invalid response format from server")
            
            self._last_successful_request = time.time()
            self._consecutive_failures = 0
            self._offline_mode = False
            
            logger.debug(f"{method} {endpoint} - Success")
            return result
            
        except requests.exceptions.RequestException as e:
            self._consecutive_failures += 1
            logger.error(f"{method} {endpoint} - Request failed: {type(e).__name__}")
            if self._consecutive_failures >= self.max_retries:
                self._offline_mode = True
                logger.warning("Entering offline mode due to consecutive failures")
            raise NetworkError(f"Network request failed: {type(e).__name__}")
    
    def send_message(self, sender: str, recipient: str, envelope: Dict[str, Any]) -> bool:
        try:
            request_data = {"sender": sender, "recipient": recipient, "envelope": envelope}
            response = self._make_request("POST", "/api/msg/send", data=request_data)
            if response.get("ok"):
                logger.info(f"Message sent successfully: {sender} -> {recipient}")
                return True
            else:
                logger.warning(f"Relay rejected message: {response.get('error', 'unknown error')}")
                return False
        except NetworkError as e:
            logger.error(f"Failed to send message {sender} -> {recipient}: {e}")
            return False
    
    def fetch_inbox(self, username: str) -> List[Dict[str, Any]]:
        try:
            response = self._make_request("GET", f"/api/msg/inbox/{username}")
            if response.get("ok"):
                messages = response.get("messages", [])
                logger.info(f"Fetched {len(messages)} messages for {username}")
                return [msg.get("envelope", {}) for msg in messages]
            else:
                logger.warning(f"Failed to fetch inbox: {response.get('error', 'unknown error')}")
                return []
        except NetworkError as e:
            logger.error(f"Failed to fetch inbox for {username}: {e}")
            return []
    
    def get_user_bundle(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            response = self._make_request("GET", f"/api/keys/bundle/{username}")
            if response.get("ok"):
                bundle = response.get("bundle", {})
                logger.info(f"Retrieved key bundle for {username}")
                return bundle
            else:
                logger.warning(f"No key bundle found for {username}")
                return None
        except NetworkError as e:
            logger.error(f"Failed to get key bundle for {username}: {e}")
            return None
    
    def upload_bundle(self, username: str, bundle: Dict[str, Any]) -> bool:
        try:
            request_data = {"username": username, "bundle": bundle}
            response = self._make_request("POST", "/api/keys/upload", data=request_data)
            if response.get("ok"):
                logger.info(f"Uploaded key bundle for {username}")
                return True
            else:
                logger.warning(f"Failed to upload bundle: {response.get('error', 'unknown error')}")
                return False
        except NetworkError as e:
            logger.error(f"Failed to upload bundle for {username}: {e}")
            return False
    
    def register_user(self, username: str, password: str) -> bool:
        try:
            request_data = {"username": username, "password": password}
            response = self._make_request("POST", "/api/register", data=request_data)
            if response.get("ok"):
                logger.info(f"User {username} registered successfully")
                return True
            else:
                logger.warning(f"Registration failed: {response.get('error', 'unknown error')}")
                return False
        except NetworkError as e:
            logger.error(f"Failed to register user {username}: {e}")
            return False
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with two-phase TOTP support.
        
        Returns:
            Dict with: ok, totp_required, login_token (if TOTP needed), error
        """
        try:
            request_data = {"username": username, "password": password}
            response = self._make_request("POST", "/api/login", data=request_data)
            
            if response.get("ok"):
                if response.get("totp_required"):
                    logger.info(f"User {username} requires TOTP verification")
                    return {
                        "ok": True,
                        "totp_required": True,
                        "login_token": response.get("login_token")
                    }
                else:
                    logger.info(f"User {username} logged in successfully")
                    return {"ok": True, "totp_required": False}
            else:
                error = response.get('error', 'unknown error')
                logger.warning(f"Login failed: {error}")
                return {"ok": False, "error": error}
        except NetworkError as e:
            logger.error(f"Failed to login user {username}: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_user_list(self) -> List[str]:
        try:
            response = self._make_request("GET", "/api/users")
            if response.get("ok"):
                users = response.get("users", [])
                logger.info(f"Retrieved {len(users)} users")
                return users
            else:
                logger.warning(f"Failed to get user list: {response.get('error', 'unknown error')}")
                return []
        except NetworkError as e:
            logger.error(f"Failed to get user list: {e}")
            return []
    
    def get_ws_token(self, username: str) -> Optional[str]:
        try:
            request_data = {"username": username}
            response = self._make_request("POST", "/api/ws-token", data=request_data)
            if response.get("ok"):
                token = response.get("token")
                logger.info(f"Retrieved WebSocket token for {username}")
                return token
            else:
                logger.warning(f"Failed to get WS token: {response.get('error', 'unknown error')}")
                return None
        except NetworkError as e:
            logger.error(f"Failed to get WS token for {username}: {e}")
            return None
    
    def health_check(self) -> bool:
        try:
            response = self._make_request("GET", "/api/health")
            return response.get("ok", False)
        except NetworkError:
            return False
    
    def is_online(self) -> bool:
        return not self._offline_mode
    
    def get_network_status(self) -> Dict[str, Any]:
        return {
            "online": not self._offline_mode,
            "last_successful_request": self._last_successful_request,
            "consecutive_failures": self._consecutive_failures,
            "relay_url": self.relay_url
        }
    
    def close(self):
        if self.session:
            self.session.close()
            logger.info("TransportClient closed")

    # =========================
    # FILE OPERATIONS
    # =========================
    
    def upload_file(
        self,
        file_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        sender: str,
        recipient: str,
        encrypted_content: bytes,
        policies_json: str = "[]",
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload an encrypted file to the relay server.
        
        Args:
            file_id: Unique file identifier
            filename: Original filename
            file_type: MIME type
            file_size: File size in bytes
            sender: Sender username
            recipient: Recipient username
            encrypted_content: Encrypted file content
            policies_json: JSON string of policies
            expires_at: Optional expiry date ISO string
            
        Returns:
            Dict with ok status and file_id
        """
        import base64
        try:
            request_data = {
                "file_id": file_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "sender": sender,
                "recipient": recipient,
                "encrypted_content": base64.b64encode(encrypted_content).decode('utf-8'),
                "policies_json": policies_json,
                "expires_at": expires_at
            }
            response = self._make_request("POST", "/api/files/upload", data=request_data)
            if response.get("ok"):
                logger.info(f"File uploaded: {file_id} from {sender} to {recipient}")
                return {"ok": True, "file_id": file_id}
            else:
                error = response.get('error', 'unknown error')
                logger.warning(f"File upload failed: {error}")
                return {"ok": False, "error": error}
        except NetworkError as e:
            logger.error(f"Failed to upload file {file_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def download_file(self, file_id: str) -> Dict[str, Any]:
        """
        Download an encrypted file from the relay server.
        
        Args:
            file_id: File identifier
            
        Returns:
            Dict with file metadata and encrypted_content (bytes)
        """
        import base64
        try:
            response = self._make_request("GET", f"/api/files/download/{file_id}")
            if response.get("ok"):
                encrypted_b64 = response.get("encrypted_content", "")
                encrypted_content = base64.b64decode(encrypted_b64) if encrypted_b64 else b""
                logger.info(f"File downloaded: {file_id}")
                return {
                    "ok": True,
                    "file_id": response.get("file_id"),
                    "filename": response.get("filename"),
                    "file_type": response.get("file_type"),
                    "file_size": response.get("file_size"),
                    "sender": response.get("sender"),
                    "policies_json": response.get("policies_json"),
                    "encrypted_content": encrypted_content,
                    "view_count": response.get("view_count", 0)
                }
            else:
                error = response.get('error', 'unknown error')
                logger.warning(f"File download failed: {error}")
                return {"ok": False, "error": error}
        except NetworkError as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from the relay server.
        
        Args:
            file_id: File identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            response = self._make_request("POST", f"/api/files/delete/{file_id}")
            if response.get("ok"):
                logger.info(f"File deleted: {file_id}")
                return True
            else:
                logger.warning(f"File deletion failed: {response.get('error', 'unknown error')}")
                return False
        except NetworkError as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata without downloading content."""
        try:
            response = self._make_request("GET", f"/api/files/info/{file_id}")
            if response.get("ok"):
                return response
            return None
        except NetworkError:
            return None
    
    def list_files(self, username: str) -> List[Dict[str, Any]]:
        """List files received by a user."""
        try:
            response = self._make_request("GET", f"/api/files/list/{username}")
            if response.get("ok"):
                return response.get("files", [])
            return []
        except NetworkError:
            return []
