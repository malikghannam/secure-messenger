"""
TOTP Two-Factor Authentication API Routes

Provides REST endpoints for TOTP setup, verification, and management.
"""

import json
import time
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash

# Will be initialized when blueprint is registered
db = None
User = None
totp_service = None

totp_bp = Blueprint('totp', __name__, url_prefix='/api/totp')

# Pending TOTP setups: session_id -> {username, secret, expires_at}
PENDING_TOTP_SETUP: Dict[str, Dict[str, Any]] = {}
SETUP_TTL = 300  # 5 minutes

# Pending login sessions requiring TOTP: token -> {username, expires_at}
PENDING_TOTP_LOGIN: Dict[str, Dict[str, Any]] = {}
LOGIN_TTL = 300  # 5 minutes


def init_totp_routes(database, user_model, service):
    """Initialize TOTP routes with dependencies."""
    global db, User, totp_service
    db = database
    User = user_model
    totp_service = service


def ok(data: Dict[str, Any], status: int = 200):
    return jsonify(data), status


def err(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


def cleanup_expired():
    """Remove expired pending sessions."""
    now = time.time()
    for sid in list(PENDING_TOTP_SETUP.keys()):
        if PENDING_TOTP_SETUP[sid].get("expires_at", 0) < now:
            del PENDING_TOTP_SETUP[sid]
    for token in list(PENDING_TOTP_LOGIN.keys()):
        if PENDING_TOTP_LOGIN[token].get("expires_at", 0) < now:
            del PENDING_TOTP_LOGIN[token]


@totp_bp.route('/setup', methods=['POST'])
def totp_setup_simple():
    """
    Initialize TOTP setup for logged-in user (simplified - no password required).
    Used by the settings UI when user is already authenticated.
    
    Request: {username}
    Response: {secret, qr_uri, ascii_qr, session_id}
    """
    cleanup_expired()
    
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    
    if not username:
        return err("username required", 400)
    
    # Get user
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    # Check if TOTP already enabled
    if user.totp_enabled:
        return err("TOTP already enabled. Disable first to reconfigure.", 409)
    
    # Generate new secret
    secret = totp_service.generate_secret()
    qr_uri = totp_service.generate_provisioning_uri(secret, username)
    
    # Generate ASCII QR code for display
    try:
        from messenger.auth.qr_generator import QRGenerator
        ascii_qr = QRGenerator.generate_ascii_qr(qr_uri)
    except:
        ascii_qr = ""
    
    # Store pending setup
    session_id = secrets.token_urlsafe(32)
    PENDING_TOTP_SETUP[session_id] = {
        "username": username,
        "secret": secret,
        "expires_at": time.time() + SETUP_TTL
    }
    
    return ok({
        "ok": True,
        "session_id": session_id,
        "secret": secret,
        "qr_uri": qr_uri,
        "ascii_qr": ascii_qr
    })


@totp_bp.route('/verify-setup', methods=['POST'])
def totp_verify_setup_simple():
    """
    Verify TOTP code and complete setup (simplified endpoint).
    
    Request: {session_id, code}
    Response: {backup_codes}
    """
    cleanup_expired()
    
    data = request.get_json(force=True, silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    code = (data.get("code") or "").strip()
    
    if not session_id or not code:
        return err("session_id and code required", 400)
    
    # Get pending setup
    pending = PENDING_TOTP_SETUP.get(session_id)
    if not pending:
        return err("Invalid or expired setup session", 400)
    
    username = pending["username"]
    secret = pending["secret"]
    
    # Verify code
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid code. Please try again.", 400)
    
    # Generate backup codes
    backup_codes = totp_service.generate_backup_codes()
    backup_hashes = [totp_service.hash_backup_code(c) for c in backup_codes]
    
    # Update user
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    user.totp_secret_encrypted = totp_service.encrypt_secret(secret)
    user.totp_enabled = True
    user.totp_backup_codes = json.dumps(backup_hashes)
    user.totp_failed_attempts = 0
    user.totp_lockout_until = None
    db.session.commit()
    
    # Cleanup pending setup
    del PENDING_TOTP_SETUP[session_id]
    
    return ok({
        "ok": True,
        "backup_codes": backup_codes,
        "message": "TOTP enabled! Save your backup codes securely."
    })


@totp_bp.route('/disable', methods=['POST'])
def totp_disable_simple():
    """
    Disable TOTP for logged-in user (simplified - code only).
    
    Request: {username, code}
    Response: {ok}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    code = (data.get("code") or "").strip()
    
    if not username or not code:
        return err("username and code required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    if not user.totp_enabled:
        return err("TOTP not enabled", 400)
    
    # Verify TOTP code
    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid TOTP code", 401)
    
    # Disable TOTP
    user.totp_secret_encrypted = None
    user.totp_enabled = False
    user.totp_backup_codes = None
    user.totp_failed_attempts = 0
    user.totp_lockout_until = None
    db.session.commit()
    
    return ok({"ok": True, "message": "TOTP disabled successfully"})


@totp_bp.route('/regenerate-backup', methods=['POST'])
def totp_regenerate_backup_simple():
    """
    Regenerate backup codes (simplified - code only).
    
    Request: {username, code}
    Response: {backup_codes}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    code = (data.get("code") or "").strip()
    
    if not username or not code:
        return err("username and code required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    if not user.totp_enabled:
        return err("TOTP not enabled", 400)
    
    # Verify TOTP code
    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid TOTP code", 401)
    
    # Generate new backup codes
    backup_codes = totp_service.generate_backup_codes()
    backup_hashes = [totp_service.hash_backup_code(c) for c in backup_codes]
    user.totp_backup_codes = json.dumps(backup_hashes)
    db.session.commit()
    
    return ok({
        "ok": True,
        "backup_codes": backup_codes,
        "message": "New backup codes generated. Old codes are now invalid."
    })


# =========================
# TOTP SETUP (with password)
# =========================

@totp_bp.route('/setup/init', methods=['POST'])
def totp_setup_init():
    """
    Initialize TOTP setup for a user.
    
    Request: {username, password}
    Response: {secret, qr_uri, session_id}
    """
    cleanup_expired()
    
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    
    if not username or not password:
        return err("username and password required", 400)
    
    # Verify user credentials
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return err("invalid credentials", 401)
    
    # Check if TOTP already enabled
    if user.totp_enabled:
        return err("TOTP already enabled. Disable first to reconfigure.", 409)
    
    # Generate new secret
    secret = totp_service.generate_secret()
    qr_uri = totp_service.generate_provisioning_uri(secret, username)
    
    # Store pending setup
    session_id = secrets.token_urlsafe(32)
    PENDING_TOTP_SETUP[session_id] = {
        "username": username,
        "secret": secret,
        "expires_at": time.time() + SETUP_TTL
    }
    
    return ok({
        "ok": True,
        "session_id": session_id,
        "secret": secret,
        "qr_uri": qr_uri,
        "message": "Scan QR code with authenticator app, then verify with a code"
    })


@totp_bp.route('/setup/verify', methods=['POST'])
def totp_setup_verify():
    """
    Verify TOTP code and complete setup.
    
    Request: {session_id, code}
    Response: {backup_codes}
    """
    cleanup_expired()
    
    data = request.get_json(force=True, silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    code = (data.get("code") or "").strip()
    
    if not session_id or not code:
        return err("session_id and code required", 400)
    
    # Get pending setup
    pending = PENDING_TOTP_SETUP.get(session_id)
    if not pending:
        return err("Invalid or expired setup session", 400)
    
    username = pending["username"]
    secret = pending["secret"]
    
    # Verify code
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid code. Please try again.", 400)
    
    # Generate backup codes
    backup_codes = totp_service.generate_backup_codes()
    backup_hashes = [totp_service.hash_backup_code(c) for c in backup_codes]
    
    # Update user
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    user.totp_secret_encrypted = totp_service.encrypt_secret(secret)
    user.totp_enabled = True
    user.totp_backup_codes = json.dumps(backup_hashes)
    user.totp_failed_attempts = 0
    user.totp_lockout_until = None
    db.session.commit()
    
    # Cleanup pending setup
    del PENDING_TOTP_SETUP[session_id]
    
    return ok({
        "ok": True,
        "backup_codes": backup_codes,
        "message": "TOTP enabled! Save your backup codes securely."
    })


# =========================
# TOTP VERIFICATION (LOGIN)
# =========================

@totp_bp.route('/verify', methods=['POST'])
def totp_verify():
    """
    Verify TOTP code during login.
    
    Request: {login_token, code} or {login_token, backup_code}
    Response: {ok}
    """
    cleanup_expired()
    
    data = request.get_json(force=True, silent=True) or {}
    login_token = (data.get("login_token") or "").strip()
    code = (data.get("code") or "").strip()
    backup_code = (data.get("backup_code") or "").strip()
    
    if not login_token:
        return err("login_token required", 400)
    if not code and not backup_code:
        return err("code or backup_code required", 400)
    
    # Get pending login
    pending = PENDING_TOTP_LOGIN.get(login_token)
    if not pending:
        return err("Invalid or expired login session", 400)
    
    username = pending["username"]
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    # Check lockout
    if user.totp_lockout_until:
        if datetime.now(timezone.utc) < user.totp_lockout_until:
            remaining = int((user.totp_lockout_until - datetime.now(timezone.utc)).total_seconds())
            return err(f"Account locked. Try again in {remaining} seconds.", 423)
        else:
            # Lockout expired, reset
            user.totp_lockout_until = None
            user.totp_failed_attempts = 0
    
    # Verify TOTP code
    if code:
        try:
            secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
        except ValueError:
            # Encryption key changed - need to reset TOTP
            # Disable TOTP for this user so they can re-setup
            user.totp_enabled = False
            user.totp_secret_encrypted = None
            user.totp_backup_codes = None
            db.session.commit()
            del PENDING_TOTP_LOGIN[login_token]
            return err("TOTP configuration corrupted. Please re-enable 2FA in settings.", 400)
        
        is_valid, drift = totp_service.verify_code(secret, code)
        
        if not is_valid:
            user.totp_failed_attempts += 1
            if user.totp_failed_attempts >= totp_service.MAX_ATTEMPTS:
                user.totp_lockout_until = datetime.now(timezone.utc) + \
                    __import__('datetime').timedelta(seconds=totp_service.LOCKOUT_DURATION)
                db.session.commit()
                return err("Too many failed attempts. Account locked for 15 minutes.", 423)
            db.session.commit()
            remaining = totp_service.MAX_ATTEMPTS - user.totp_failed_attempts
            return err(f"Invalid code. {remaining} attempts remaining.", 401)
    
    # Verify backup code
    elif backup_code:
        stored_hashes = json.loads(user.totp_backup_codes or "[]")
        is_valid, remaining_hashes = totp_service.verify_backup_code(stored_hashes, backup_code)
        
        if not is_valid:
            user.totp_failed_attempts += 1
            if user.totp_failed_attempts >= totp_service.MAX_ATTEMPTS:
                user.totp_lockout_until = datetime.now(timezone.utc) + \
                    __import__('datetime').timedelta(seconds=totp_service.LOCKOUT_DURATION)
                db.session.commit()
                return err("Too many failed attempts. Account locked for 15 minutes.", 423)
            db.session.commit()
            return err("Invalid backup code.", 401)
        
        # Update remaining backup codes
        user.totp_backup_codes = json.dumps(remaining_hashes)
    
    # Success - reset failed attempts and cleanup
    user.totp_failed_attempts = 0
    db.session.commit()
    del PENDING_TOTP_LOGIN[login_token]
    
    response = {"ok": True, "message": "TOTP verified successfully"}
    if backup_code:
        remaining_count = len(json.loads(user.totp_backup_codes or "[]"))
        response["backup_codes_remaining"] = remaining_count
        if remaining_count <= 3:
            response["warning"] = f"Only {remaining_count} backup codes remaining!"
    
    return ok(response)


# =========================
# TOTP MANAGEMENT
# =========================

@totp_bp.route('/status', methods=['POST'])
def totp_status():
    """
    Get TOTP status for a user.
    
    Request: {username}
    Response: {enabled, backup_codes_count}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    
    if not username:
        return err("username required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return err("User not found", 404)
    
    backup_count = 0
    if user.totp_backup_codes:
        backup_count = len(json.loads(user.totp_backup_codes))
    
    return ok({
        "ok": True,
        "enabled": user.totp_enabled,
        "backup_codes_count": backup_count
    })


@totp_bp.route('/disable-secure', methods=['POST'])
def totp_disable_secure():
    """
    Disable TOTP for a user (requires password).
    
    Request: {username, password, code}
    Response: {ok}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()
    
    if not username or not password or not code:
        return err("username, password, and code required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return err("invalid credentials", 401)
    
    if not user.totp_enabled:
        return err("TOTP not enabled", 400)
    
    # Verify TOTP code
    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid TOTP code", 401)
    
    # Disable TOTP
    user.totp_secret_encrypted = None
    user.totp_enabled = False
    user.totp_backup_codes = None
    user.totp_failed_attempts = 0
    user.totp_lockout_until = None
    db.session.commit()
    
    return ok({"ok": True, "message": "TOTP disabled successfully"})


@totp_bp.route('/backup/regenerate', methods=['POST'])
def totp_backup_regenerate():
    """
    Regenerate backup codes.
    
    Request: {username, password, code}
    Response: {backup_codes}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()
    
    if not username or not password or not code:
        return err("username, password, and code required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return err("invalid credentials", 401)
    
    if not user.totp_enabled:
        return err("TOTP not enabled", 400)
    
    # Verify TOTP code
    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    is_valid, _ = totp_service.verify_code(secret, code)
    if not is_valid:
        return err("Invalid TOTP code", 401)
    
    # Generate new backup codes
    backup_codes = totp_service.generate_backup_codes()
    backup_hashes = [totp_service.hash_backup_code(c) for c in backup_codes]
    user.totp_backup_codes = json.dumps(backup_hashes)
    db.session.commit()
    
    return ok({
        "ok": True,
        "backup_codes": backup_codes,
        "message": "New backup codes generated. Old codes are now invalid."
    })


@totp_bp.route('/regenerate', methods=['POST'])
def totp_regenerate():
    """
    Regenerate TOTP secret (creates new secret, invalidates old one).
    
    Request: {username, password, code}
    Response: {secret, qr_uri, backup_codes}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()
    
    if not username or not password or not code:
        return err("username, password, and code required", 400)
    
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return err("invalid credentials", 401)
    
    if not user.totp_enabled:
        return err("TOTP not enabled", 400)
    
    # Verify current TOTP code
    old_secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    is_valid, _ = totp_service.verify_code(old_secret, code)
    if not is_valid:
        return err("Invalid TOTP code", 401)
    
    # Generate new secret
    new_secret = totp_service.generate_secret()
    qr_uri = totp_service.generate_provisioning_uri(new_secret, username)
    
    # Generate new backup codes
    backup_codes = totp_service.generate_backup_codes()
    backup_hashes = [totp_service.hash_backup_code(c) for c in backup_codes]
    
    # Update user with new secret
    user.totp_secret_encrypted = totp_service.encrypt_secret(new_secret)
    user.totp_backup_codes = json.dumps(backup_hashes)
    user.totp_failed_attempts = 0
    user.totp_lockout_until = None
    db.session.commit()
    
    return ok({
        "ok": True,
        "secret": new_secret,
        "qr_uri": qr_uri,
        "backup_codes": backup_codes,
        "message": "TOTP regenerated. Old codes are now invalid. Scan new QR code."
    })


def create_totp_login_token(username: str) -> str:
    """Create a pending TOTP login token."""
    cleanup_expired()
    token = secrets.token_urlsafe(32)
    PENDING_TOTP_LOGIN[token] = {
        "username": username,
        "expires_at": time.time() + LOGIN_TTL
    }
    return token
