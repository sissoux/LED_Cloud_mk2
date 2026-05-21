"""
Test script to verify PWM inversion is working correctly
With INVERT_WHITE_PWM enabled, the white strips should now behave normally:
- 0% command = 0% light (was 100% before)
- 100% command = 100% light (was 0% before)
"""

import serial
import json
import time

# Serial port configuration
SERIAL_PORT = 'COM29'
BAUD_RATE = 115200

def send_command(ser, command):
    """Send JSON command and get response"""
    json_str = json.dumps(command)
    ser.write((json_str + '\n').encode())
    time.sleep(0.1)
    
    if ser.in_waiting:
        response = ser.readline().decode().strip()
        try:
            return json.loads(response)
        except:
            return {"raw": response}
    return None

def test_pwm_inversion():
    """Test that PWM inversion is working correctly"""
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        
        print("PWM Inversion Test")
        print("=" * 60)
        print("\nWith INVERT_WHITE_PWM enabled in platformio.ini:")
        print("- 0% command should produce 0% light (255 PWM internally)")
        print("- 100% command should produce 100% light (0 PWM internally)")
        print()
        
        # Test 1: Turn completely off
        print("1. Testing OFF (0% intensity)")
        print("-" * 60)
        cmd = {"cmd": "white", "warm": 0.0, "cool": 0.0}
        print(f"Command: {cmd}")
        response = send_command(ser, cmd)
        print(f"Response: {response}")
        print("Expected: White strips should be OFF (no light)")
        input("Verify lights are OFF, then press Enter...")
        
        # Test 2: Turn completely on
        print("\n2. Testing ON (100% intensity)")
        print("-" * 60)
        cmd = {"cmd": "white", "warm": 1.0, "cool": 1.0}
        print(f"Command: {cmd}")
        response = send_command(ser, cmd)
        print(f"Response: {response}")
        print("Expected: White strips should be at FULL brightness")
        input("Verify lights are at FULL brightness, then press Enter...")
        
        # Test 3: 50% intensity
        print("\n3. Testing 50% intensity")
        print("-" * 60)
        cmd = {"cmd": "white", "warm": 0.5, "cool": 0.5}
        print(f"Command: {cmd}")
        response = send_command(ser, cmd)
        print(f"Response: {response}")
        print("Expected: White strips should be at HALF brightness")
        input("Verify lights are at HALF brightness, then press Enter...")
        
        # Test 4: Ramp test
        print("\n4. Smooth ramp test (0% to 100%)")
        print("-" * 60)
        print("Ramping up from 0% to 100%...")
        for i in range(0, 101, 10):
            intensity = i / 100.0
            cmd = {"cmd": "white", "warm": intensity, "cool": intensity}
            send_command(ser, cmd)
            print(f"  {i}%", end="", flush=True)
            time.sleep(0.3)
        print("\nExpected: Smooth increase from dark to bright")
        
        time.sleep(1)
        
        print("\nRamping down from 100% to 0%...")
        for i in range(100, -1, -10):
            intensity = i / 100.0
            cmd = {"cmd": "white", "warm": intensity, "cool": intensity}
            send_command(ser, cmd)
            print(f"  {i}%", end="", flush=True)
            time.sleep(0.3)
        print("\nExpected: Smooth decrease from bright to dark")
        
        # Test 5: CCT command test
        print("\n5. Testing CCT command with inversion")
        print("-" * 60)
        
        test_temps = [
            ("Warm 2700K @ 100%", 2700, 1.0),
            ("Neutral 3500K @ 100%", 3500, 1.0),
            ("Cool 6000K @ 100%", 6000, 1.0),
            ("Neutral 3500K @ 50%", 3500, 0.5),
        ]
        
        for name, temp, intensity in test_temps:
            cmd = {"cmd": "cctWhite", "cct": temp, "intensity": intensity}
            print(f"\n{name}")
            print(f"Command: {cmd}")
            response = send_command(ser, cmd)
            print(f"Response: {response}")
            time.sleep(2)
        
        # Reset
        print("\n6. Turning off...")
        print("-" * 60)
        response = send_command(ser, {"cmd": "reset"})
        print(f"Reset: {response}")
        
        print("\n" + "=" * 60)
        print("PWM Inversion test complete!")
        print("\nIf all tests showed correct behavior:")
        print("✓ The PWM inversion is working properly")
        print("\nIf lights were still inverted (bright at 0%, dim at 100%):")
        print("✗ Comment out the INVERT_WHITE_PWM flag in platformio.ini")

if __name__ == "__main__":
    test_pwm_inversion()
