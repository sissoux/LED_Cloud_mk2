"""
Test script for CCT White command
Demonstrates color temperature control from warm (2700K) to cool (6000K)
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

def test_cct_sweep():
    """Sweep through color temperatures from warm to cool"""
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        
        print("CCT White Command Test")
        print("=" * 60)
        
        # Test 1: Sweep from warm to cool at 100% intensity
        print("\n1. Temperature sweep (2700K to 6000K) at 100% intensity")
        print("-" * 60)
        temperatures = [2700, 3000, 3500, 4000, 4500, 5000, 5500, 6000]
        
        for temp in temperatures:
            cmd = {"cmd": "cctWhite", "cct": temp, "intensity": 1.0}
            print(f"Setting {temp}K... ", end="")
            response = send_command(ser, cmd)
            print(f"Response: {response}")
            time.sleep(1.5)
        
        # Test 2: Fixed temperature with varying intensity
        print("\n2. Daylight (5000K) with intensity sweep")
        print("-" * 60)
        intensities = [0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4, 0.2]
        
        for intensity in intensities:
            cmd = {"cmd": "cctWhite", "cct": 5000, "intensity": intensity}
            print(f"Setting intensity {intensity:.1f}... ", end="")
            response = send_command(ser, cmd)
            print(f"Response: {response}")
            time.sleep(0.8)
        
        # Test 3: Common lighting scenarios
        print("\n3. Common lighting scenarios")
        print("-" * 60)
        scenarios = [
            ("Warm Evening", 2700, 0.7),
            ("Cozy Reading", 3000, 0.8),
            ("Neutral Day", 4000, 1.0),
            ("Bright Office", 5000, 1.0),
            ("Cool Focus", 6000, 0.9),
        ]
        
        for name, temp, intensity in scenarios:
            cmd = {"cmd": "cctWhite", "cct": temp, "intensity": intensity}
            print(f"{name:15} ({temp}K @ {intensity:.0%})... ", end="")
            response = send_command(ser, cmd)
            print(f"Response: {response}")
            time.sleep(2.0)
        
        # Test 4: Edge cases
        print("\n4. Edge cases (auto-clamping test)")
        print("-" * 60)
        edge_cases = [
            ("Below minimum", 2000, 0.5),  # Should clamp to 2700K
            ("Above maximum", 7000, 0.5),  # Should clamp to 6000K
            ("Over intensity", 4000, 1.5),  # Should clamp to 1.0
            ("Negative intensity", 4000, -0.2),  # Should clamp to 0.0
        ]
        
        for name, temp, intensity in edge_cases:
            cmd = {"cmd": "cctWhite", "cct": temp, "intensity": intensity}
            print(f"{name:20} (CCT={temp}, I={intensity})... ", end="")
            response = send_command(ser, cmd)
            print(f"Response: {response}")
            time.sleep(1.5)
        
        # Reset
        print("\n5. Turning off...")
        print("-" * 60)
        response = send_command(ser, {"cmd": "reset"})
        print(f"Reset: {response}")
        
        print("\n" + "=" * 60)
        print("CCT White test complete!")

def test_cct_vs_manual():
    """Compare CCT command with manual warm/cool mix"""
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        
        print("\nCCT vs Manual Mix Comparison")
        print("=" * 60)
        
        # Test 3500K (middle temperature)
        # Expected: 50% warm (2700K) + 50% cool (6000K)
        print("\nTarget: 3500K @ 100% intensity")
        print("-" * 60)
        
        print("Using cctWhite command:")
        cmd = {"cmd": "cctWhite", "cct": 3500, "intensity": 1.0}
        response = send_command(ser, cmd)
        print(f"  Command: {cmd}")
        print(f"  Response: {response}")
        time.sleep(3)
        
        print("\nUsing manual white command (should be equivalent):")
        # At 3500K: cool_ratio = (3500-2700)/(6000-2700) = 800/3300 = 0.242
        #           warm_ratio = (6000-3500)/(6000-2700) = 2500/3300 = 0.758
        cmd = {"cmd": "white", "warm": 0.758, "cool": 0.242}
        response = send_command(ser, cmd)
        print(f"  Command: {cmd}")
        print(f"  Response: {response}")
        time.sleep(3)
        
        # Reset
        send_command(ser, {"cmd": "reset"})

if __name__ == "__main__":
    print("Select test:")
    print("1. Full CCT sweep and scenarios")
    print("2. CCT vs Manual comparison")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        test_cct_sweep()
    elif choice == "2":
        test_cct_vs_manual()
    elif choice == "3":
        test_cct_sweep()
        print("\n" + "=" * 60)
        test_cct_vs_manual()
    else:
        print("Invalid choice")
