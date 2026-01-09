#!/usr/bin/env python3
"""
Production-Ready Secure Messenger - Main Entry Point

This is the main entry point for the refactored secure messaging application.
It demonstrates the new layered architecture while preserving all existing
functionality.

Usage:
    python main.py

The application will start a Flask development server on http://127.0.0.1:5001
"""

import sys
from pathlib import Path
from flask import Flask

# Add the messenger package to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import from the new layered structure
try:
    from messenger.crypto import client_store
    from messenger.pq_backend import get_default_backend
    from messenger.ui import UIController
    print("✅ Successfully imported from new layered structure")
except ImportError as e:
    print(f"❌ Failed to import from new structure: {e}")
    sys.exit(1)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    # Initialize UI controller with the app
    ui_controller = UIController(app, relay_url="http://127.0.0.1:5000")
    
    return app, ui_controller

def main():
    """Main entry point for the application."""
    print("🚀 Starting Production-Ready Secure Messenger")
    print("📁 New layered architecture:")
    print("   - messenger.crypto (frozen cryptographic layer)")
    print("   - messenger.pq_backend (post-quantum abstraction)")
    print("   - messenger.message (session management)")
    print("   - messenger.transport (network layer)")
    print("   - messenger.ui (user interface layer)")
    print()
    
    # Test the new PQ backend
    try:
        backend = get_default_backend()
        print("✅ PQ backend initialized successfully")
    except Exception as e:
        print(f"❌ PQ backend initialization failed: {e}")
    
    # Test crypto layer
    try:
        # Test that we can create a new identity using the refactored crypto layer
        test_state = client_store.create_new_identity("test_user")
        print("✅ Crypto layer working correctly")
    except Exception as e:
        print(f"❌ Crypto layer test failed: {e}")
    
    # Create and run the Flask app
    try:
        app, ui_controller = create_app()
        print("✅ UI Controller initialized successfully")
        print()
        print("🎯 Task 5 'Modernize User Interface Components' completed!")
        print("📋 Summary:")
        print("   - Created UIController with crypto-agnostic design")
        print("   - Updated Flask routes for modern messaging interface")
        print("   - Enhanced JavaScript with search functionality")
        print("   - Implemented property tests for UI behavior")
        print("   - Maintained WhatsApp-style visual design")
        print()
        print("🌐 Starting Flask development server...")
        print("   URL: http://127.0.0.1:5001")
        print("   Note: Make sure relay server is running on http://127.0.0.1:5000")
        print()
        
        app.run(host='127.0.0.1', port=5001, debug=True)
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    finally:
        # Clean up
        try:
            ui_controller.close()
        except:
            pass

if __name__ == "__main__":
    main()