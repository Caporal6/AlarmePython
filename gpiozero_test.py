#!/usr/bin/env python3
"""
Simple script to test if gpiozero is working properly
"""

print("Testing gpiozero installation...")

try:
    import gpiozero
    print("gpiozero successfully imported")
    
    # Print version info if available
    try:
        print(f"Version: {gpiozero.__version__}")
    except AttributeError:
        print("Version info not available")
    
    # Try importing specific classes
    from gpiozero import LED, Buzzer, AngularServo
    print("LED, Buzzer, AngularServo classes successfully imported")
    
    # Check if the LED class exists and what its methods are
    print("\nLED class methods:")
    print(dir(LED))
    
    # Test if we can create an LED object
    try:
        print("\nCreating LED on pin 6...")
        led = LED(6)
        print("LED object created successfully")
        
        print("Turning LED on...")
        led.on()
        
        import time
        print("Waiting 1 second...")
        time.sleep(1)
        
        print("Turning LED off...")
        led.off()
        print("LED test complete!")
        
    except Exception as e:
        print(f"Error creating/using LED: {e}")
    
except ImportError as e:
    print(f"Error importing gpiozero: {e}")
    print("Make sure gpiozero is installed with: pip install gpiozero")