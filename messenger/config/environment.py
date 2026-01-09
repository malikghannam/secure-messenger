"""
Environment Detection and Management

Detects the current environment (development, production, testing) and
provides environment-specific configuration without changing behavior.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional


class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class EnvironmentDetector:
    """
    Detects the current environment based on various indicators.
    
    Uses multiple detection methods to reliably determine the environment
    without relying on secrets or sensitive information.
    """
    
    def __init__(self):
        """Initialize environment detector."""
        self._cached_environment: Optional[Environment] = None
    
    def detect_environment(self) -> Environment:
        """
        Detect the current environment.
        
        Returns:
            Detected environment
        """
        if self._cached_environment is not None:
            return self._cached_environment
        
        # Method 1: Explicit environment variable
        env_var = os.environ.get('MESSENGER_ENV', '').lower()
        if env_var in ['development', 'dev']:
            self._cached_environment = Environment.DEVELOPMENT
        elif env_var in ['production', 'prod']:
            self._cached_environment = Environment.PRODUCTION
        elif env_var in ['testing', 'test']:
            self._cached_environment = Environment.TESTING
        
        # Method 2: Common CI/CD environment indicators
        elif self._is_ci_environment():
            self._cached_environment = Environment.TESTING
        
        # Method 3: Development indicators
        elif self._is_development_environment():
            self._cached_environment = Environment.DEVELOPMENT
        
        # Method 4: Production indicators
        elif self._is_production_environment():
            self._cached_environment = Environment.PRODUCTION
        
        # Default: Development (safe default)
        else:
            self._cached_environment = Environment.DEVELOPMENT
        
        return self._cached_environment
    
    def _is_ci_environment(self) -> bool:
        """Check if running in CI/CD environment."""
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS',
            'TRAVIS', 'CIRCLECI', 'JENKINS_URL', 'GITLAB_CI'
        ]
        return any(os.environ.get(var) for var in ci_indicators)
    
    def _is_development_environment(self) -> bool:
        """Check if running in development environment."""
        dev_indicators = [
            # Development tools
            os.environ.get('FLASK_ENV') == 'development',
            os.environ.get('DEBUG') == '1',
            
            # Development paths
            os.path.exists('.git'),
            os.path.exists('requirements-dev.txt'),
            os.path.exists('pyproject.toml'),
            
            # Local development
            os.environ.get('USER') in ['developer', 'dev'],
            'localhost' in os.environ.get('HOSTNAME', ''),
        ]
        return any(dev_indicators)
    
    def _is_production_environment(self) -> bool:
        """Check if running in production environment."""
        prod_indicators = [
            # Production environment variables
            os.environ.get('FLASK_ENV') == 'production',
            os.environ.get('NODE_ENV') == 'production',
            
            # Container/cloud indicators
            os.path.exists('/.dockerenv'),
            os.environ.get('KUBERNETES_SERVICE_HOST'),
            os.environ.get('AWS_EXECUTION_ENV'),
            
            # System indicators
            os.path.exists('/etc/systemd'),
            os.environ.get('USER') in ['www-data', 'app', 'messenger'],
        ]
        return any(prod_indicators)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get detailed environment information for debugging.
        
        Returns:
            Environment information (no sensitive data)
        """
        env = self.detect_environment()
        
        return {
            'environment': env.value,
            'detection_method': self._get_detection_method(),
            'indicators': {
                'is_ci': self._is_ci_environment(),
                'is_development': self._is_development_environment(),
                'is_production': self._is_production_environment(),
            },
            'safe_env_vars': {
                'MESSENGER_ENV': os.environ.get('MESSENGER_ENV'),
                'FLASK_ENV': os.environ.get('FLASK_ENV'),
                'NODE_ENV': os.environ.get('NODE_ENV'),
                'CI': bool(os.environ.get('CI')),
            }
        }
    
    def _get_detection_method(self) -> str:
        """Get the method used to detect the environment."""
        env_var = os.environ.get('MESSENGER_ENV')
        if env_var:
            return f"explicit_env_var:{env_var}"
        elif self._is_ci_environment():
            return "ci_indicators"
        elif self._is_development_environment():
            return "development_indicators"
        elif self._is_production_environment():
            return "production_indicators"
        else:
            return "default_fallback"


# Global environment detector instance
_environment_detector = EnvironmentDetector()


def get_environment() -> Environment:
    """
    Get the current environment.
    
    Returns:
        Current environment
    """
    return _environment_detector.detect_environment()


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == Environment.DEVELOPMENT


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == Environment.PRODUCTION


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_environment() == Environment.TESTING


def get_environment_info() -> Dict[str, Any]:
    """Get detailed environment information."""
    return _environment_detector.get_environment_info()