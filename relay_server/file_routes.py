"""File sharing routes for the relay server."""

import os
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO

file_bp = Blueprint('files', __name__, url_prefix='/api/files')

# Will be initialized by init_file_routes
db = None
User = None
FileMetadata = None
UPLOAD_FOLDER = None


def init_file_routes(_db, _User, _FileMetadata, upload_folder=None):
    """Initialize file routes with database models."""
    global db, User, FileMetadata, UPLOAD_FOLDER
    db = _db
    User = _User
    FileMetadata = _FileMetadata
    UPLOAD_FOLDER = upload_folder or os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def ok(data, status=200):
    return jsonify(data), status


def err(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status


@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload an encrypted file with metadata."""
    data = request.get_json(force=True, silent=True) or {}
    
    file_id = data.get('file_id')
    filename = data.get('filename')
    file_type = data.get('file_type')
    file_size = data.get('file_size')
    sender = data.get('sender')
    recipient = data.get('recipient')
    policies_json = data.get('policies_json')
    encrypted_content_b64 = data.get('encrypted_content')
    expires_at_str = data.get('expires_at')
    
    if not all([file_id, filename, file_type, sender, recipient, encrypted_content_b64]):
        return err("Missing required fields", 400)
    
    # Verify users exist
    if User and not User.query.filter_by(username=sender).first():
        return err("Unknown sender", 404)
    if User and not User.query.filter_by(username=recipient).first():
        return err("Unknown recipient", 404)
    
    # Save encrypted content to file
    import base64
    try:
        encrypted_content = base64.b64decode(encrypted_content_b64)
    except Exception:
        return err("Invalid encrypted content", 400)
    
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.enc")
    with open(file_path, 'wb') as f:
        f.write(encrypted_content)

    
    # Parse expiry date
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except Exception:
            pass
    
    # Create metadata record
    metadata = FileMetadata(
        file_id=file_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size or len(encrypted_content),
        sender=sender,
        recipient=recipient,
        policies_json=policies_json or '[]',
        expires_at=expires_at
    )
    db.session.add(metadata)
    db.session.commit()
    
    return ok({"ok": True, "file_id": file_id})


@file_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download an encrypted file."""
    metadata = FileMetadata.query.filter_by(file_id=file_id, is_deleted=False).first()
    if not metadata:
        return err("File not found", 404)
    
    # Check expiry
    if metadata.expires_at and datetime.now(timezone.utc) > metadata.expires_at:
        metadata.is_deleted = True
        db.session.commit()
        return err("File expired", 410)
    
    # Read encrypted content
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.enc")
    if not os.path.exists(file_path):
        return err("File not found on disk", 404)
    
    with open(file_path, 'rb') as f:
        encrypted_content = f.read()
    
    # Update view tracking
    if metadata.first_viewed_at is None:
        metadata.first_viewed_at = datetime.now(timezone.utc)
    metadata.view_count += 1
    db.session.commit()
    
    import base64
    return ok({
        "ok": True,
        "file_id": file_id,
        "filename": metadata.filename,
        "file_type": metadata.file_type,
        "file_size": metadata.file_size,
        "sender": metadata.sender,
        "policies_json": metadata.policies_json,
        "encrypted_content": base64.b64encode(encrypted_content).decode('utf-8'),
        "view_count": metadata.view_count
    })


@file_bp.route('/delete/<file_id>', methods=['DELETE', 'POST'])
def delete_file(file_id):
    """Delete a file."""
    metadata = FileMetadata.query.filter_by(file_id=file_id).first()
    if not metadata:
        return err("File not found", 404)
    
    # Mark as deleted
    metadata.is_deleted = True
    db.session.commit()
    
    # Delete physical file
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.enc")
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return ok({"ok": True, "file_id": file_id})


@file_bp.route('/info/<file_id>', methods=['GET'])
def file_info(file_id):
    """Get file metadata without downloading content."""
    metadata = FileMetadata.query.filter_by(file_id=file_id, is_deleted=False).first()
    if not metadata:
        return err("File not found", 404)
    
    return ok({
        "ok": True,
        "file_id": file_id,
        "filename": metadata.filename,
        "file_type": metadata.file_type,
        "file_size": metadata.file_size,
        "sender": metadata.sender,
        "recipient": metadata.recipient,
        "policies_json": metadata.policies_json,
        "view_count": metadata.view_count,
        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
        "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None
    })


@file_bp.route('/list/<username>', methods=['GET'])
def list_files(username):
    """List files for a user (received files)."""
    files = FileMetadata.query.filter_by(recipient=username, is_deleted=False).order_by(FileMetadata.created_at.desc()).all()
    
    result = []
    for f in files:
        result.append({
            "file_id": f.file_id,
            "filename": f.filename,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "sender": f.sender,
            "policies_json": f.policies_json,
            "view_count": f.view_count,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })
    
    return ok({"ok": True, "files": result})
