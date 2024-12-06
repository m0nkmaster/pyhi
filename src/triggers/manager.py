"""Manager for handling multiple wake triggers."""
from typing import List, Callable, Optional
from .base import WakeTrigger

class TriggerManager:
    """Manages multiple wake triggers."""
    
    def __init__(self):
        """Initialize the trigger manager."""
        self.triggers: List[WakeTrigger] = []
        self._wake_callback: Optional[Callable[[], None]] = None
    
    def add_trigger(self, trigger: WakeTrigger) -> None:
        """Add a wake trigger to manage."""
        trigger.set_wake_callback(self._on_wake)
        self.triggers.append(trigger)
    
    def set_wake_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to be called when any trigger activates."""
        self._wake_callback = callback
    
    def _on_wake(self) -> None:
        """Handle wake trigger activation."""
        if self._wake_callback:
            self._wake_callback()
    
    def start_all(self) -> None:
        """Start all wake triggers."""
        for trigger in self.triggers:
            trigger.start()
    
    def stop_all(self) -> None:
        """Stop all wake triggers."""
        for trigger in self.triggers:
            trigger.stop()
    
    @property
    def any_active(self) -> bool:
        """Return whether any trigger is currently active."""
        return any(trigger.is_active for trigger in self.triggers)
