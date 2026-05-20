#!/usr/bin/env python3
"""
Random Flash Test Script for Cloud Lamp ESP32-C3

Tests the two random flash commands:
- randomSegFlash: Random segment with intensity-based timing
- randomFlash: Random adjacent LEDs with intensity-based count and timing
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
        print(f"  → {response}")
        return response
    return None


def test_random_seg_flash_intensity_range(ser):
    """Test randomSegFlash with different intensity levels."""
    print("\n" + "="*70)
    print("TEST 1: Random Segment Flash - Intensity Range (1-10)")
    print("="*70)
    print("Testing different intensity levels on random segments\n")
    
    for intensity in [1, 3, 5, 7, 10]:
        print(f"Intensity {intensity}/10:")
        send_command(ser, {"cmd": "randomSegFlash", "intensity": intensity})
        time.sleep(1.5)


def test_random_seg_flash_colors(ser):
    """Test randomSegFlash with different colors."""
    print("\n" + "="*70)
    print("TEST 2: Random Segment Flash - Different Colors")
    print("="*70)
    print("Testing colored flashes with high intensity\n")
    
    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("Yellow", 255, 255, 0),
        ("Cyan", 0, 255, 255),
        ("Magenta", 255, 0, 255)
    ]
    
    for name, r, g, b in colors:
        print(f"{name} flash:")
        send_command(ser, {"cmd": "randomSegFlash", "intensity": 8, "r": r, "g": g, "b": b})
        time.sleep(1.2)


def test_random_flash_intensity_range(ser):
    """Test randomFlash with different intensity levels."""
    print("\n" + "="*70)
    print("TEST 3: Random LEDs Flash - Intensity Range (1-10)")
    print("="*70)
    print("Testing different LED counts based on intensity\n")
    
    for intensity in [1, 2, 4, 6, 8, 10]:
        print(f"Intensity {intensity}/10 (LED count scales with intensity):")
        send_command(ser, {"cmd": "randomFlash", "intensity": intensity})
        time.sleep(1.5)


def test_random_flash_rapid_sequence(ser):
    """Test rapid sequence of random flashes."""
    print("\n" + "="*70)
    print("TEST 4: Rapid Random Flash Sequence")
    print("="*70)
    print("Simulating storm with random flashes\n")
    
    import random
    
    for i in range(10):
        intensity = random.randint(3, 9)
        print(f"Flash {i+1}/10 (intensity {intensity}):")
        send_command(ser, {"cmd": "randomFlash", "intensity": intensity})
        time.sleep(random.uniform(0.3, 0.8))


def test_mixed_random_flashes(ser):
    """Test mixing segment and LED-based random flashes."""
    print("\n" + "="*70)
    print("TEST 5: Mixed Random Flashes")
    print("="*70)
    print("Alternating between segment and LED-based flashes\n")
    
    import random
    
    for i in range(8):
        intensity = random.randint(4, 10)
        
        if i % 2 == 0:
            print(f"Random segment flash (intensity {intensity}):")
            send_command(ser, {"cmd": "randomSegFlash", "intensity": intensity})
        else:
            print(f"Random LEDs flash (intensity {intensity}):")
            send_command(ser, {"cmd": "randomFlash", "intensity": intensity})
        
        time.sleep(random.uniform(0.5, 1.0))


def test_low_vs_high_intensity(ser):
    """Compare low and high intensity flashes side by side."""
    print("\n" + "="*70)
    print("TEST 6: Low vs High Intensity Comparison")
    print("="*70)
    print("Direct comparison of intensity effects\n")
    
    print("Low intensity (1) - segment flash:")
    send_command(ser, {"cmd": "randomSegFlash", "intensity": 1})
    time.sleep(1.5)
    
    print("High intensity (10) - segment flash:")
    send_command(ser, {"cmd": "randomSegFlash", "intensity": 10})
    time.sleep(2.0)
    
    print("\nLow intensity (1) - LED flash:")
    send_command(ser, {"cmd": "randomFlash", "intensity": 1})
    time.sleep(1.5)
    
    print("High intensity (10) - LED flash:")
    send_command(ser, {"cmd": "randomFlash", "intensity": 10})
    time.sleep(2.0)


def reset(ser):
    """Reset all LEDs."""
    send_command(ser, {"cmd": "reset"})
    time.sleep(0.5)


def main():
    print("\n" + "="*70)
    print(" RANDOM FLASH TEST SUITE")
    print(" ESP32-C3 Cloud Lamp - Random Lightning Effects")
    print("="*70)
    print(f"\nPort: {SERIAL_PORT}")
    print(f"Baud: {BAUD_RATE}")
    print("\nIntensity Scale (1-10):")
    print("  - Attack:  1-5ms (low) → 50-100ms (high)")
    print("  - Plateau: 5-20ms (low) → 50-150ms (high)")
    print("  - Release: 50-150ms (low) → 150-300ms (high)")
    print("  - LED count (randomFlash): 1-2 LEDs (low) → 15-25 LEDs (high)")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for ESP32 to initialize
        print("\n✓ Connected to ESP32-C3\n")
        
        # Reset before tests
        print("Resetting device...")
        reset(ser)
        
        # Run tests
        test_random_seg_flash_intensity_range(ser)
        reset(ser)
        
        test_random_seg_flash_colors(ser)
        reset(ser)
        
        test_random_flash_intensity_range(ser)
        reset(ser)
        
        test_random_flash_rapid_sequence(ser)
        reset(ser)
        
        test_mixed_random_flashes(ser)
        reset(ser)
        
        test_low_vs_high_intensity(ser)
        reset(ser)
        
        print("\n" + "="*70)
        print("✓ All random flash tests completed!")
        print("="*70 + "\n")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"✗ Error: Could not open serial port {SERIAL_PORT}")
        print(f"  Details: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        if 'ser' in locals() and ser.is_open:
            reset(ser)
            ser.close()
        return 0
    
    return 0


if __name__ == "__main__":
    exit(main())
