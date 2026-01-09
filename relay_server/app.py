from __future__ import annotations

import base64
import json
import secrets
import time
import re
import sys
import os
from typing import Any, Dict, Optional, Tuple

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, KeyBundle, Message, FileMetadata

# Add parent directory to path for messenger imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import email verification
try:
    from messenger.auth.email_verification import EmailVerificationService, get_verification_service
    EMAIL_VERIFICATION_AVAILABLE = True
    print("Email verification module loaded")
except ImportError:
    EMAIL_VERIFICATION_AVAILABLE = False
    print("Warning: Email verification module not available")

# Import TOTP module
try:
    from messenger.auth.totp_service import TOTPService, get_totp_service
    from totp_routes import totp_bp, init_totp_routes, create_totp_login_token
    TOTP_AVAILABLE = True
    print("TOTP module loaded")
except ImportError as e:
    TOTP_AVAILABLE = False
    print(f"Warning: TOTP module not available: {e}")

# Import file routes
try:
    from file_routes import file_bp, init_file_routes
    FILE_ROUTES_AVAILABLE = True
    print("File routes module loaded")
except ImportError as e:
    FILE_ROUTES_AVAILABLE = False
    print(f"Warning: File routes not available: {e}")

WS_TOKENS: Dict[str, Tuple[str, float]] = {}  # token -> (username, expires_at)
WS_TTL = 60  # seconds

