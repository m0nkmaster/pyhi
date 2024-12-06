"""Base classes for wake triggers."""
from abc import ABC, abstractmethod
from typing import Optional, Callable, Protocol
from dataclasses import dataclass, field

class HasEnabled(Protocol):
    """Protocol for objects with enabled property."""
    @property
    def enabled(self) -> bool: ...
    @enabled.setter
    def enabled(self, value: bool) -> None: ...

@dataclass
class TriggerConfig:
    """Base configuration for triggers."""
    _enabled: bool = field(default=True)  # Internal field
    
    @property
    def enabled(self) -> bool:
        """Get enabled state."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled state."""
        self._enabled = value

class WakeTrigger(ABC):
    """Base class for wake triggers."""
    
    def __init__(self, config: HasEnabled):
        """Initialize the trigger."""
        self.config = config
        self._callback: Optional[Callable[[], None]] = None
    
    def set_wake_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to be called when the trigger activates."""
        self._callback = callback
    
    def notify_wake(self) -> None:
        """Notify that the trigger has been activated."""
        if self._callback:
            self._callback()
    
    def start(self) -> None:
        """Start listening for wake triggers."""
        if not self.config.enabled:
            return
        self._start_impl()
    
    @abstractmethod
    def _start_impl(self) -> None:
        """Implementation of start method."""
        pass
    
    def stop(self) -> None:
        """Stop listening for wake triggers."""
        if not self.config.enabled:
            return
        self._stop_impl()
    
    @abstractmethod
    def _stop_impl(self) -> None:
        """Implementation of stop method."""
        pass
    
    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Return whether the trigger is currently active."""
        pass
