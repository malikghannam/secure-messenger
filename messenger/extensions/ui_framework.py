"""
UI Framework Extension Interface

This module defines interfaces for future UI enhancements and extensibility.
The interfaces are designed to extend the existing Flask-based UI without
modifying the core UI controller or template system.

These interfaces are NOT implemented - they provide architectural hooks for
future development.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from enum import Enum


class UIComponentType(Enum):
    """Types of UI components that can be extended."""
    CHAT_BUBBLE = "chat_bubble"
    SIDEBAR_WIDGET = "sidebar_widget"
    TOOLBAR_BUTTON = "toolbar_button"
    STATUS_INDICATOR = "status_indicator"
    NOTIFICATION = "notification"
    MODAL_DIALOG = "modal_dialog"


class UITheme(Enum):
    """Available UI themes."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


class UIFrameworkInterface(ABC):
    """
    Interface for UI framework extensions.
    
    This interface defines how the UI system could be extended with new
    components, themes, and interaction patterns while maintaining the
    existing Flask-based architecture.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    @abstractmethod
    def register_component(
        self, 
        component_type: UIComponentType,
        component_id: str,
        render_function: Callable[..., str],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Register a new UI component.
        
        Args:
            component_type: Type of component being registered
            component_id: Unique identifier for the component
            render_function: Function that renders the component HTML
            metadata: Additional component configuration
            
        Returns:
            True if component was registered successfully
        """
        pass
    
    @abstractmethod
    def unregister_component(
        self, 
        component_type: UIComponentType,
        component_id: str
    ) -> bool:
        """
        Unregister a UI component.
        
        Args:
            component_type: Type of component to unregister
            component_id: ID of the component to remove
            
        Returns:
            True if component was unregistered successfully
        """
        pass
    
    @abstractmethod
    def render_component(
        self, 
        component_type: UIComponentType,
        component_id: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a registered UI component.
        
        Args:
            component_type: Type of component to render
            component_id: ID of the component to render
            context: Rendering context data
            
        Returns:
            Rendered HTML for the component
        """
        pass
    
    @abstractmethod
    def set_theme(self, theme: UITheme, theme_config: Dict[str, Any]) -> bool:
        """
        Set the active UI theme.
        
        Args:
            theme: Theme to activate
            theme_config: Theme-specific configuration
            
        Returns:
            True if theme was set successfully
        """
        pass
    
    @abstractmethod
    def get_available_themes(self) -> List[Dict[str, Any]]:
        """
        Get list of available UI themes.
        
        Returns:
            List of theme information dictionaries
        """
        pass
    
    @abstractmethod
    def register_keyboard_shortcut(
        self, 
        shortcut: str,
        action_id: str,
        callback: Callable[[], None]
    ) -> bool:
        """
        Register a keyboard shortcut.
        
        Args:
            shortcut: Key combination (e.g., "Ctrl+N")
            action_id: Unique identifier for the action
            callback: Function to call when shortcut is pressed
            
        Returns:
            True if shortcut was registered successfully
        """
        pass
    
    @abstractmethod
    def add_context_menu_item(
        self, 
        context: str,
        item_id: str,
        label: str,
        callback: Callable[..., None]
    ) -> bool:
        """
        Add an item to a context menu.
        
        Args:
            context: Context where menu appears (e.g., "message", "user")
            item_id: Unique identifier for the menu item
            label: Display text for the menu item
            callback: Function to call when item is selected
            
        Returns:
            True if menu item was added successfully
        """
        pass


class UIExtensionHooks:
    """
    Hook system for UI extension events.
    
    This class provides hooks that would be called during UI interactions,
    allowing extensions to respond to user actions and UI state changes
    without modifying the core UI controller.
    
    NOT IMPLEMENTED - This is an architectural extension point.
    """
    
    def __init__(self):
        """Initialize UI extension hooks."""
        self._callbacks = {
            'message_rendered': None,
            'chat_opened': None,
            'chat_closed': None,
            'user_action': None,
            'theme_changed': None,
            'component_loaded': None,
            'shortcut_pressed': None
        }
    
    def register_message_rendered_hook(
        self, 
        callback: Callable[[str, str, Dict[str, Any]], None]
    ):
        """
        Register callback for when a message is rendered.
        
        Args:
            callback: Function called with (peer, message_id, message_data)
        """
        self._callbacks['message_rendered'] = callback
    
    def register_chat_opened_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for when a chat is opened.
        
        Args:
            callback: Function called with (peer,)
        """
        self._callbacks['chat_opened'] = callback
    
    def register_chat_closed_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for when a chat is closed.
        
        Args:
            callback: Function called with (peer,)
        """
        self._callbacks['chat_closed'] = callback
    
    def register_user_action_hook(
        self, 
        callback: Callable[[str, Dict[str, Any]], None]
    ):
        """
        Register callback for user actions.
        
        Args:
            callback: Function called with (action_type, action_data)
        """
        self._callbacks['user_action'] = callback
    
    def register_theme_changed_hook(
        self, 
        callback: Callable[[UITheme, Dict[str, Any]], None]
    ):
        """
        Register callback for when theme changes.
        
        Args:
            callback: Function called with (new_theme, theme_config)
        """
        self._callbacks['theme_changed'] = callback
    
    def register_shortcut_pressed_hook(
        self, 
        callback: Callable[[str], None]
    ):
        """
        Register callback for keyboard shortcuts.
        
        Args:
            callback: Function called with (shortcut,)
        """
        self._callbacks['shortcut_pressed'] = callback