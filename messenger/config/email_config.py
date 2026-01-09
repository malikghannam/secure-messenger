"""
Email Configuration

Gmail SMTP configuration for sending verification emails.
Requires environment variables to be set.
"""

import os
from typing import Dict, Any


def get_smtp_config() -> Dict[str, Any]:
    """
    Get SMTP configuration from environment variables.
    
    Required environment variables:
        GMAIL_SENDER: Your Gmail address (e.g., myapp@gmail.com)
        GMAIL_APP_PASSWORD: 16-character app-specific password
        
    Optional environment variables:
        SMTP_SERVER: SMTP server (default: smtp.gmail.com)
        SMTP_PORT: SMTP port (default: 587)
        EMAIL_ENCRYPTION_KEY: Fernet key for email encryption
    
    Returns:
        Dict with SMTP configuration
    """
    return {
        'server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'port': int(os.environ.get('SMTP_PORT', '587')),
        'sender_email': os.environ.get('GMAIL_SENDER', ''),
        'sender_password': os.environ.get('GMAIL_APP_PASSWORD', ''),
        'use_tls': True
    }


def is_email_configured() -> bool:
    """Check if email sending is properly configured."""
    config = get_smtp_config()
    return bool(config['sender_email'] and config['sender_password'])


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key for email storage.
    
    In production, set EMAIL_ENCRYPTION_KEY environment variable.
    """
    from cryptography.fernet import Fernet
    
    key = os.environ.get('EMAIL_ENCRYPTION_KEY')
    if key:
        return key.encode() if isinstance(key, str) else key
    
    # Generate key for development (not persistent!)
    return Fernet.generate_key()


# Configuration instructions for users
SETUP_INSTRUCTIONS = """
=== Gmail SMTP Setup Instructions ===

1. Go to your Google Account settings:
   https://myaccount.google.com/

2. Enable 2-Step Verification:
   Security → 2-Step Verification → Turn on

3. Create an App Password:
   Security → 2-Step Verification → App passwords
   - Select app: "Mail"
   - Select device: "Other (Custom name)"
   - Enter: "Secure Messenger"
   - Click "Generate"
   - Copy the 16-character password

4. Set environment variables:
   export GMAIL_SENDER="your-email@gmail.com"
   export GMAIL_APP_PASSWORD="your-16-char-password"

5. (Optional) For production, generate and set encryption key:
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   export EMAIL_ENCRYPTION_KEY="your-generated-key"
"""


def print_setup_instructions():
    """Print setup instructions for Gmail SMTP."""
    print(SETUP_INSTRUCTIONS)
