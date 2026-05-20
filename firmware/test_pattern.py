#!/usr/bin/env python3
"""
Pattern Command Test Script for Cloud Lamp ESP32-C3

Tests the pattern command that sends multiple lightning events
in a single JSON frame for efficient animation sequences.
"""

import serial
import json
import time

SERIAL_PORT = "COM29"
BAUD_RATE = 115200


def send_command(ser, cmd_dict):
    """Send JSON command and wait for response."""
    cmd_str = json.dumps(cmd_dict) + "\n"
    ser.write(cmd_str.encode())
    ser.flush()
    
    time.sleep(0.05)
    if ser.in_waiting > 0:
        response = ser.readline().decode().strip()
        print(f"Response: {response}")
    else:
        print("No response")


def test_simple_storm(ser):
    """Test a simple storm pattern across segments."""
    print("\n" + "="*70)
    print("TEST 1: Simple Storm Pattern")
    print("="*70)
    print("Description: 4 flashes across segments with delays")
    
    pattern = {
        "cmd": "pattern",
        "events": [
            {"time_ms": 0, "segment": 0, "r": 255, "g": 255, "b": 255, "attack": 50, "plateau": 100, "release": 200, "intensity": 1.0},
            {"time_ms": 500, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 40, "plateau": 80, "release": 180, "intensity": 0.9},
            {"time_ms": 900, "segment": 2, "r": 255, "g": 255, "b": 255, "attack": 30, "plateau": 60, "release": 150, "intensity": 0.7},
            {"time_ms": 1200, "segment": 3, "r": 255, "g": 255, "b": 255, "attack": 60, "plateau": 120, "release": 250, "intensity": 1.0}
        ]
    }
    
    send_command(ser, pattern)
    print("Pattern sent. Wait for completion...")
    time.sleep(3)


def test_rapid_flicker(ser):
    """Test rapid flickering effect."""
    print("\n" + "="*70)
    print("TEST 2: Rapid Flicker Pattern")
    print("="*70)
    print("Description: Quick successive flashes on segment 1")
    
    pattern = {
        "cmd": "pattern",
        "events": [
            {"time_ms": 0, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 20, "plateau": 30, "release": 50, "intensity": 1.0},
            {"time_ms": 150, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 15, "plateau": 20, "release": 40, "intensity": 0.6},
            {"time_ms": 250, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 25, "plateau": 40, "release": 60, "intensity": 0.8},
            {"time_ms": 400, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 30, "plateau": 50, "release": 100, "intensity": 1.0}
        ]
    }
    
    send_command(ser, pattern)
    print("Pattern sent. Wait for completion...")
    time.sleep(2)


def test_multi_color_sequence(ser):
    """Test pattern with different colors."""
    print("\n" + "="*70)
    print("TEST 3: Multi-Color Sequence")
    print("="*70)
    print("Description: Different colored flashes on each segment")
    
    pattern = {
        "cmd": "pattern",
        "events": [
            {"time_ms": 0, "segment": 0, "r": 255, "g": 0, "b": 0, "attack": 50, "plateau": 100, "release": 150, "intensity": 1.0},
            {"time_ms": 400, "segment": 1, "r": 0, "g": 255, "b": 0, "attack": 50, "plateau": 100, "release": 150, "intensity": 1.0},
            {"time_ms": 800, "segment": 2, "r": 0, "g": 0, "b": 255, "attack": 50, "plateau": 100, "release": 150, "intensity": 1.0},
            {"time_ms": 1200, "segment": 3, "r": 255, "g": 255, "b": 0, "attack": 50, "plateau": 100, "release": 150, "intensity": 1.0}
        ]
    }
    
    send_command(ser, pattern)
    print("Pattern sent. Wait for completion...")
    time.sleep(2.5)


