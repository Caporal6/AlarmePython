# test_hardware.py
import interface_1

print(f"Hardware available: {interface_1.HARDWARE_AVAILABLE}")
print(f"Has get_sensor_data: {hasattr(interface_1, 'get_sensor_data')}")

if hasattr(interface_1, 'get_sensor_data'):
    data = interface_1.get_sensor_data()
    print(f"Sensor data: {data}")

if interface_1.HARDWARE_AVAILABLE:
    print("Testing LED...")
    interface_1.led.on()
    import time
    time.sleep(1)
    interface_1.led.off()
    print("LED test complete")