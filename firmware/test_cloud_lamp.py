#!/usr/bin/env python3
"""
Cloud Lamp ESP32-C3 Test Script

Tests all available serial commands for the cloud lamp firmware.
Connects via serial and sends JSON commands to test functionality.

Hardware: Seeed Studio XIAO ESP32-C3
Communication: 115200 baud, JSON over serial
"""

import serial
import json
import time
import sys

# Configuration
SERIAL_PORT = 'COM29'  # Change to match your COM port
BAUD_RATE = 115200
TIMEOUT = 2.0

class CloudLampTester:
    def __init__(self, port, baud_rate):
        """Initialize serial connection to cloud lamp."""
        print(f"Connecting to {port} at {baud_rate} baud...")
        try:
            self.serial = serial.Serial(port, baud_rate, timeout=TIMEOUT)
            time.sleep(2)  # Wait for ESP32 to reset after serial connection
            
            # Flush any startup messages
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore')
                print(f"  Startup: {line.strip()}")
            
            print("✓ Connected successfully\n")
        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            sys.exit(1)
    
    def send_command(self, command_dict):
        """Send a JSON command and wait for response."""
        command_json = json.dumps(command_dict)
        print(f"→ Sending: {command_json}")
        
        # Send command
        self.serial.write((command_json + '\n').encode('utf-8'))
        self.serial.flush()
        
        # Wait for response
        time.sleep(0.1)
        if self.serial.in_waiting:
            response = self.serial.readline().decode('utf-8', errors='ignore').strip()
            print(f"← Response: {response}")
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                print(f"  Warning: Could not parse response as JSON")
                return None
        else:
            print("← No response received")
            return None
    
    def test_ping(self):
        """Test ping command."""
        print("\n" + "="*60)
        print("TEST 1: Ping Command")
        print("="*60)
        print("Description: Simple connectivity test")
        response = self.send_command({"cmd": "ping"})
        if response and response.get("status") == "ok":
            print("✓ Ping successful\n")
            return True
        else:
            print("✗ Ping failed\n")
            return False
    
    def test_white_strips(self):
        """Test warm and cool white strip control."""
        print("\n" + "="*60)
        print("TEST 2: White Strip Control")
        print("="*60)
        print("Description: Control warm and cool white LED strips (PWM)")
        print("Parameters: warm (0.0-1.0), cool (0.0-1.0)\n")
        
        tests = [
            {"warm": 0.0, "cool": 0.0, "desc": "Both off"},
            {"warm": 0.25, "cool": 0.0, "desc": "Warm 25%"},
            {"warm": 0.5, "cool": 0.0, "desc": "Warm 50%"},
            {"warm": 1.0, "cool": 0.0, "desc": "Warm 100%"},
            {"warm": 0.0, "cool": 0.25, "desc": "Cool 25%"},
            {"warm": 0.0, "cool": 0.5, "desc": "Cool 50%"},
            {"warm": 0.0, "cool": 1.0, "desc": "Cool 100%"},
            {"warm": 0.5, "cool": 0.5, "desc": "Both 50%"},
            {"warm": 1.0, "cool": 1.0, "desc": "Both 100%"},
            {"warm": 0.0, "cool": 0.0, "desc": "Both off (final)"},
        ]
        
        all_passed = True
        for test in tests:
            print(f"  Testing: {test['desc']}")
            response = self.send_command({
                "cmd": "white",
                "warm": test["warm"],
                "cool": test["cool"]
            })
            
            if response and response.get("status") == "ok":
                print(f"  ✓ Success")
            else:
                print(f"  ✗ Failed")
                all_passed = False
            
            time.sleep(1.0)  # Visual delay between tests
            print()
        
        if all_passed:
            print("✓ All white strip tests passed\n")
        else:
            print("✗ Some white strip tests failed\n")
        
        return all_passed
    
    def test_reset(self):
        """Test reset command."""
        print("\n" + "="*60)
        print("TEST 3: Reset Command")
        print("="*60)
        print("Description: Turn off all LEDs and white strips")
        
        # First turn something on
        print("  Setting warm white to 100%...")
        self.send_command({"cmd": "white", "warm": 1.0, "cool": 0.0})
        time.sleep(1.0)
        
        # Now reset
        print("  Sending reset command...")
        response = self.send_command({"cmd": "reset"})
        
        if response and response.get("status") == "ok":
            print("✓ Reset successful\n")
            return True
        else:
            print("✗ Reset failed\n")
            return False
    
    def test_invalid_command(self):
        """Test error handling with invalid command."""
        print("\n" + "="*60)
        print("TEST 4: Invalid Command Handling")
        print("="*60)
        print("Description: Verify proper error responses")
        
        response = self.send_command({"cmd": "invalid_command"})
        
        if response and response.get("status") == "error":
            print("✓ Error handling works correctly\n")
            return True
        else:
            print("✗ Error handling failed\n")
            return False
    
    def test_missing_parameters(self):
        """Test error handling with missing parameters."""
        print("\n" + "="*60)
        print("TEST 5: Missing Command Field")
        print("="*60)
        print("Description: Send JSON without 'cmd' field")
        
        response = self.send_command({"other": "data"})
        
        if response and response.get("status") == "error":
            print("✓ Missing parameter detection works\n")
            return True
        else:
            print("✗ Missing parameter detection failed\n")
            return False
    
    def test_white_edge_cases(self):
        """Test white strips with edge case values."""
        print("\n" + "="*60)
        print("TEST 6: White Strip Edge Cases")
        print("="*60)
        print("Description: Test boundary values and clamping")
        
        tests = [
            {"warm": -0.5, "cool": 0.0, "desc": "Negative warm (should clamp to 0)"},
            {"warm": 1.5, "cool": 0.0, "desc": "Over 1.0 warm (should clamp to 1)"},
            {"warm": 0.0, "cool": -0.5, "desc": "Negative cool (should clamp to 0)"},
            {"warm": 0.0, "cool": 2.0, "desc": "Over 1.0 cool (should clamp to 1)"},
        ]
        
        all_passed = True
        for test in tests:
            print(f"  Testing: {test['desc']}")
            response = self.send_command({
                "cmd": "white",
                "warm": test["warm"],
                "cool": test["cool"]
            })
            
            if response and response.get("status") == "ok":
                print(f"  ✓ Command accepted (firmware will clamp values)")
            else:
                print(f"  ✗ Failed")
                all_passed = False
            
            time.sleep(0.5)
            print()
        
        # Clean up
        self.send_command({"cmd": "reset"})
        
        if all_passed:
            print("✓ Edge case tests passed\n")
        else:
            print("✗ Some edge case tests failed\n")
        
        return all_passed
    
    def test_lightning(self):
        """Test lightning animation."""
        print("\n" + "="*60)
        print("TEST 7: Lightning Animation")
        print("="*60)
        print("Description: Test configurable lightning flash on segments")
        print("Parameters: segment (0-3), attack, plateau, release (ms), r, g, b (0-255)\n")
        
        tests = [
            {
                "desc": "Default white lightning on segment 0",
                "params": {"cmd": "lightning", "segment": 0}
            },
            {
                "desc": "Blue lightning on segment 1 (fast)",
                "params": {"cmd": "lightning", "segment": 1, "r": 100, "g": 150, "b": 255, "attack": 30, "plateau": 50, "release": 100}
            },
            {
                "desc": "Slow orange lightning on segment 2",
                "params": {"cmd": "lightning", "segment": 2, "r": 255, "g": 150, "b": 0, "attack": 200, "plateau": 300, "release": 500}
            },
            {
                "desc": "Purple lightning on segment 3",
                "params": {"cmd": "lightning", "segment": 3, "r": 200, "g": 0, "b": 255, "attack": 50, "plateau": 100, "release": 200}
            },
        ]
        
        all_passed = True
        for test in tests:
            print(f"  Testing: {test['desc']}")
            response = self.send_command(test["params"])
            
            if response and response.get("status") == "ok":
                print(f"  ✓ Lightning triggered")
            else:
                print(f"  ✗ Failed")
                all_passed = False
            
            # Wait for animation to complete
            time.sleep(1.5)
            print()
        
        # Clean up
        self.send_command({"cmd": "reset"})
        
        if all_passed:
            print("✓ All lightning tests passed\n")
        else:
            print("✗ Some lightning tests failed\n")
        
        return all_passed
    
    def run_all_tests(self):
        """Run all test suites."""
        print("\n" + "="*70)
        print(" CLOUD LAMP ESP32-C3 SERIAL COMMAND TEST SUITE")
        print("="*70)
        print(f"\nPort: {SERIAL_PORT}")
        print(f"Baud: {BAUD_RATE}")
        print(f"Device: Seeed Studio XIAO ESP32-C3")
        
        results = {
            "Ping": self.test_ping(),
            "White Strips": self.test_white_strips(),
            "Reset": self.test_reset(),
            "Invalid Command": self.test_invalid_command(),
            "Missing Parameters": self.test_missing_parameters(),
            "Edge Cases": self.test_white_edge_cases(),
            "Lightning": self.test_lightning(),
        }
        
        # Summary
        print("\n" + "="*70)
        print(" TEST SUMMARY")
        print("="*70)
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{test_name:.<40} {status}")
        
        total = len(results)
        passed = sum(results.values())
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
        
        print("="*70 + "\n")
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Serial connection closed.")


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print(" Cloud Lamp Serial Test Script")
    print(" ESP32-C3 Firmware Command Testing")
    print("="*70 + "\n")
    
    # Check if port is specified in command line
    port = SERIAL_PORT
    if len(sys.argv) > 1:
        port = sys.argv[1]
        print(f"Using port from command line: {port}\n")
    
    # Run tests
    tester = None
    try:
        tester = CloudLampTester(port, BAUD_RATE)
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester:
            tester.close()


if __name__ == "__main__":
    main()