def test_white_strips_pattern(ser):
    """Test pattern on white PWM strips."""
    print("\n" + "="*70)
    print("TEST 4: White Strips Pattern")
    print("="*70)
    print("Description: Alternating flashes on cool and warm white strips")
    
    pattern = {
        "cmd": "pattern",
        "events": [
            {"time_ms": 0, "segment": 4, "r": 0, "g": 0, "b": 0, "attack": 50, "plateau": 100, "release": 200, "intensity": 1.0},
            {"time_ms": 500, "segment": 5, "r": 0, "g": 0, "b": 0, "attack": 50, "plateau": 100, "release": 200, "intensity": 1.0},
            {"time_ms": 1000, "segment": 4, "r": 0, "g": 0, "b": 0, "attack": 50, "plateau": 100, "release": 200, "intensity": 0.7},
            {"time_ms": 1400, "segment": 5, "r": 0, "g": 0, "b": 0, "attack": 50, "plateau": 100, "release": 200, "intensity": 0.7}
        ]
    }
    
    send_command(ser, pattern)
    print("Pattern sent. Wait for completion...")
    time.sleep(2.5)


def test_complex_storm(ser):
    """Test complex realistic storm pattern."""
    print("\n" + "="*70)
    print("TEST 5: Complex Realistic Storm")
    print("="*70)
    print("Description: Multi-segment storm with varying intensities")
    
    pattern = {
        "cmd": "pattern",
        "events": [
            # Initial flash
            {"time_ms": 0, "segment": 2, "r": 255, "g": 255, "b": 255, "attack": 30, "plateau": 50, "release": 100, "intensity": 1.0},
            # Chain reaction
            {"time_ms": 200, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 20, "plateau": 40, "release": 80, "intensity": 0.7},
            {"time_ms": 300, "segment": 3, "r": 255, "g": 255, "b": 255, "attack": 25, "plateau": 50, "release": 90, "intensity": 0.8},
            # Brief pause
            # Second wave
            {"time_ms": 800, "segment": 0, "r": 255, "g": 255, "b": 255, "attack": 40, "plateau": 80, "release": 150, "intensity": 0.9},
            {"time_ms": 1000, "segment": 2, "r": 255, "g": 255, "b": 255, "attack": 35, "plateau": 70, "release": 130, "intensity": 1.0},
            # Final big flash
            {"time_ms": 1600, "segment": 1, "r": 255, "g": 255, "b": 255, "attack": 50, "plateau": 150, "release": 300, "intensity": 1.0},
            {"time_ms": 1650, "segment": 2, "r": 255, "g": 255, "b": 255, "attack": 50, "plateau": 150, "release": 300, "intensity": 1.0}
        ]
    }
    
    send_command(ser, pattern)
    print("Pattern sent. Wait for completion...")
    time.sleep(3.5)


def reset(ser):
    """Reset all LEDs."""
    send_command(ser, {"cmd": "reset"})
    time.sleep(0.5)


def main():
    print("\n" + "="*70)
    print(" PATTERN COMMAND TEST SUITE")
    print(" ESP32-C3 Cloud Lamp - Pattern Animation Testing")
    print("="*70)
    print(f"\nPort: {SERIAL_PORT}")
    print(f"Baud: {BAUD_RATE}")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for ESP32 to initialize
        print("Connected to ESP32-C3\n")
        
        # Reset before tests
        print("Resetting device...")
        reset(ser)
        
        # Run tests
        test_simple_storm(ser)
        reset(ser)
        
        test_rapid_flicker(ser)
        reset(ser)
        
        test_multi_color_sequence(ser)
        reset(ser)
        
        test_white_strips_pattern(ser)
        reset(ser)
        
        test_complex_storm(ser)
        reset(ser)
        
        print("\n" + "="*70)
        print("All pattern tests completed!")
        print("="*70 + "\n")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {SERIAL_PORT}")
        print(f"Details: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        if ser.is_open:
            reset(ser)
            ser.close()
        return 0
    
    return 0


if __name__ == "__main__":
    exit(main())