# Allowlist origins (browser client ports)
ALLOWED_ORIGINS = {
    "http://127.0.0.1:9000",
    "http://localhost:9000",
    "http://127.0.0.1:5001",
    "http://localhost:5001",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "relay-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///relay.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

socketio = SocketIO(
    app,
    cors_allowed_origins=list(ALLOWED_ORIGINS) + ["*"],  # dev-friendly
    ping_timeout=30,
    ping_interval=10,
)

with app.app_context():
    db.create_all()
    
    # Initialize TOTP routes
    if TOTP_AVAILABLE:
        totp_service = get_totp_service()
        init_totp_routes(db, User, totp_service)
        app.register_blueprint(totp_bp)
        print("TOTP routes registered")
    
    # Initialize file routes
    if FILE_ROUTES_AVAILABLE:
        init_file_routes(db, User, FileMetadata)
        app.register_blueprint(file_bp)
        print("File routes registered")


# -------------------------
# CORS helper (NO extra deps)
# -------------------------
@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    # Allow all origins in development
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp


@app.route("/api/<path:_p>", methods=["OPTIONS"])
def api_options(_p):
    # Browser preflight
    return ("", 204)


def ok(data: Dict[str, Any], status: int = 200):
    return jsonify(data), status


def err(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


def b64d(s: str) -> Optional[bytes]:
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        pad = (-len(s)) % 4
        return base64.urlsafe_b64decode((s + "=" * pad).encode())
    except Exception:
        return None


# =========================
# WS TOKEN
# =========================
@app.route("/api/ws-token", methods=["POST"])
def api_ws_token():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return err("username required", 400)

    if not User.query.filter_by(username=username).first():
        return err("unknown user", 404)

    # cleanup expired
    now = time.time()
    for t, (_u, exp) in list(WS_TOKENS.items()):
        if exp < now:
            WS_TOKENS.pop(t, None)

    token = secrets.token_urlsafe(32)
    WS_TOKENS[token] = (username, time.time() + WS_TTL)
    return ok({"ok": True, "token": token})


@app.route("/api/health", methods=["GET"])
def health():
    return ok({"ok": True})


# =========================
# AUTH
# =========================
@app.route("/api/register", methods=["POST"])
def api_register():
    """Legacy register endpoint - redirects to new flow if email verification is enabled."""
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    
    if not username or not password:
        return err("username/password required", 400)
    if User.query.filter_by(username=username).first():
        return err("username exists", 409)

    # If email provided and verification available, use new flow
    if email and EMAIL_VERIFICATION_AVAILABLE:
        return api_register_init()
    
    # Legacy registration without email
    u = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(u)
    db.session.commit()
    return ok({"ok": True})


@app.route("/api/register/init", methods=["POST"])
def api_register_init():
    """Initialize registration with email verification."""
    if not EMAIL_VERIFICATION_AVAILABLE:
        return err("Email verification not available", 503)
    
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip().lower()
    
    if not username:
        return err("Username is required", 400)
    if not password:
        return err("Password is required", 400)
    if len(password) < 6:
        return err("Password must be at least 6 characters", 400)
    if not email:
        return err("Gmail address is required", 400)
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return err("Username can only contain letters, numbers, and underscores", 400)
    
    if User.query.filter_by(username=username).first():
        return err("Username already exists", 409)
    
    verification_service = get_verification_service()
    if not verification_service.validate_gmail(email):
        return err("Please enter a valid Gmail address", 400)
    
    code = verification_service.generate_code()
    success, message = verification_service.send_verification_email(email, code)
    if not success:
        return err(message, 500)
    
    password_hash = generate_password_hash(password)
    session_id = verification_service.store_pending_verification(
        email=email,
        code=code,
        username=username,
        password_hash=password_hash
    )
    
    return ok({
        "ok": True,
        "session_id": session_id,
        "email_masked": verification_service.mask_email(email),
        "message": "Verification code sent to your email"
    })


@app.route("/api/register/verify", methods=["POST"])
def api_register_verify():
    """Verify code and complete registration."""
    if not EMAIL_VERIFICATION_AVAILABLE:
        return err("Email verification not available", 503)
    
    data = request.get_json(force=True, silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    code = (data.get("code") or "").strip()
    
    if not session_id:
        return err("Session ID is required", 400)
    if not code:
        return err("Verification code is required", 400)
    if not re.match(r'^\d{6}$', code):
        return err("Invalid code format. Please enter 6 digits.", 400)
    
    verification_service = get_verification_service()
    result = verification_service.verify_code(session_id, code)
    
    if not result['success']:
        return err(result['error'], 400)
    
    if User.query.filter_by(username=result['username']).first():
        return err("Username was taken. Please start registration again.", 409)
    
    u = User(
        username=result['username'],
        password_hash=result['password_hash'],
        email_encrypted=result['email_encrypted'],
        email_verified=True
    )
    db.session.add(u)
    db.session.commit()
    
    socketio.emit("user_registered", {"username": result['username']})
    
    return ok({
        "ok": True,
        "username": result['username'],
        "message": "Registration complete! You can now log in."
    })


@app.route("/api/register/resend", methods=["POST"])
def api_register_resend():
    """Resend verification code."""
    if not EMAIL_VERIFICATION_AVAILABLE:
        return err("Email verification not available", 503)
    
    data = request.get_json(force=True, silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    
    if not session_id:
        return err("Session ID is required", 400)
    
    verification_service = get_verification_service()
    success, message, _ = verification_service.resend_code(session_id)
    
    if not success:
        return err(message, 429 if "wait" in message.lower() or "maximum" in message.lower() else 400)
    
    return ok({"ok": True, "message": message})


@app.route("/api/register/status", methods=["POST"])
def api_register_status():
    """Get status of pending registration."""
    if not EMAIL_VERIFICATION_AVAILABLE:
        return err("Email verification not available", 503)
    
    data = request.get_json(force=True, silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    
    if not session_id:
        return err("Session ID is required", 400)
    
    verification_service = get_verification_service()
    info = verification_service.get_session_info(session_id)
    
    if not info:
        return err("Session expired or invalid", 400)
    
    return ok({"ok": True, **info})


@app.route("/api/login", methods=["POST"])
def api_login():
    """Login with optional TOTP two-factor authentication."""
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    
    u = User.query.filter_by(username=username).first()
    if not u or not check_password_hash(u.password_hash, password):
        return err("invalid credentials", 401)
    
    # Check if TOTP is enabled for this user
    if TOTP_AVAILABLE and u.totp_enabled:
        # Create a login token for TOTP verification
        login_token = create_totp_login_token(username)
        return ok({
            "ok": True,
            "totp_required": True,
            "login_token": login_token,
            "message": "TOTP verification required"
        })
    
    # No TOTP - login successful
    return ok({"ok": True, "totp_required": False})


@app.route("/api/users", methods=["GET"])
def api_users():
    users = [u.username for u in User.query.order_by(User.username.asc()).all()]
    return ok({"ok": True, "users": users})


# =========================
# KEY BUNDLES
# =========================
@app.route("/api/keys/upload", methods=["POST"])
def api_keys_upload():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    bundle = data.get("bundle") or {}

    if not username:
        return err("username required", 400)
    if not User.query.filter_by(username=username).first():
        return err("unknown user", 404)

    for k in ["ik_pub", "spk_pub", "kyber_pub"]:
        if not bundle.get(k):
            return err(f"missing bundle.{k}", 400)

    kb = KeyBundle.query.filter_by(username=username).first()
    if kb is None:
        kb = KeyBundle(username=username)
        db.session.add(kb)

    kb.ik_pub = bundle["ik_pub"]
    kb.spk_pub = bundle["spk_pub"]
    kb.spk_sig = bundle.get("spk_sig")
    kb.opk_id = bundle.get("opk_id")
    kb.opk_pub = bundle.get("opk_pub")
    kb.kyber_pub = bundle["kyber_pub"]
    db.session.commit()

    return ok({"ok": True})


@app.route("/api/keys/bundle/<username>", methods=["GET"])
def api_keys_bundle(username: str):
    kb = KeyBundle.query.filter_by(username=username).first()
    if kb is None:
        return err("no bundle", 404)

    opk_id = kb.opk_id
    opk_pub = kb.opk_pub
    kb.opk_id = None
    kb.opk_pub = None
    db.session.commit()

    return ok({
        "ok": True,
        "bundle": {
            "username": kb.username,
            "ik_pub": kb.ik_pub,
            "spk_pub": kb.spk_pub,
            "spk_sig": kb.spk_sig,
            "opk_id": opk_id,
            "opk_pub": opk_pub,
            "kyber_pub": kb.kyber_pub,
        }
    })


# =========================
# MESSAGES
# =========================
@app.route("/api/msg/send", methods=["POST"])
def api_msg_send():
    data = request.get_json(force=True, silent=True) or {}
    sender = (data.get("sender") or "").strip()
    recipient = (data.get("recipient") or "").strip()
    envelope = data.get("envelope")

    if not sender or not recipient or envelope is None:
        return err("sender/recipient/envelope required", 400)

    if not User.query.filter_by(username=sender).first():
        return err("unknown sender", 404)
    if not User.query.filter_by(username=recipient).first():
        return err("unknown recipient", 404)

    msg = Message(
        sender=sender,
        recipient=recipient,
        envelope=json.dumps(envelope),
        delivered=False,
    )
    db.session.add(msg)
    db.session.commit()

    socketio.emit("msg", {"from": sender}, room=recipient)
    return ok({"ok": True, "id": msg.id})


@app.route("/api/msg/inbox/<username>", methods=["GET"])
def api_msg_inbox(username: str):
    rows = Message.query.filter_by(recipient=username, delivered=False).order_by(Message.id.asc()).all()
    out = []
    for r in rows:
        out.append({"id": r.id, "envelope": json.loads(r.envelope)})
        r.delivered = True
    db.session.commit()
    return ok({"ok": True, "messages": out})


# =========================
# SOCKET AUTH
# =========================
@socketio.on("auth")
def on_auth(data):
    token = (data or {}).get("token")
    if not token or token not in WS_TOKENS:
        emit("authed", {"ok": False, "error": "invalid_token"})
        return

    username, exp = WS_TOKENS.pop(token)
    if time.time() > exp:
        emit("authed", {"ok": False, "error": "token_expired"})
        return

    join_room(username)
    emit("authed", {"ok": True, "username": username})


if __name__ == "__main__":
    print("Starting Relay Server on 0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
