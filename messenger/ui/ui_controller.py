"""UI Controller - Handles web interface with crypto-agnostic design"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from ..message import SessionManager
from ..transport import TransportClient, NetworkError
from ..crypto.client_store import (
    create_new_identity, save_state, load_state, has_state, get_history, get_public_bundle
)
from ..error_handling import (
    MessengerError, CryptoError, NetworkError as MessengerNetworkError,
    ValidationError, StorageError, AuthenticationError,
    SecureLogger, error_recovery_manager, graceful_degradation_manager
)
from ..profile import ProfileManager, UserProfile

# Import TOTP client
try:
    from ..auth.totp_client import TOTPClient, TOTPClientError
    from ..auth.qr_generator import get_qr_generator
    TOTP_AVAILABLE = True
except ImportError:
    TOTP_AVAILABLE = False
    TOTPClient = None
    TOTPClientError = Exception

logger = SecureLogger("messenger.ui")


class UIController:
    def __init__(self, app: Flask, relay_url: str = "http://127.0.0.1:5000"):
        self.app = app
        self.relay_url = relay_url
        self.transport = TransportClient(relay_url)
        self.profile_manager = ProfileManager()
        
        if TOTP_AVAILABLE:
            self.totp_client = TOTPClient(relay_url)
            try:
                self.qr_generator = get_qr_generator()
            except Exception:
                self.qr_generator = None
        else:
            self.totp_client = None
            self.qr_generator = None
        
        self._user_states: Dict[str, Dict[str, Any]] = {}
        self._session_managers: Dict[str, SessionManager] = {}
        self._user_passwords: Dict[str, str] = {}
        
        self._register_routes()
        graceful_degradation_manager.register_component("ui", essential=False)
        logger.info("UI Controller initialized")

    def _save_user_state(self, username: str) -> bool:
        if username not in self._user_states or username not in self._user_passwords:
            return False
        try:
            save_state(username, self._user_passwords[username], self._user_states[username])
            return True
        except Exception as e:
            logger.error(f"Failed to save state for {username}: {e}")
            return False

    def _register_routes(self):
        @self.app.route('/')
        def index():
            if 'username' in session:
                return redirect(url_for('chat'))
            return redirect(url_for('login'))

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'GET':
                return render_template('login.html', relay_http=self.relay_url)
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('login.html', relay_http=self.relay_url)
            try:
                login_result = self.transport.login_user(username, password)
                if isinstance(login_result, dict):
                    if not login_result.get("ok"):
                        flash(login_result.get('error', 'Invalid credentials'), 'error')
                        return render_template('login.html', relay_http=self.relay_url)
                    if login_result.get("totp_required") and TOTP_AVAILABLE:
                        session['pending_login_username'] = username
                        session['pending_login_password'] = password
                        session['pending_login_token'] = login_result.get("login_token")
                        return redirect(url_for('totp_verify'))
                elif not login_result:
                    flash('Invalid credentials', 'error')
                    return render_template('login.html', relay_http=self.relay_url)
            except Exception as e:
                flash('Connection problem. Please try again.', 'error')
                return render_template('login.html', relay_http=self.relay_url)
            if not has_state(username):
                flash('No local identity found. Please register first.', 'error')
                return render_template('login.html', relay_http=self.relay_url)
            try:
                user_state = load_state(username, password)
                self._user_states[username] = user_state
                self._session_managers[username] = SessionManager(user_state)
                self._user_passwords[username] = password
                session['username'] = username
                flash('Login successful', 'ok')
                return redirect(url_for('chat'))
            except Exception as e:
                if "password" in str(e).lower() or "decrypt" in str(e).lower():
                    flash('Invalid password', 'error')
                else:
                    flash('Failed to load user data', 'error')
                return render_template('login.html', relay_http=self.relay_url)

        @self.app.route('/totp-verify', methods=['GET', 'POST'])
        def totp_verify():
            if 'pending_login_username' not in session:
                flash('No pending login. Please login first.', 'error')
                return redirect(url_for('login'))
            if request.method == 'GET':
                return render_template('totp_verify.html', relay_http=self.relay_url)
            code = request.form.get('code', '').strip()
            backup_code = request.form.get('backup_code', '').strip()
            if not code and not backup_code:
                flash('Please enter a TOTP code or backup code', 'error')
                return render_template('totp_verify.html', relay_http=self.relay_url)
            username = session.get('pending_login_username')
            password = session.get('pending_login_password')
            login_token = session.get('pending_login_token')
            try:
                self.totp_client.set_pending_login_token(login_token)
                if code:
                    result = self.totp_client.verify_login(code)
                else:
                    result = self.totp_client.verify_login_with_backup(backup_code)
                if not result.get('success'):
                    flash(result.get('error', 'Verification failed'), 'error')
                    return render_template('totp_verify.html', relay_http=self.relay_url)
                session.pop('pending_login_username', None)
                session.pop('pending_login_password', None)
                session.pop('pending_login_token', None)
                if not has_state(username):
                    flash('No local identity found.', 'error')
                    return redirect(url_for('login'))
                user_state = load_state(username, password)
                self._user_states[username] = user_state
                self._session_managers[username] = SessionManager(user_state)
                self._user_passwords[username] = password
                session['username'] = username
                flash('Login successful', 'ok')
                return redirect(url_for('chat'))
            except Exception as e:
                flash('Verification failed.', 'error')
                return render_template('totp_verify.html', relay_http=self.relay_url)

        @self.app.route('/register', methods=['GET', 'POST'])
        def register():
            if request.method == 'GET':
                return render_template('register.html', relay_http=self.relay_url)
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('register.html', relay_http=self.relay_url)
            if not self.transport.register_user(username, password):
                flash('Registration failed.', 'error')
                return render_template('register.html', relay_http=self.relay_url)
            try:
                user_state = create_new_identity(username)
                save_state(username, password, user_state)
                bundle = get_public_bundle(user_state)
                self.transport.upload_bundle(username, bundle)
                flash('Registration successful! Please login.', 'ok')
                return redirect(url_for('login'))
            except Exception as e:
                logger.error(f"Failed to create identity: {e}")
                flash('Failed to create user identity', 'error')
                return render_template('register.html', relay_http=self.relay_url)

        @self.app.route('/chat')
        def chat():
            if 'username' not in session:
                return redirect(url_for('login'))
            username = session['username']
            users = self.transport.get_user_list()
            return render_template('chat.html', me=username, users=users, relay_ws=self.relay_url.replace('http', 'ws'))

        @self.app.route('/logout')
        def logout():
            username = session.get('username')
            if username:
                self._save_user_state(username)
                self._user_states.pop(username, None)
                self._session_managers.pop(username, None)
                self._user_passwords.pop(username, None)
            session.clear()
            flash('Logged out successfully', 'ok')
            return redirect(url_for('login'))

        # ============ API Endpoints ============
        @self.app.route('/api/me')
        def api_me():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            return jsonify({'ok': True, 'username': session['username']})

        @self.app.route('/api/users')
        def api_users():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            users = self.transport.get_user_list()
            return jsonify({'ok': True, 'users': users})

        @self.app.route('/api/create-identity', methods=['POST'])
        def api_create_identity():
            """Create local crypto identity after email verification."""
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            if not username or not password:
                return jsonify({'ok': False, 'error': 'username and password required'}), 400
            if has_state(username):
                return jsonify({'ok': False, 'error': 'Identity already exists'}), 409
            try:
                user_state = create_new_identity(username)
                save_state(username, password, user_state)
                bundle = get_public_bundle(user_state)
                self.transport.upload_bundle(username, bundle)
                return jsonify({'ok': True, 'message': 'Identity created successfully'})
            except Exception as e:
                logger.error(f"Failed to create identity: {e}")
                return jsonify({'ok': False, 'error': str(e)}), 500

        @self.app.route('/api/send', methods=['POST'])
        def api_send():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            session_manager = self._session_managers.get(username)
            if not session_manager:
                return jsonify({'ok': False, 'error': 'session_not_found'}), 500
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            recipient = data.get('to', '').strip()
            text = data.get('text', '').strip()
            if not recipient or not text:
                return jsonify({'ok': False, 'error': 'recipient_and_text_required'}), 400
            try:
                envelope = session_manager.send_message(recipient, text, self.transport)
                if self.transport.send_message(username, recipient, envelope):
                    self._save_user_state(username)
                    return jsonify({'ok': True})
                return jsonify({'ok': False, 'error': 'send_failed'}), 500
            except Exception as e:
                return jsonify({'ok': False, 'error': 'internal_error'}), 500

        @self.app.route('/api/inbox')
        def api_inbox():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            session_manager = self._session_managers.get(username)
            if not session_manager:
                return jsonify({'ok': False, 'error': 'session_not_found'}), 500
            try:
                envelopes = self.transport.fetch_inbox(username)
                for envelope in envelopes:
                    try:
                        sender = envelope.get('from')
                        if not sender:
                            continue
                        if envelope.get('type') == 'prekey':
                            session_manager.handle_prekey_message(envelope)
                        else:
                            session_manager.decrypt_message(sender, envelope)
                    except:
                        continue
                if envelopes:
                    self._save_user_state(username)
                return jsonify({'ok': True, 'processed': len(envelopes)})
            except Exception as e:
                return jsonify({'ok': False, 'error': 'inbox_processing_failed'}), 500

        @self.app.route('/api/history/<peer>')
        def api_history(peer: str):
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            user_state = self._user_states.get(username)
            if not user_state:
                return jsonify({'ok': False, 'error': 'user_state_not_found'}), 500
            history = get_history(user_state, peer)
            return jsonify({'ok': True, 'messages': history})

        @self.app.route('/api/ws-token', methods=['POST'])
        def api_ws_token():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            token = self.transport.get_ws_token(username)
            if token:
                return jsonify({'ok': True, 'token': token})
            return jsonify({'ok': False, 'error': 'token_generation_failed'}), 500

        # ============ Profile API Endpoints ============
        @self.app.route('/api/profile', methods=['GET'])
        def api_get_profile():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            profile = self.profile_manager.get_profile(username)
            if not profile:
                profile = self.profile_manager.create_profile(username)
            if profile:
                return jsonify({'ok': True, 'profile': {
                    'username': profile.username,
                    'displayName': profile.display_name,
                    'avatarUrl': profile.get_avatar_url(),
                    'createdAt': profile.created_at,
                    'updatedAt': profile.updated_at
                }})
            return jsonify({'ok': False, 'error': 'profile_not_found'}), 404

        @self.app.route('/api/profile', methods=['POST'])
        def api_update_profile():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            display_name = data.get('displayName', '').strip()
            if display_name:
                success, message = self.profile_manager.update_display_name(username, display_name)
                if success:
                    return jsonify({'ok': True, 'message': message})
                return jsonify({'ok': False, 'error': message}), 400
            return jsonify({'ok': False, 'error': 'no_changes'}), 400

        @self.app.route('/api/profile/<target_username>')
        def api_get_user_profile(target_username: str):
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            profile = self.profile_manager.get_profile(target_username)
            if profile:
                return jsonify({'ok': True, 'profile': {
                    'username': profile.username,
                    'displayName': profile.display_name,
                    'avatarUrl': profile.get_avatar_url(),
                    'initial': profile.get_display_initial()
                }})
            return jsonify({'ok': True, 'profile': {
                'username': target_username,
                'displayName': target_username,
                'avatarUrl': None,
                'initial': target_username[0].upper() if target_username else '?'
            }})

        @self.app.route('/api/avatar', methods=['POST'])
        def api_upload_avatar():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            if 'avatar' not in request.files:
                return jsonify({'ok': False, 'error': 'no_file_provided'}), 400
            file = request.files['avatar']
            if file.filename == '':
                return jsonify({'ok': False, 'error': 'no_file_selected'}), 400
            file_data = file.read()
            content_type = file.content_type or 'application/octet-stream'
            success, message = self.profile_manager.save_avatar(username, file_data, content_type, file.filename)
            if success:
                return jsonify({'ok': True, 'message': message, 'avatarUrl': f'/api/avatar/{username}'})
            return jsonify({'ok': False, 'error': message}), 400

        @self.app.route('/api/avatar/<target_username>')
        def api_get_avatar(target_username: str):
            avatar_path = self.profile_manager.get_avatar_file_path(target_username)
            if avatar_path and avatar_path.exists():
                from flask import send_file
                return send_file(avatar_path, mimetype='image/jpeg')
            return jsonify({'ok': False, 'error': 'avatar_not_found'}), 404

        @self.app.route('/api/avatar', methods=['DELETE'])
        def api_delete_avatar():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            if self.profile_manager.delete_avatar(username):
                return jsonify({'ok': True, 'message': 'Avatar deleted'})
            return jsonify({'ok': False, 'error': 'No avatar to delete'}), 404

        # ============ TOTP API Endpoints ============
        @self.app.route('/api/totp/status', methods=['GET'])
        def api_totp_status():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            if not TOTP_AVAILABLE:
                return jsonify({'ok': True, 'enabled': False, 'available': False})
            username = session['username']
            try:
                status = self.totp_client.get_status(username)
                return jsonify({'ok': True, 'enabled': status.get('enabled', False), 'backup_codes_count': status.get('backup_codes_count', 0)})
            except:
                return jsonify({'ok': True, 'enabled': False})

        @self.app.route('/api/totp/setup', methods=['POST'])
        def api_totp_setup():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            if not TOTP_AVAILABLE:
                return jsonify({'ok': False, 'error': 'TOTP not available'}), 503
            username = session['username']
            password = self._user_passwords.get(username)
            if not password:
                return jsonify({'ok': False, 'error': 'password_not_available'}), 400
            try:
                result = self.totp_client.setup_totp(username, password)
                ascii_qr = None
                if self.qr_generator and result.get('qr_uri'):
                    try:
                        ascii_qr = self.qr_generator.generate_ascii(result['qr_uri'])
                    except:
                        pass
                return jsonify({'ok': True, 'session_id': result.get('session_id'), 'secret': result.get('secret'), 'qr_uri': result.get('qr_uri'), 'ascii_qr': ascii_qr})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)}), 400

        @self.app.route('/api/totp/verify-setup', methods=['POST'])
        def api_totp_verify_setup():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            code = data.get('code', '').strip()
            session_id = data.get('session_id', '').strip()
            if not code:
                return jsonify({'ok': False, 'error': 'code_required'}), 400
            try:
                result = self.totp_client.confirm_setup(code, session_id)
                return jsonify({'ok': True, 'backup_codes': result.get('backup_codes', [])})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)}), 400

        @self.app.route('/api/totp/disable', methods=['POST'])
        def api_totp_disable():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            password = self._user_passwords.get(username)
            if not password:
                return jsonify({'ok': False, 'error': 'password_not_available'}), 400
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            code = data.get('code', '').strip()
            if not code:
                return jsonify({'ok': False, 'error': 'code_required'}), 400
            try:
                result = self.totp_client.disable_totp(username, password, code)
                return jsonify({'ok': True, 'message': result.get('message', 'TOTP disabled')})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)}), 400

        @self.app.route('/api/totp/regenerate-backup', methods=['POST'])
        def api_totp_regenerate_backup():
            if 'username' not in session:
                return jsonify({'ok': False, 'error': 'not_authenticated'}), 401
            username = session['username']
            password = self._user_passwords.get(username)
            if not password:
                return jsonify({'ok': False, 'error': 'password_not_available'}), 400
            data = request.get_json()
            if not data:
                return jsonify({'ok': False, 'error': 'invalid_json'}), 400
            code = data.get('code', '').strip()
            if not code:
                return jsonify({'ok': False, 'error': 'code_required'}), 400
            try:
                result = self.totp_client.regenerate_backup_codes(username, password, code)
                return jsonify({'ok': True, 'backup_codes': result.get('backup_codes', [])})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)}), 400

    def get_user_list(self) -> List[str]:
        return self.transport.get_user_list()

    def close(self):
        if self.transport:
            self.transport.close()
        if TOTP_AVAILABLE and self.totp_client:
            self.totp_client.close()
        logger.info("UI Controller closed")