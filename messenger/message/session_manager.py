"""
Message Session Manager

This module provides a pure coordinator layer that manages cryptographic sessions
between the PQ backend and Double Ratchet implementations. It handles session
lifecycle, message encryption/decryption, and replay protection without duplicating
any cryptographic logic.

The SessionManager coordinates existing crypto functions from the frozen crypto layer.
"""

from typing import Optional, Dict, Any, Tuple
import logging
from datetime import datetime

# Import from frozen crypto layer (behavior-frozen - only CALL, don't modify)
from ..crypto.client_store import (
    get_session, put_session, add_history,
    get_private_keys, get_public_bundle
)
from ..crypto.pqx3dh import (
    pqx3dh_initiate, pqx3dh_respond,
    build_initiator_ratchet, build_responder_ratchet
)
from ..crypto.ratchet import DoubleRatchet

# Import PQ backend abstraction
from ..pq_backend import get_default_backend

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Pure coordinator layer for managing cryptographic sessions.
    
    This class coordinates between the PQ backend and Double Ratchet without
    duplicating any cryptographic logic. It calls existing frozen crypto functions
    and manages session lifecycle and persistence.
    """
    
    def __init__(self, state: Dict[str, Any]):
        """
        Initialize SessionManager with user state.
        
        Args:
            state: User state dictionary from client_store
        """
        self.state = state
        self.pq_backend = get_default_backend()
        self._seen_messages = state.setdefault("_seen_msgs_v1", {})
        logger.debug("SessionManager initialized")
    
    def get_session(self, peer: str) -> Optional[DoubleRatchet]:
        """
        Get existing session for a peer.
        
        Args:
            peer: Username of the peer
            
        Returns:
            DoubleRatchet session if exists, None otherwise
        """
        return get_session(self.state, peer)
    
    def create_session(
        self, 
        peer: str, 
        root_key: bytes,
        my_priv: Any,
        their_pub: Any,
        is_initiator: bool
    ) -> DoubleRatchet:
        """Create a new session with a peer."""
        if is_initiator:
            ratchet = build_initiator_ratchet(root_key, my_priv, their_pub)
        else:
            ratchet = build_responder_ratchet(root_key, my_priv, their_pub)
        
        put_session(self.state, peer, ratchet)
        logger.info(f"Created new session with {peer} (initiator: {is_initiator})")
        return ratchet
    
    def initiate_session(self, peer: str, their_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate a new session with a peer using their prekey bundle."""
        my_keys = get_private_keys(self.state)
        
        from ..crypto.client_store import b64d, _load_pub_any
        
        their_ik_pub = _load_pub_any(their_bundle["ik_pub"], "their_ik_pub")
        their_spk_pub = _load_pub_any(their_bundle["spk_pub"], "their_spk_pub")
        their_kyber_pub = b64d(their_bundle["kyber_pub"])
        
        their_opk_pub = None
        opk_id = their_bundle.get("opk_id")
        if opk_id is not None and their_bundle.get("opk_pub"):
            their_opk_pub = _load_pub_any(their_bundle["opk_pub"], "their_opk_pub")
        
        root_key, ek_priv, kyber_ct, opk_used = pqx3dh_initiate(
            my_ik_priv=my_keys["ik_priv"],
            their_ik_pub=their_ik_pub,
            their_spk_pub=their_spk_pub,
            their_opk_pub=their_opk_pub,
            their_kyber_pub=their_kyber_pub
        )
        
        ratchet = self.create_session(
            peer=peer,
            root_key=root_key,
            my_priv=ek_priv,
            their_pub=their_spk_pub,
            is_initiator=True
        )
        
        logger.info(f"Initiated session with {peer}")
        return {
            "ratchet": ratchet,
            "ek_priv": ek_priv,
            "kyber_ct": kyber_ct,
            "opk_id": opk_id
        }
    
    def respond_to_session(self, peer: str, prekey_msg: Dict[str, Any]) -> DoubleRatchet:
        """Respond to a session initiation from a peer."""
        my_keys = get_private_keys(self.state)
        
        from ..crypto.client_store import b64d, _load_pub_any
        
        their_ik_pub = _load_pub_any(prekey_msg["from_ik_pub"], "their_ik_pub")
        ek_pub_bytes = b64d(prekey_msg["ek_pub"])
        kyber_ct = b64d(prekey_msg["kyber_ct"])
        
        opk_id = prekey_msg.get("opk_id")
        my_opk_priv = None
        if opk_id is not None:
            from ..crypto.client_store import get_opk_priv_by_id, mark_opk_used, _load_priv_any
            opk_priv_str = get_opk_priv_by_id(self.state, opk_id)
            if opk_priv_str:
                my_opk_priv = _load_priv_any(opk_priv_str, f"opk_{opk_id}")
                mark_opk_used(self.state, opk_id)
        
        root_key = pqx3dh_respond(
            my_ik_priv=my_keys["ik_priv"],
            my_spk_priv=my_keys["spk_priv"],
            my_opk_priv=my_opk_priv,
            my_kyber_priv=my_keys["kyber_priv"],
            their_ik_pub=their_ik_pub,
            ek_pub_bytes=ek_pub_bytes,
            kyber_ct=kyber_ct
        )
        
        ratchet = self.create_session(
            peer=peer,
            root_key=root_key,
            my_priv=my_keys["spk_priv"],
            their_pub=ek_pub_bytes,
            is_initiator=False
        )
        
        logger.info(f"Responded to session initiation from {peer}")
        return ratchet
    
    def encrypt_message(self, peer: str, plaintext: str) -> Dict[str, Any]:
        """Encrypt a message for a peer."""
        ratchet = self.get_session(peer)
        if ratchet is None:
            raise RuntimeError(f"No session exists with {peer}")
        
        encrypted_payload = ratchet.encrypt(plaintext.encode('utf-8'))
        put_session(self.state, peer, ratchet)
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        add_history(self.state, peer, "out", plaintext, timestamp)
        
        logger.debug(f"Encrypted message for {peer}")
        return {
            "type": "msg",
            "from": self.state["username"],
            "to": peer,
            "payload": encrypted_payload,
            "ts": timestamp
        }
    
    def decrypt_message(self, peer: str, envelope: Dict[str, Any]) -> str:
        """Decrypt a message from a peer."""
        msg_id = f"{peer}:{envelope.get('ts', '')}"
        peer_seen = self._seen_messages.setdefault(peer, {})
        
        if msg_id in peer_seen:
            logger.warning(f"Replay attack detected from {peer}: {msg_id}")
            raise RuntimeError("Message replay detected")
        
        ratchet = self.get_session(peer)
        if ratchet is None:
            raise RuntimeError(f"No session exists with {peer}")
        
        try:
            decrypted_bytes = ratchet.decrypt(envelope["payload"])
            plaintext = decrypted_bytes.decode('utf-8')
            
            put_session(self.state, peer, ratchet)
            peer_seen[msg_id] = True
            
            timestamp = envelope.get("ts", datetime.utcnow().isoformat() + "Z")
            add_history(self.state, peer, "in", plaintext, timestamp)
            
            logger.debug(f"Decrypted message from {peer}")
            return plaintext
            
        except Exception as e:
            logger.error(f"Failed to decrypt message from {peer}: {e}")
            raise RuntimeError(f"Decryption failed: {e}")
    
    def send_message(self, peer: str, plaintext: str, transport_client) -> Dict[str, Any]:
        """Send a message to a peer, handling session initiation if needed."""
        existing_session = self.get_session(peer)
        
        if existing_session is None:
            # Need to initiate session - get recipient's bundle
            bundle = transport_client.get_user_bundle(peer)
            if not bundle:
                raise RuntimeError(f"Could not retrieve bundle for {peer}")
            
            # Initiate session
            session_data = self.initiate_session(peer, bundle)
            
            # Create prekey message envelope
            envelope = self.encrypt_message(peer, plaintext)
            
            # Add prekey-specific fields
            from ..crypto.client_store import b64e
            envelope.update({
                "type": "prekey",
                "ek_pub": b64e(session_data["ratchet"].DHs.public_key().public_bytes_raw()),
                "kyber_ct": b64e(session_data["kyber_ct"]),
                "opk_id": session_data["opk_id"],
                "from_ik_pub": get_public_bundle(self.state)["ik_pub"]
            })
            
            logger.info(f"Created prekey message for {peer}")
            return envelope
        else:
            # Regular message - session already exists
            envelope = self.encrypt_message(peer, plaintext)
            logger.info(f"Encrypted regular message for {peer}")
            return envelope
    
    def handle_prekey_message(self, envelope: Dict[str, Any]) -> str:
        """Handle a prekey message (first message in a conversation)."""
        peer = envelope["from"]
        
        prekey_data = {
            "from_ik_pub": envelope.get("from_ik_pub"),
            "ek_pub": envelope["ek_pub"],
            "kyber_ct": envelope["kyber_ct"],
            "opk_id": envelope.get("opk_id")
        }
        
        # Respond to session initiation
        ratchet = self.respond_to_session(peer, prekey_data)
        
        # Decrypt the message payload
        decrypted_bytes = ratchet.decrypt(envelope["payload"])
        plaintext = decrypted_bytes.decode('utf-8')
        
        # Update session state
        put_session(self.state, peer, ratchet)
        
        # Add to history
        timestamp = envelope.get("ts", datetime.utcnow().isoformat() + "Z")
        add_history(self.state, peer, "in", plaintext, timestamp)
        
        logger.info(f"Handled prekey message from {peer}")
        return plaintext
