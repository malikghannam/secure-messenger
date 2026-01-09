from __future__ import annotations

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now_utc():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_encrypted = db.Column(db.String(512), nullable=True)  # Encrypted Gmail address
    email_verified = db.Column(db.Boolean, default=False, nullable=False)  # Verification status
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)
    
    # TOTP Two-Factor Authentication fields
    totp_secret_encrypted = db.Column(db.String(512), nullable=True)  # Fernet-encrypted base32 secret
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Whether TOTP is active
    totp_backup_codes = db.Column(db.Text, nullable=True)  # JSON array of hashed backup codes
    totp_failed_attempts = db.Column(db.Integer, default=0, nullable=False)  # Consecutive failed attempts
    totp_lockout_until = db.Column(db.DateTime(timezone=True), nullable=True)  # Account lockout timestamp


class KeyBundle(db.Model):
    __tablename__ = "key_bundles"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey("users.username"), unique=True, nullable=False, index=True)

    # base64 strings
    ik_pub = db.Column(db.Text, nullable=False)
    spk_pub = db.Column(db.Text, nullable=False)
    spk_sig = db.Column(db.Text, nullable=True)

    opk_id = db.Column(db.Integer, nullable=True)
    opk_pub = db.Column(db.Text, nullable=True)

    kyber_pub = db.Column(db.Text, nullable=False)

    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80), nullable=False, index=True)
    recipient = db.Column(db.String(80), nullable=False, index=True)

    # JSON envelope as text: {"type":"prekey"/"msg", ...}
    envelope = db.Column(db.Text, nullable=False)

    delivered = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)



class FileMetadata(db.Model):
    """Metadata for secure file sharing."""
    __tablename__ = "file_metadata"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    sender = db.Column(db.String(80), nullable=False, index=True)
    recipient = db.Column(db.String(80), nullable=False, index=True)
    policies_json = db.Column(db.Text, nullable=False)  # JSON array of policies
    
    # Tracking
    view_count = db.Column(db.Integer, default=0, nullable=False)
    first_viewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
