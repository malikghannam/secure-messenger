"""
Graceful Degradation Manager

Provides graceful degradation strategies for various failure scenarios.
Ensures the application continues to function even when some components fail.
"""

from typing import Dict, Any, Optional, Callable, Set
from enum import Enum
import threading
from .secure_logger import secure_logger


class ComponentStatus(Enum):
    """Component status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class DegradationLevel(Enum):
    """System degradation levels."""
    NORMAL = "normal"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class ComponentHealth:
    """Tracks health status of a system component."""
    
    def __init__(self, name: str, essential: bool = False):
        """
        Initialize component health tracker.
        
        Args:
            name: Component name
            essential: Whether component is essential for core functionality
        """
        self.name = name
        self.essential = essential
        self.status = ComponentStatus.HEALTHY
        self.last_error: Optional[Exception] = None
        self.error_count = 0
        self.last_check = 0.0
        self.degraded_features: Set[str] = set()
    
    def mark_healthy(self):
        """Mark component as healthy."""
        self.status = ComponentStatus.HEALTHY
        self.error_count = 0
        self.last_error = None
        self.degraded_features.clear()
        secure_logger.debug("Component {name} marked as healthy", name=self.name)
    
    def mark_degraded(self, features: Optional[Set[str]] = None):
        """Mark component as degraded."""
        self.status = ComponentStatus.DEGRADED
        if features:
            self.degraded_features.update(features)
        secure_logger.warning(
            "Component {name} marked as degraded, affected features: {features}",
            name=self.name,
            features=list(self.degraded_features)
        )
    
    def mark_failed(self, error: Optional[Exception] = None):
        """Mark component as failed."""
        self.status = ComponentStatus.FAILED
        self.error_count += 1
        if error:
            self.last_error = error
        secure_logger.error(
            "Component {name} marked as failed (error count: {count})",
            name=self.name,
            count=self.error_count
        )
    
    def disable(self):
        """Disable component."""
        self.status = ComponentStatus.DISABLED
        secure_logger.info("Component {name} disabled", name=self.name)


class GracefulDegradationManager:
    """
    Manages graceful degradation of system functionality.
    
    Monitors component health and provides fallback strategies
    when components fail or become unavailable.
    """
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self.components: Dict[str, ComponentHealth] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
        self.feature_dependencies: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._setup_core_components()
    
    def _setup_core_components(self):
        """Setup core system components."""
        # Essential components
        self.register_component("crypto", essential=True)
        self.register_component("storage", essential=True)
        self.register_component("session_manager", essential=True)
        
        # Non-essential components
        self.register_component("transport", essential=False)
        self.register_component("websocket", essential=False)
        self.register_component("ui", essential=False)
        
        # Setup feature dependencies
        self.feature_dependencies = {
            "send_message": {"crypto", "session_manager", "transport"},
            "receive_message": {"crypto", "session_manager", "storage"},
            "real_time_notifications": {"websocket", "transport"},
            "message_history": {"storage", "session_manager"},
            "user_interface": {"ui", "storage"},
            "session_management": {"crypto", "session_manager", "storage"}
        }
    
    def register_component(self, name: str, essential: bool = False) -> ComponentHealth:
        """
        Register a system component for health monitoring.
        
        Args:
            name: Component name
            essential: Whether component is essential
            
        Returns:
            ComponentHealth instance
        """
        with self._lock:
            component = ComponentHealth(name, essential)
            self.components[name] = component
            secure_logger.debug(
                "Registered component {name} (essential: {essential})",
                name=name,
                essential=essential
            )
            return component
    
    def register_fallback(self, component_name: str, fallback_func: Callable):
        """
        Register a fallback strategy for a component.
        
        Args:
            component_name: Name of the component
            fallback_func: Fallback function to call when component fails
        """
        with self._lock:
            self.fallback_strategies[component_name] = fallback_func
            secure_logger.debug(
                "Registered fallback strategy for component {name}",
                name=component_name
            )
    
    def report_component_error(self, component_name: str, error: Exception):
        """
        Report an error in a component.
        
        Args:
            component_name: Name of the component
            error: The error that occurred
        """
        with self._lock:
            if component_name not in self.components:
                secure_logger.warning(
                    "Error reported for unknown component: {name}",
                    name=component_name
                )
                return
            
            component = self.components[component_name]
            component.mark_failed(error)
            
            # Determine degradation strategy
            self._handle_component_failure(component_name, error)
    
    def _handle_component_failure(self, component_name: str, error: Exception):
        """Handle component failure with appropriate degradation."""
        component = self.components[component_name]
        
        if component.essential:
            # Essential component failure - major degradation
            secure_logger.critical(
                "Essential component {name} failed - system degradation required",
                name=component_name
            )
            self._degrade_dependent_features(component_name)
        else:
            # Non-essential component - try fallback
            if component_name in self.fallback_strategies:
                secure_logger.info(
                    "Attempting fallback for failed component {name}",
                    name=component_name
                )
                try:
                    self.fallback_strategies[component_name](error)
                    component.mark_degraded()
                except Exception as fallback_error:
                    secure_logger.error(
                        "Fallback failed for component {name}: {error}",
                        name=component_name,
                        error=str(fallback_error)
                    )
                    self._degrade_dependent_features(component_name)
            else:
                self._degrade_dependent_features(component_name)
    
    def _degrade_dependent_features(self, failed_component: str):
        """Degrade features that depend on the failed component."""
        affected_features = []
        
        for feature, dependencies in self.feature_dependencies.items():
            if failed_component in dependencies:
                affected_features.append(feature)
        
        if affected_features:
            secure_logger.warning(
                "Features affected by {component} failure: {features}",
                component=failed_component,
                features=affected_features
            )
            
            # Mark component as degraded with affected features
            component = self.components[failed_component]
            component.mark_degraded(set(affected_features))
    
    def is_feature_available(self, feature_name: str) -> bool:
        """
        Check if a feature is currently available.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            True if feature is available, False otherwise
        """
        with self._lock:
            if feature_name not in self.feature_dependencies:
                return True  # Unknown features are assumed available
            
            dependencies = self.feature_dependencies[feature_name]
            
            for dep in dependencies:
                if dep not in self.components:
                    continue
                
                component = self.components[dep]
                if component.status == ComponentStatus.FAILED:
                    return False
                elif component.status == ComponentStatus.DISABLED:
                    return False
            
            return True
    
    def get_degradation_level(self) -> DegradationLevel:
        """
        Get current system degradation level.
        
        Returns:
            Current degradation level
        """
        with self._lock:
            failed_essential = 0
            failed_non_essential = 0
            total_essential = 0
            total_non_essential = 0
            
            for component in self.components.values():
                if component.essential:
                    total_essential += 1
                    if component.status == ComponentStatus.FAILED:
                        failed_essential += 1
                else:
                    total_non_essential += 1
                    if component.status == ComponentStatus.FAILED:
                        failed_non_essential += 1
            
            # Determine degradation level
            if failed_essential > 0:
                if failed_essential >= total_essential * 0.5:
                    return DegradationLevel.CRITICAL
                else:
                    return DegradationLevel.MAJOR
            elif failed_non_essential > 0:
                if failed_non_essential >= total_non_essential * 0.5:
                    return DegradationLevel.MAJOR
                else:
                    return DegradationLevel.MINOR
            else:
                return DegradationLevel.NORMAL
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            System status information
        """
        with self._lock:
            component_statuses = {}
            for name, component in self.components.items():
                component_statuses[name] = {
                    'status': component.status.value,
                    'essential': component.essential,
                    'error_count': component.error_count,
                    'degraded_features': list(component.degraded_features)
                }
            
            available_features = {}
            for feature in self.feature_dependencies:
                available_features[feature] = self.is_feature_available(feature)
            
            return {
                'degradation_level': self.get_degradation_level().value,
                'components': component_statuses,
                'available_features': available_features,
                'total_components': len(self.components),
                'healthy_components': sum(
                    1 for c in self.components.values() 
                    if c.status == ComponentStatus.HEALTHY
                ),
                'failed_components': sum(
                    1 for c in self.components.values() 
                    if c.status == ComponentStatus.FAILED
                )
            }
    
    def attempt_recovery(self, component_name: str) -> bool:
        """
        Attempt to recover a failed component.
        
        Args:
            component_name: Name of the component to recover
            
        Returns:
            True if recovery was successful, False otherwise
        """
        with self._lock:
            if component_name not in self.components:
                return False
            
            component = self.components[component_name]
            if component.status == ComponentStatus.HEALTHY:
                return True  # Already healthy
            
            secure_logger.info(
                "Attempting recovery for component {name}",
                name=component_name
            )
            
            # Basic recovery attempt - mark as healthy and see if it works
            # In a real implementation, this would include specific recovery logic
            component.mark_healthy()
            
            return True
    
    def get_user_facing_status(self) -> Dict[str, Any]:
        """
        Get user-friendly system status information.
        
        Returns:
            User-friendly status information
        """
        degradation = self.get_degradation_level()
        available_features = {
            feature: self.is_feature_available(feature)
            for feature in self.feature_dependencies
        }
        
        # Create user-friendly messages
        if degradation == DegradationLevel.NORMAL:
            status_message = "All systems operational"
            status_color = "green"
        elif degradation == DegradationLevel.MINOR:
            status_message = "Minor service disruption - some features may be limited"
            status_color = "yellow"
        elif degradation == DegradationLevel.MAJOR:
            status_message = "Service disruption - reduced functionality"
            status_color = "orange"
        else:  # CRITICAL
            status_message = "Major service disruption - core features affected"
            status_color = "red"
        
        return {
            'status_message': status_message,
            'status_color': status_color,
            'degradation_level': degradation.value,
            'available_features': available_features
        }


# Global graceful degradation manager instance
graceful_degradation_manager = GracefulDegradationManager()