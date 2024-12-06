"""Bluetooth button wake trigger implementation."""
import threading
from dataclasses import dataclass, field
from typing import Optional
import asyncio
from bleak import BleakScanner, BleakClient
from .base import WakeTrigger, TriggerConfig

@dataclass
class BluetoothTriggerConfig:
    """Configuration for Bluetooth trigger."""
    device_name: str  # Name of the Bluetooth device to connect to
    characteristic_uuid: str  # UUID of the characteristic to monitor
    _enabled: bool = field(default=True)  # Internal field
    device_address: str = field(default="")  # MAC address of the device (optional, can be discovered)
    button_press_value: bytes = field(default=b'\x01')  # Value that indicates button press
    
    @property
    def enabled(self) -> bool:
        """Get enabled state."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled state."""
        self._enabled = value

class BluetoothTrigger(WakeTrigger):
    """Bluetooth button wake trigger."""
    
    def __init__(self, config: Optional[BluetoothTriggerConfig] = None):
        """Initialize the Bluetooth trigger."""
        super().__init__(config or BluetoothTriggerConfig())
        self.config: BluetoothTriggerConfig = self.config  # type: ignore
        self._client: Optional[BleakClient] = None
        self._scanner: Optional[BleakScanner] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    async def _notification_handler(self, sender: int, data: bytes) -> None:
        """Handle notifications from the Bluetooth device."""
        if data == self.config.button_press_value:
            self.notify_wake()
    
    async def _connect_and_monitor(self) -> None:
        """Connect to the device and monitor for button presses."""
        try:
            # Scan for device if address not provided
            if not self.config.device_address:
                print(f"Scanning for Bluetooth device '{self.config.device_name}'...")
                device = await BleakScanner.find_device_by_name(
                    self.config.device_name, timeout=20.0
                )
                if not device:
                    print(f"Could not find device '{self.config.device_name}'")
                    return
                self.config.device_address = device.address
            
            print(f"Connecting to {self.config.device_address}...")
            async with BleakClient(self.config.device_address) as client:
                self._client = client
                print(f"Connected to {client.address}")
                
                # Start notification monitoring
                await client.start_notify(
                    self.config.characteristic_uuid,
                    self._notification_handler
                )
                
                # Keep connection alive until stopped
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.1)
                
                await client.stop_notify(self.config.characteristic_uuid)
                
        except Exception as e:
            print(f"Bluetooth error: {e}")
        finally:
            self._client = None
    
    def _run_bluetooth_loop(self) -> None:
        """Run the Bluetooth event loop in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_and_monitor())
        loop.close()
    
    def _start_impl(self) -> None:
        """Start monitoring for Bluetooth button presses."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_bluetooth_loop)
            self._thread.daemon = True
            self._thread.start()
    
    def _stop_impl(self) -> None:
        """Stop monitoring for Bluetooth button presses."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
    
    @property
    def is_active(self) -> bool:
        """Return whether the Bluetooth trigger is currently active."""
        return bool(self._thread and self._thread.is_alive())
