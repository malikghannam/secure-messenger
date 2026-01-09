"""
Configuration Validation

Validates configuration parameters to ensure they are safe and secure.
Never allows secrets or keys in configuration files.
"""

from typing import Dict, Any, List, Union
import re
from pathlib import Path
from ..error_handling import ValidationError


class ConfigValidator:
    """
    Validates configuration parameters for security and correctness.
    
    Ensures that configuration files never contain secrets and that
    all parameters are within safe ranges.
    """
    
    def __init__(self):
        """Initialize configuration validator."""
        self.forbidden_secret_patterns = [
            # Base64-like patterns (potential keys)
            r'[A-Za-z0-9+/]{32,}={0,2}',
            
            # Hex patterns (potential keys)
            r'[0-9a-fA-F]{32,}',
            
            # JWT tokens
            r'eyJ[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+',
            
            # Private key headers
            r'-----BEGIN [A-Z ]+PRIVATE KEY-----',
            
            # Common secret formats
            r'sk_[a-zA-Z0-9]+',  # Stripe-style secret keys
            r'pk_[a-zA-Z0-9]+',  # Public keys that might be sensitive
        ]
    
    def validate_config(self, config: Dict[str, Any]):
        """
        Validate entire configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self._validate_no_secrets_in_values(config)
        self._validate_network_config(config.get('network', {}))
        self._validate_ui_config(config.get('ui', {}))
        self._validate_storage_config(config.get('storage', {}))
        self._validate_security_config(config.get('security', {}))
        self._validate_logging_config(config.get('logging', {}))
        self._validate_performance_config(config.get('performance', {}))
    
    def _validate_no_secrets_in_values(self, config: Dict[str, Any], path: str = ""):
        """
        Validate that no values look like secrets.
        
        Args:
            config: Configuration section to validate
            path: Current path in configuration (for error messages)
        """
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, str):
                # Check if value matches secret patterns
                for pattern in self.forbidden_secret_patterns:
                    if re.search(pattern, value):
                        raise ValidationError(
                            f"Configuration value at '{current_path}' appears to contain "
                            f"secret data. Secrets must be provided via runtime mechanisms only."
                        )
                
                # Check for suspicious long strings
                if len(value) > 100 and not self._is_safe_long_string(value, key):
                    raise ValidationError(
                        f"Configuration value at '{current_path}' is suspiciously long "
                        f"and may contain secret data."
                    )
            
            elif isinstance(value, dict):
                self._validate_no_secrets_in_values(value, current_path)
    
    def _is_safe_long_string(self, value: str, key: str) -> bool:
        """Check if a long string is safe (not a secret)."""
        safe_long_string_keys = [
            'format', 'description', 'message', 'template',
            'path', 'directory', 'file_path', 'log_path'
        ]
        
        # If the key suggests it's a safe long string
        if any(safe_key in key.lower() for safe_key in safe_long_string_keys):
            return True
        
        # If it's a file path
        if '/' in value or '\\' in value or value.startswith('~'):
            return True
        
        # If it's a format string
        if '%(' in value or '{' in value:
            return True
        
        return False
    
    def _validate_network_config(self, network: Dict[str, Any]):
        """Validate network configuration."""
        if 'relay_host' in network:
            host = network['relay_host']
            if not isinstance(host, str) or not host.strip():
                raise ValidationError("network.relay_host must be a non-empty string")
            
            # Validate host format (basic check)
            if not re.match(r'^[a-zA-Z0-9.-]+$', host):
                raise ValidationError("network.relay_host contains invalid characters")
        
        if 'relay_port' in network:
            port = network['relay_port']
            if not isinstance(port, int) or not (1 <= port <= 65535):
                raise ValidationError("network.relay_port must be an integer between 1 and 65535")
        
        if 'connection_timeout' in network:
            timeout = network['connection_timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValidationError("network.connection_timeout must be a positive number")
        
        if 'retry_attempts' in network:
            attempts = network['retry_attempts']
            if not isinstance(attempts, int) or not (0 <= attempts <= 100):
                raise ValidationError("network.retry_attempts must be an integer between 0 and 100")
        
        if 'retry_delay' in network:
            delay = network['retry_delay']
            if not isinstance(delay, (int, float)) or delay < 0:
                raise ValidationError("network.retry_delay must be a non-negative number")
    
    def _validate_ui_config(self, ui: Dict[str, Any]):
        """Validate UI configuration."""
        if 'host' in ui:
            host = ui['host']
            if not isinstance(host, str) or not host.strip():
                raise ValidationError("ui.host must be a non-empty string")
        
        if 'port' in ui:
            port = ui['port']
            if not isinstance(port, int) or not (1 <= port <= 65535):
                raise ValidationError("ui.port must be an integer between 1 and 65535")
        
        if 'theme' in ui:
            theme = ui['theme']
            valid_themes = ['light', 'dark', 'auto']
            if theme not in valid_themes:
                raise ValidationError(f"ui.theme must be one of: {', '.join(valid_themes)}")
        
        if 'language' in ui:
            language = ui['language']
            if not isinstance(language, str) or not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', language):
                raise ValidationError("ui.language must be a valid language code (e.g., 'en', 'en-US')")
        
        if 'message_history_limit' in ui:
            limit = ui['message_history_limit']
            if not isinstance(limit, int) or not (1 <= limit <= 10000):
                raise ValidationError("ui.message_history_limit must be an integer between 1 and 10000")
    
    def _validate_storage_config(self, storage: Dict[str, Any]):
        """Validate storage configuration."""
        if 'data_directory' in storage:
            data_dir = storage['data_directory']
            if not isinstance(data_dir, str) or not data_dir.strip():
                raise ValidationError("storage.data_directory must be a non-empty string")
            
            # Validate path format
            try:
                Path(data_dir).expanduser()
            except Exception:
                raise ValidationError("storage.data_directory must be a valid path")
        
        if 'backup_interval_hours' in storage:
            interval = storage['backup_interval_hours']
            if not isinstance(interval, int) or not (1 <= interval <= 8760):  # Max 1 year
                raise ValidationError("storage.backup_interval_hours must be an integer between 1 and 8760")
        
        if 'max_backups' in storage:
            max_backups = storage['max_backups']
            if not isinstance(max_backups, int) or not (0 <= max_backups <= 100):
                raise ValidationError("storage.max_backups must be an integer between 0 and 100")
        
        if 'file_permissions' in storage:
            perms = storage['file_permissions']
            if not isinstance(perms, int) or not (0o000 <= perms <= 0o777):
                raise ValidationError("storage.file_permissions must be a valid octal permission (0o000-0o777)")
    
    def _validate_security_config(self, security: Dict[str, Any]):
        """Validate security configuration."""
        if 'session_timeout_minutes' in security:
            timeout = security['session_timeout_minutes']
            if not isinstance(timeout, int) or not (1 <= timeout <= 10080):  # Max 1 week
                raise ValidationError("security.session_timeout_minutes must be an integer between 1 and 10080")
        
        if 'max_login_attempts' in security:
            attempts = security['max_login_attempts']
            if not isinstance(attempts, int) or not (1 <= attempts <= 100):
                raise ValidationError("security.max_login_attempts must be an integer between 1 and 100")
        
        if 'lockout_duration_minutes' in security:
            duration = security['lockout_duration_minutes']
            if not isinstance(duration, int) or not (1 <= duration <= 1440):  # Max 24 hours
                raise ValidationError("security.lockout_duration_minutes must be an integer between 1 and 1440")
    
    def _validate_logging_config(self, logging: Dict[str, Any]):
        """Validate logging configuration."""
        if 'level' in logging:
            level = logging['level']
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if level not in valid_levels:
                raise ValidationError(f"logging.level must be one of: {', '.join(valid_levels)}")
        
        if 'file_path' in logging:
            file_path = logging['file_path']
            if not isinstance(file_path, str) or not file_path.strip():
                raise ValidationError("logging.file_path must be a non-empty string")
            
            # Validate path format
            try:
                Path(file_path).expanduser()
            except Exception:
                raise ValidationError("logging.file_path must be a valid path")
        
        if 'file_max_size_mb' in logging:
            size = logging['file_max_size_mb']
            if not isinstance(size, (int, float)) or not (1 <= size <= 1000):
                raise ValidationError("logging.file_max_size_mb must be a number between 1 and 1000")
        
        if 'file_backup_count' in logging:
            count = logging['file_backup_count']
            if not isinstance(count, int) or not (0 <= count <= 100):
                raise ValidationError("logging.file_backup_count must be an integer between 0 and 100")
    
    def _validate_performance_config(self, performance: Dict[str, Any]):
        """Validate performance configuration."""
        if 'message_batch_size' in performance:
            batch_size = performance['message_batch_size']
            if not isinstance(batch_size, int) or not (1 <= batch_size <= 1000):
                raise ValidationError("performance.message_batch_size must be an integer between 1 and 1000")
        
        if 'ui_update_throttle_ms' in performance:
            throttle = performance['ui_update_throttle_ms']
            if not isinstance(throttle, int) or not (10 <= throttle <= 5000):
                raise ValidationError("performance.ui_update_throttle_ms must be an integer between 10 and 5000")
        
        if 'network_pool_size' in performance:
            pool_size = performance['network_pool_size']
            if not isinstance(pool_size, int) or not (1 <= pool_size <= 100):
                raise ValidationError("performance.network_pool_size must be an integer between 1 and 100")
        
        if 'cache_size_mb' in performance:
            cache_size = performance['cache_size_mb']
            if not isinstance(cache_size, (int, float)) or not (1 <= cache_size <= 1000):
                raise ValidationError("performance.cache_size_mb must be a number between 1 and 1000")
        
        if 'gc_interval_minutes' in performance:
            interval = performance['gc_interval_minutes']
            if not isinstance(interval, int) or not (1 <= interval <= 1440):
                raise ValidationError("performance.gc_interval_minutes must be an integer between 1 and 1440")
    
    def validate_runtime_secret_key(self, key: str):
        """
        Validate that a runtime secret key is acceptable.
        
        Args:
            key: Secret key name to validate
            
        Raises:
            ValidationError: If key name is invalid
        """
        if not isinstance(key, str) or not key.strip():
            raise ValidationError("Runtime secret key must be a non-empty string")
        
        # Key should be descriptive but not contain the actual secret
        if len(key) < 3:
            raise ValidationError("Runtime secret key must be at least 3 characters")
        
        if len(key) > 100:
            raise ValidationError("Runtime secret key must be at most 100 characters")
        
        # Should only contain safe characters
        if not re.match(r'^[a-zA-Z0-9_.-]+$', key):
            raise ValidationError("Runtime secret key can only contain letters, numbers, underscores, dots, and hyphens")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of validation rules for documentation.
        
        Returns:
            Validation rules summary
        """
        return {
            'forbidden_in_config_files': [
                'passwords', 'private_keys', 'secret_keys', 'tokens',
                'api_keys', 'credentials', 'certificates'
            ],
            'network_limits': {
                'relay_port': '1-65535',
                'connection_timeout': '>0 seconds',
                'retry_attempts': '0-100',
                'retry_delay': '>=0 seconds'
            },
            'ui_limits': {
                'port': '1-65535',
                'theme': ['light', 'dark', 'auto'],
                'language': 'ISO language codes (e.g., en, en-US)',
                'message_history_limit': '1-10000'
            },
            'storage_limits': {
                'backup_interval_hours': '1-8760 (1 year)',
                'max_backups': '0-100',
                'file_permissions': '0o000-0o777'
            },
            'security_limits': {
                'session_timeout_minutes': '1-10080 (1 week)',
                'max_login_attempts': '1-100',
                'lockout_duration_minutes': '1-1440 (24 hours)'
            },
            'logging_limits': {
                'level': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                'file_max_size_mb': '1-1000',
                'file_backup_count': '0-100'
            },
            'performance_limits': {
                'message_batch_size': '1-1000',
                'ui_update_throttle_ms': '10-5000',
                'network_pool_size': '1-100',
                'cache_size_mb': '1-1000',
                'gc_interval_minutes': '1-1440 (24 hours)'
            }
        }