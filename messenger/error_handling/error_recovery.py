"""
Error Recovery Manager

Provides automated error recovery strategies for different types of failures.
Implements graceful degradation and recovery mechanisms.
"""

from typing import Dict, Any, Optional, Callable, List
import time
import asyncio
from enum import Enum
from .error_categories import MessengerError, CryptoError, NetworkError, StorageError
from .secure_logger import secure_logger


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    RESET = "reset"
    IGNORE = "ignore"
    ESCALATE = "escalate"


class RecoveryAction:
    """Represents a recovery action for a specific error type."""
    
    def __init__(
        self,
        strategy: RecoveryStrategy,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 30.0,
        fallback_action: Optional[Callable] = None
    ):
        """
        Initialize recovery action.
        
        Args:
            strategy: Recovery strategy to use
            max_attempts: Maximum retry attempts
            delay: Initial delay between attempts
            backoff_multiplier: Exponential backoff multiplier
            max_delay: Maximum delay between attempts
            fallback_action: Fallback function to call if recovery fails
        """
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay
        self.fallback_action = fallback_action


class ErrorRecoveryManager:
    """
    Manages error recovery strategies and automatic recovery attempts.
    
    Provides centralized error recovery with configurable strategies
    for different error types and scenarios.
    """
    
    def __init__(self):
        """Initialize error recovery manager."""
        self.recovery_strategies: Dict[type, RecoveryAction] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        """Setup default recovery strategies for common error types."""
        
        # Network errors: Retry with exponential backoff
        self.recovery_strategies[NetworkError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=5,
            delay=1.0,
            backoff_multiplier=2.0,
            max_delay=30.0
        )
        
        # Storage errors: Retry with shorter delays, then fallback
        self.recovery_strategies[StorageError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            delay=0.5,
            backoff_multiplier=1.5,
            max_delay=5.0
        )
        
        # Crypto errors: Usually not recoverable, escalate
        self.recovery_strategies[CryptoError] = RecoveryAction(
            strategy=RecoveryStrategy.ESCALATE,
            max_attempts=1
        )
        
        # Generic messenger errors: Retry once, then escalate
        self.recovery_strategies[MessengerError] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=2,
            delay=1.0
        )
    
    def register_strategy(self, error_type: type, action: RecoveryAction):
        """
        Register a recovery strategy for an error type.
        
        Args:
            error_type: Exception type to handle
            action: Recovery action to take
        """
        self.recovery_strategies[error_type] = action
        secure_logger.debug(
            "Registered recovery strategy for {error_type}: {strategy}",
            error_type=error_type.__name__,
            strategy=action.strategy.value
        )
    
    def recover(
        self, 
        error: Exception, 
        operation: Callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Attempt to recover from an error by retrying the operation.
        
        Args:
            error: The error that occurred
            operation: The operation to retry
            context: Additional context for recovery
            
        Returns:
            Result of successful operation
            
        Raises:
            The original error if recovery fails
        """
        error_type = type(error)
        strategy = self._get_strategy_for_error(error_type)
        
        if strategy.strategy == RecoveryStrategy.IGNORE:
            secure_logger.debug("Ignoring error as per strategy: {error_type}", 
                              error_type=error_type.__name__)
            return None
        
        if strategy.strategy == RecoveryStrategy.ESCALATE:
            secure_logger.warning("Escalating error as per strategy: {error_type}",
                                error_type=error_type.__name__)
            raise error
        
        if strategy.strategy == RecoveryStrategy.RETRY:
            return self._retry_operation(error, operation, strategy, context)
        
        if strategy.strategy == RecoveryStrategy.FALLBACK:
            return self._fallback_operation(error, strategy, context)
        
        if strategy.strategy == RecoveryStrategy.RESET:
            return self._reset_and_retry(error, operation, strategy, context)
        
        # Default: escalate unknown strategies
        raise error
    
    def _get_strategy_for_error(self, error_type: type) -> RecoveryAction:
        """Get recovery strategy for error type, checking inheritance."""
        # Check exact type match first
        if error_type in self.recovery_strategies:
            return self.recovery_strategies[error_type]
        
        # Check parent classes
        for registered_type, strategy in self.recovery_strategies.items():
            if issubclass(error_type, registered_type):
                return strategy
        
        # Default strategy: retry once
        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=1,
            delay=1.0
        )
    
    def _retry_operation(
        self, 
        error: Exception, 
        operation: Callable,
        strategy: RecoveryAction,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Retry operation with exponential backoff."""
        last_error = error
        delay = strategy.delay
        
        for attempt in range(strategy.max_attempts):
            secure_logger.info(
                "Retrying operation (attempt {attempt}/{max_attempts}) after {error_type}",
                attempt=attempt + 1,
                max_attempts=strategy.max_attempts,
                error_type=type(error).__name__
            )
            
            if attempt > 0:  # Don't delay on first retry
                time.sleep(delay)
                delay = min(delay * strategy.backoff_multiplier, strategy.max_delay)
            
            try:
                result = operation()
                
                # Log successful recovery
                self._log_recovery_success(error, attempt + 1, context)
                return result
                
            except Exception as retry_error:
                last_error = retry_error
                secure_logger.debug(
                    "Retry attempt {attempt} failed: {error_type}",
                    attempt=attempt + 1,
                    error_type=type(retry_error).__name__
                )
        
        # All retries failed
        self._log_recovery_failure(error, strategy.max_attempts, context)
        raise last_error
    
    def _fallback_operation(
        self, 
        error: Exception, 
        strategy: RecoveryAction,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute fallback operation."""
        if strategy.fallback_action:
            secure_logger.info(
                "Executing fallback action for {error_type}",
                error_type=type(error).__name__
            )
            try:
                result = strategy.fallback_action(error, context)
                self._log_recovery_success(error, 1, context, "fallback")
                return result
            except Exception as fallback_error:
                secure_logger.error(
                    "Fallback action failed: {error_type}",
                    error_type=type(fallback_error).__name__
                )
                raise fallback_error
        else:
            secure_logger.warning(
                "No fallback action configured for {error_type}",
                error_type=type(error).__name__
            )
            raise error
    
    def _reset_and_retry(
        self, 
        error: Exception, 
        operation: Callable,
        strategy: RecoveryAction,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Reset state and retry operation."""
        secure_logger.info(
            "Resetting state and retrying after {error_type}",
            error_type=type(error).__name__
        )
        
        # Perform reset logic here (implementation depends on context)
        # For now, just retry with a longer delay
        time.sleep(strategy.delay * 2)
        
        try:
            result = operation()
            self._log_recovery_success(error, 1, context, "reset")
            return result
        except Exception as reset_error:
            self._log_recovery_failure(error, 1, context)
            raise reset_error
    
    def _log_recovery_success(
        self, 
        original_error: Exception, 
        attempts: int,
        context: Optional[Dict[str, Any]],
        method: str = "retry"
    ):
        """Log successful recovery."""
        recovery_record = {
            'timestamp': time.time(),
            'error_type': type(original_error).__name__,
            'recovery_method': method,
            'attempts': attempts,
            'success': True
        }
        
        self.recovery_history.append(recovery_record)
        
        secure_logger.info(
            "Recovery successful: {error_type} resolved after {attempts} attempts using {method}",
            error_type=recovery_record['error_type'],
            attempts=attempts,
            method=method
        )
    
    def _log_recovery_failure(
        self, 
        original_error: Exception, 
        attempts: int,
        context: Optional[Dict[str, Any]]
    ):
        """Log failed recovery."""
        recovery_record = {
            'timestamp': time.time(),
            'error_type': type(original_error).__name__,
            'recovery_method': 'retry',
            'attempts': attempts,
            'success': False
        }
        
        self.recovery_history.append(recovery_record)
        
        secure_logger.warning(
            "Recovery failed: {error_type} could not be resolved after {attempts} attempts",
            error_type=recovery_record['error_type'],
            attempts=attempts
        )
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {'total_recoveries': 0, 'success_rate': 0.0}
        
        total = len(self.recovery_history)
        successful = sum(1 for record in self.recovery_history if record['success'])
        
        error_types = {}
        for record in self.recovery_history:
            error_type = record['error_type']
            if error_type not in error_types:
                error_types[error_type] = {'total': 0, 'successful': 0}
            error_types[error_type]['total'] += 1
            if record['success']:
                error_types[error_type]['successful'] += 1
        
        return {
            'total_recoveries': total,
            'successful_recoveries': successful,
            'success_rate': successful / total if total > 0 else 0.0,
            'error_type_stats': error_types
        }


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()