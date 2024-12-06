"""Test script for Bluetooth button functionality."""
import asyncio
from bleak import BleakScanner, BleakClient
import sys

async def scan_devices():
    """Scan for available Bluetooth devices."""
    print("Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    if not devices:
        print("No devices found!")
        return
    
    print("\nFound devices:")
    for i, device in enumerate(devices):
        print(f"{i+1}. Name: {device.name or 'Unknown'}")
        print(f"   Address: {device.address}")
        print(f"   RSSI: {device.rssi}dBm")
        print()
    
    return devices

async def inspect_device(address: str):
    """Inspect a specific device's services and characteristics."""
    try:
        async with BleakClient(address) as client:
            print(f"\nConnected to {address}")
            
            # Get all services
            services = await client.get_services()
            
            print("\nAvailable services and characteristics:")
            for service in services:
                print(f"\nService: {service.uuid}")
                for char in service.characteristics:
                    print(f"  Characteristic: {char.uuid}")
                    print(f"    Properties: {', '.join(char.properties)}")
                    try:
                        if "read" in char.properties:
                            value = await client.read_gatt_char(char.uuid)
                            print(f"    Current value: {value}")
                    except Exception as e:
                        print(f"    Error reading value: {e}")
    
    except Exception as e:
        print(f"Error connecting to device: {e}")

async def monitor_characteristic(address: str, characteristic_uuid: str):
    """Monitor a specific characteristic for notifications."""
    def notification_handler(_, data: bytes):
        print(f"Received data: {data}")
    
    try:
        async with BleakClient(address) as client:
            print(f"\nConnected to {address}")
            print(f"Monitoring characteristic {characteristic_uuid}")
            print("Press Ctrl+C to stop...")
            
            await client.start_notify(characteristic_uuid, notification_handler)
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1.0)
    
    except Exception as e:
        print(f"Error: {e}")

async def main():
    """Main function."""
    if len(sys.argv) == 1:
        # Just scan for devices
        await scan_devices()
    
    elif len(sys.argv) == 2:
        # Inspect specific device
        address = sys.argv[1]
        await inspect_device(address)
    
    elif len(sys.argv) == 3:
        # Monitor specific characteristic
        address = sys.argv[1]
        characteristic = sys.argv[2]
        await monitor_characteristic(address, characteristic)
    
    else:
        print("Usage:")
        print("  python test_bluetooth.py                    # Scan for devices")
        print("  python test_bluetooth.py ADDRESS           # Inspect device")
        print("  python test_bluetooth.py ADDRESS CHAR_UUID # Monitor characteristic")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
