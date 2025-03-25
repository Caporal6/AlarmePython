#!/usr/bin/env python3
# Pi5 Hardware Test Script

import sys
import time
import os

print(f"Python version: {sys.version}")
print(f"Running as user: {os.getlogin()}")

print("\nChecking for Raspberry Pi 5...")
pi5_detected = False
try:
    with open('/proc/device-tree/model', 'r') as f:
        model = f.read()
        pi5_detected = 'Raspberry Pi 5' in model
        print(f"System model: {model.strip()}")
except Exception as e:
    print(f"Error checking Pi model: {e}")

print(f"Pi 5 detected: {pi5_detected}")

print("\nTrying direct GPIO access...")
try:
    import RPi.GPIO as GPIO
    print("RPi.GPIO module imported successfully")
    
    # Set up GPIO mode
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Test with LED on pin 6 (or whichever pin you have an LED connected to)
    LED_PIN = 6
    
    print(f"Setting up pin {LED_PIN} as output")
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    print(f"Turning LED ON (pin {LED_PIN})")
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(2)
    
    print(f"Turning LED OFF (pin {LED_PIN})")
    GPIO.output(LED_PIN, GPIO.LOW)
    
    # Also test buzzer if connected
    BUZZER_PIN = 18
    print(f"Setting up buzzer on pin {BUZZER_PIN}")
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    
    print("Testing buzzer")
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    
    GPIO.cleanup()
    print("GPIO test completed successfully")
except Exception as e:
    print(f"Error with GPIO: {e}")

print("\nTrying pinctrl command...")
try:
    import subprocess
    result = subprocess.run(["pinctrl", "get"], capture_output=True, text=True)
    print(f"pinctrl status: {result.returncode}")
    if result.returncode == 0:
        print("pinctrl output (first 10 lines):")
        for line in result.stdout.split('\n')[:10]:
            print(f"  {line}")
    else:
        print(f"pinctrl error: {result.stderr}")
except Exception as e:
    print(f"Error running pinctrl: {e}")