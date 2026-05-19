#!/usr/bin/env python3
"""
Cloud Lamp Lightning Animation Tester

Dedicated testing script for lightning flash animations.
Tests various timing configurations, colors, and sequences.

Hardware: Seeed Studio XIAO ESP32-C3
Communication: 115200 baud, JSON over serial
"""

import serial
import json
import time
import sys
import random

# Configuration
SERIAL_PORT = 'COM29'  # Change to match your COM port
BAUD_RATE = 115200
TIMEOUT = 2.0

class LightningTester:
    def __init__(self, port, baud_rate):
        """Initialize serial connection to cloud lamp."""
        print(f"Connecting to {port} at {baud_rate} baud...")
        try:
            self.serial = serial.Serial(port, baud_rate, timeout=TIMEOUT)
            time.sleep(2)  # Wait for ESP32 to reset
            
            # Flush any startup messages
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore')
                print(f"  {line.strip()}")
            
            print("✓ Connected successfully\n")
        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            sys.exit(1)
    
    def send_command(self, command_dict):
        """Send a JSON command and wait for response."""
        command_json = json.dumps(command_dict)
        
        # Send command
        self.serial.write((command_json + '\n').encode('utf-8'))
        self.serial.flush()
        
        # Wait for response
        time.sleep(0.05)
        if self.serial.in_waiting:
            response = self.serial.readline().decode('utf-8', errors='ignore').strip()
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return None
        return None
    
    def lightning(self, segment=0, r=255, g=255, b=255, attack=50, plateau=100, release=200, intensity=1.0):
        """Trigger a lightning flash with specified parameters."""
        cmd = {
            "cmd": "lightning",
            "segment": segment,
            "r": r,
            "g": g,
            "b": b,
            "attack": attack,
            "plateau": plateau,
            "release": release,
            "intensity": intensity
        }
        return self.send_command(cmd)
    
    def reset(self):
        """Reset all LEDs and animations."""
        return self.send_command({"cmd": "reset"})
    
    def wait_animation(self, attack, plateau, release):
        """Wait for animation to complete."""
        total_ms = attack + plateau + release
        time.sleep(total_ms / 1000.0 + 0.1)  # Add 100ms buffer
    
    def test_basic_flashes(self):
        """Test basic lightning flashes on each segment."""
        print("\n" + "="*70)
        print(" TEST 1: Basic Lightning Flash - White on Each RGB Segment")
        print("="*70)
        print("Testing default white lightning on all 4 RGB segments\n")
        
        for segment in range(4):
            print(f"  RGB Segment {segment}... ", end='', flush=True)
            response = self.lightning(segment=segment)
            if response and response.get("status") == "ok":
                print("✓ Triggered")
            else:
                print("✗ Failed")
            self.wait_animation(50, 100, 200)
        
        print("\n✓ Basic flash test complete\n")
    
    def test_white_strip_flashes(self):
        """Test lightning flashes on white PWM strips."""
        print("\n" + "="*70)
        print(" TEST 2: White Strip Lightning")
        print("="*70)
        print("Testing lightning on PWM white strips (segments 4 & 5)")
        print("Note: RGB color values are ignored for white strips\n")
        
        tests = [
            {"segment": 4, "name": "Cool White Strip (Seg 4)", "attack": 50, "plateau": 100, "release": 200},
            {"segment": 5, "name": "Warm White Strip (Seg 5)", "attack": 50, "plateau": 100, "release": 200},
            {"segment": 4, "name": "Cool White (Fast)", "attack": 30, "plateau": 50, "release": 100},
            {"segment": 5, "name": "Warm White (Slow)", "attack": 150, "plateau": 300, "release": 400},
            {"segment": 4, "name": "Cool White (Sharp)", "attack": 10, "plateau": 30, "release": 80},
            {"segment": 5, "name": "Warm White (Long)", "attack": 100, "plateau": 500, "release": 600},
        ]
        
        for test in tests:
            print(f"  {test['name']:.<35} ", end='', flush=True)
            response = self.lightning(
                segment=test['segment'],
                attack=test['attack'],
                plateau=test['plateau'],
                release=test['release']
            )
            if response and response.get("status") == "ok":
                print("✓ Triggered")
            else:
                print("✗ Failed")
            self.wait_animation(test['attack'], test['plateau'], test['release'])
        
        print("\n✓ White strip flash test complete\n")
    
    def test_timing_variations(self):
        """Test different attack/plateau/release timings."""
        print("\n" + "="*70)
        print(" TEST 3: Timing Variations")
        print("="*70)
        print("Testing different attack, plateau, and release timings\n")
        
        tests = [
            {"name": "Quick flash", "attack": 30, "plateau": 50, "release": 80},
            {"name": "Default flash", "attack": 50, "plateau": 100, "release": 200},
            {"name": "Slow flash", "attack": 150, "plateau": 300, "release": 400},
            {"name": "Very slow flash", "attack": 300, "plateau": 500, "release": 700},
            {"name": "Sharp strike", "attack": 10, "plateau": 30, "release": 100},
            {"name": "Long glow", "attack": 100, "plateau": 500, "release": 600},
        ]
        
        for i, test in enumerate(tests):
            segment = i % 4  # Cycle through segments
            print(f"  {test['name']:.<30} ", end='', flush=True)
            print(f"({test['attack']}ms/{test['plateau']}ms/{test['release']}ms) on seg {segment}... ", end='', flush=True)
            
            self.lightning(
                segment=segment,
                attack=test['attack'],
                plateau=test['plateau'],
                release=test['release']
            )
            print("✓")
            self.wait_animation(test['attack'], test['plateau'], test['release'])
        
        print("\n✓ Timing variation test complete\n")
    
    def test_color_variations(self):
        """Test lightning with different colors."""
        print("\n" + "="*70)
        print(" TEST 4: Color Variations")
        print("="*70)
        print("Testing lightning with different colors\n")
        
        colors = [
            {"name": "Pure White", "r": 255, "g": 255, "b": 255},
            {"name": "Cool Blue", "r": 100, "g": 150, "b": 255},
            {"name": "Electric Purple", "r": 200, "g": 50, "b": 255},
            {"name": "Warm Orange", "r": 255, "g": 120, "b": 0},
            {"name": "Bright Yellow", "r": 255, "g": 255, "b": 0},
            {"name": "Cyan Flash", "r": 0, "g": 255, "b": 255},
            {"name": "Magenta Bolt", "r": 255, "g": 0, "b": 255},
            {"name": "Green Strike", "r": 0, "g": 255, "b": 50},
        ]
        
        for i, color in enumerate(colors):
            segment = i % 4
            print(f"  {color['name']:.<25} ", end='', flush=True)
            print(f"RGB({color['r']:3d},{color['g']:3d},{color['b']:3d}) on seg {segment}... ", end='', flush=True)
            
            self.lightning(
                segment=segment,
                r=color['r'],
                g=color['g'],
                b=color['b'],
                attack=40,
                plateau=80,
                release=150
            )
            print("✓")
            self.wait_animation(40, 80, 150)
        
        print("\n✓ Color variation test complete\n")
    
    def test_sequential_storm(self):
        """Test sequential lightning across segments (storm effect)."""
        print("\n" + "="*70)
        print(" TEST 5: Sequential Storm Pattern")
        print("="*70)
        print("Simulating a thunderstorm with sequential strikes\n")
        
        print("  Starting storm sequence...")
        
        # Storm sequence: random segments with varying delays
        strikes = [
            {"segment": 2, "delay": 0.0, "attack": 30, "plateau": 50, "release": 120},
            {"segment": 0, "delay": 0.4, "attack": 20, "plateau": 40, "release": 100},
            {"segment": 3, "delay": 0.8, "attack": 40, "plateau": 60, "release": 150},
            {"segment": 1, "delay": 1.5, "attack": 25, "plateau": 50, "release": 110},
            {"segment": 2, "delay": 0.3, "attack": 35, "plateau": 70, "release": 140},
            {"segment": 0, "delay": 0.2, "attack": 15, "plateau": 30, "release": 80},
            {"segment": 3, "delay": 1.2, "attack": 50, "plateau": 100, "release": 200},
            {"segment": 1, "delay": 0.5, "attack": 30, "plateau": 50, "release": 100},
        ]
        
        for i, strike in enumerate(strikes):
            time.sleep(strike['delay'])
            print(f"    Strike {i+1}: Segment {strike['segment']} ", end='', flush=True)
            
            self.lightning(
                segment=strike['segment'],
                r=200, g=220, b=255,  # Slight blue tint
                attack=strike['attack'],
                plateau=strike['plateau'],
                release=strike['release']
            )
            print("⚡")
        
        time.sleep(1.0)
        print("\n✓ Storm sequence complete\n")
    
    def test_all_segments_simultaneous(self):
        """Test triggering multiple segments in rapid succession."""
        print("\n" + "="*70)
        print(" TEST 6: Rapid Multi-Segment Strikes")
        print("="*70)
        print("Note: Only one animation active at a time, but can trigger rapidly\n")
        
        print("  Triggering all segments in rapid succession...")
        for segment in range(4):
            self.lightning(segment=segment, attack=40, plateau=80, release=150)
            time.sleep(0.05)  # Very short delay between triggers
            print(f"    Segment {segment} triggered")
        
        time.sleep(0.5)
        print("\n✓ Rapid multi-segment test complete\n")
    
    def test_realistic_lightning(self):
        """Test realistic lightning patterns with multiple quick flashes."""
        print("\n" + "="*70)
        print(" TEST 7: Realistic Lightning Pattern")
        print("="*70)
        print("Simulating realistic multi-flash lightning strikes\n")
        
        patterns = [
            {
                "name": "Double flash",
                "flashes": [
                    {"segment": 1, "attack": 20, "plateau": 40, "release": 100, "delay": 0.0},
                    {"segment": 1, "attack": 15, "plateau": 30, "release": 80, "delay": 0.15},
                ]
            },
            {
                "name": "Triple flash",
                "flashes": [
                    {"segment": 3, "attack": 25, "plateau": 50, "release": 120, "delay": 0.0},
                    {"segment": 3, "attack": 20, "plateau": 40, "release": 90, "delay": 0.18},
                    {"segment": 3, "attack": 30, "plateau": 60, "release": 150, "delay": 0.15},
                ]
            },
            {
                "name": "Flickering strike",
                "flashes": [
                    {"segment": 0, "attack": 10, "plateau": 20, "release": 50, "delay": 0.0},
                    {"segment": 0, "attack": 15, "plateau": 30, "release": 70, "delay": 0.08},
                    {"segment": 0, "attack": 8, "plateau": 15, "release": 40, "delay": 0.08},
                    {"segment": 0, "attack": 40, "plateau": 80, "release": 200, "delay": 0.12},
                ]
            },
        ]
        
        for pattern in patterns:
            print(f"  {pattern['name']}:")
            for i, flash in enumerate(pattern['flashes']):
                time.sleep(flash['delay'])
                self.lightning(
                    segment=flash['segment'],
                    r=220, g=230, b=255,
                    attack=flash['attack'],
                    plateau=flash['plateau'],
                    release=flash['release']
                )
                print(f"    Flash {i+1} ⚡")
            
            time.sleep(0.5)
            print()
        
        print("✓ Realistic lightning patterns complete\n")
    def test_intensity_variations(self):
        """Test lightning with different intensity levels."""
        print("\n" + "="*70)
        print(" TEST 8: Intensity Variations")
        print("="*70)
        print("Testing lightning with different intensity levels (0.0-1.0)\n")
        
        tests = [
            {"segment": 0, "intensity": 1.0, "name": "100% intensity (default)"},
            {"segment": 1, "intensity": 0.75, "name": "75% intensity"},
            {"segment": 2, "intensity": 0.5, "name": "50% intensity"},
            {"segment": 3, "intensity": 0.25, "name": "25% intensity"},
            {"segment": 0, "intensity": 0.1, "name": "10% intensity (very dim)"},
            {"segment": 4, "intensity": 0.5, "name": "Cool white 50% intensity"},
            {"segment": 5, "intensity": 0.5, "name": "Warm white 50% intensity"},
        ]
        
        for test in tests:
            print(f"  {test['name']:.<40} ", end='', flush=True)
            self.lightning(
                segment=test['segment'],
                intensity=test['intensity'],
                attack=40,
                plateau=80,
                release=150
            )
            print("✓")
            self.wait_animation(40, 80, 150)
        
        print("\n✓ Intensity variation test complete\n")
    
    def run_interactive_mode(self):
        """Interactive mode for manual testing."""
        print("\n" + "="*70)
        print(" INTERACTIVE LIGHTNING MODE")
        print("="*70)
        print("Segments:")
        print("  0-3: RGB LED segments")
        print("  4:   Cool white strip (PWM)")
        print("  5:   Warm white strip (PWM)")
        print("\nCommands:")
        print("  s<N>      - Strike segment N (0-5) with current settings")
        print("  c<R,G,B>  - Set color for RGB segments (e.g., c255,200,100)")
        print("  t<A,P,R>  - Set timing (attack,plateau,release in ms, e.g., t50,100,200)")
        print("  i<0.0-1.0> - Set intensity (e.g., i0.5 for 50%)")
        print("  storm     - Run a random storm sequence")
        print("  reset     - Reset all LEDs")
        print("  quit      - Exit interactive mode")
        print("="*70 + "\n")
        
        current_r, current_g, current_b = 255, 255, 255
        current_attack, current_plateau, current_release = 50, 100, 200
        current_intensity = 1.0
        
        while True:
            try:
                cmd = input("lightning> ").strip().lower()
                
                if cmd == "quit" or cmd == "exit" or cmd == "q":
                    break
                
                elif cmd.startswith("s"):
                    try:
                        segment = int(cmd[1:])
                        if 0 <= segment <= 5:
                            self.lightning(
                                segment=segment,
                                r=current_r, g=current_g, b=current_b,
                                attack=current_attack,
                                plateau=current_plateau,
                                release=current_release,
                                intensity=current_intensity
                            )
                            if segment <= 3:
                                print(f"⚡ RGB Segment {segment} - RGB({current_r},{current_g},{current_b}) - {current_attack}/{current_plateau}/{current_release}ms @ {int(current_intensity*100)}%")
                            elif segment == 4:
                                print(f"⚡ Cool White Strip - {current_attack}/{current_plateau}/{current_release}ms @ {int(current_intensity*100)}%")
                            else:  # segment == 5
                                print(f"⚡ Warm White Strip - {current_attack}/{current_plateau}/{current_release}ms @ {int(current_intensity*100)}%")
                        else:
                            print("Error: Segment must be 0-5 (0-3: RGB, 4: Cool White, 5: Warm White)")
                    except ValueError:
                        print("Error: Invalid segment number")
                
                elif cmd.startswith("c"):
                    try:
                        rgb = cmd[1:].split(',')
                        current_r = int(rgb[0])
                        current_g = int(rgb[1])
                        current_b = int(rgb[2])
                        print(f"Color set to RGB({current_r},{current_g},{current_b})")
                    except (ValueError, IndexError):
                        print("Error: Use format c<R,G,B> (e.g., c255,200,100)")
                
                elif cmd.startswith("t"):
                    try:
                        timing = cmd[1:].split(',')
                        current_attack = int(timing[0])
                        current_plateau = int(timing[1])
                        current_release = int(timing[2])
                        print(f"Timing set to {current_attack}/{current_plateau}/{current_release}ms")
                    except (ValueError, IndexError):
                        print("Error: Use format t<A,P,R> (e.g., t50,100,200)")
                
                elif cmd.startswith("i"):
                    try:
                        current_intensity = float(cmd[1:])
                        current_intensity = max(0.0, min(1.0, current_intensity))  # Clamp to 0.0-1.0
                        print(f"Intensity set to {current_intensity:.2f} ({int(current_intensity*100)}%)")
                    except ValueError:
                        print("Error: Use format i<0.0-1.0> (e.g., i0.5 for 50%)")
                
                elif cmd == "storm":
                    print("Starting random storm...")
                    for _ in range(random.randint(5, 10)):
                        # Mix RGB segments and white strips (weighted toward RGB)
                        segment = random.choices([0, 1, 2, 3, 4, 5], weights=[3, 3, 3, 3, 1, 1])[0]
                        attack = random.randint(20, 60)
                        plateau = random.randint(40, 120)
                        release = random.randint(80, 250)
                        self.lightning(segment=segment, r=200, g=220, b=255, 
                                     attack=attack, plateau=plateau, release=release)
                        if segment <= 3:
                            print(f"  ⚡ RGB Segment {segment}")
                        elif segment == 4:
                            print(f"  ⚡ Cool White Strip")
                        else:
                            print(f"  ⚡ Warm White Strip")
                        time.sleep(random.uniform(0.1, 1.5))
                    print("Storm complete")
                
                elif cmd == "reset":
                    self.reset()
                    print("Reset complete")
                
                elif cmd == "":
                    continue
                
                else:
                    print(f"Unknown command: {cmd}")
            
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
            except EOFError:
                break
    
    def run_all_tests(self):
        """Run all automated tests."""
        print("\n" + "="*70)
        print(" LIGHTNING ANIMATION TEST SUITE")
        print(" ESP32-C3 Cloud Lamp - Comprehensive Lightning Testing")
        print("="*70)
        print(f"\nPort: {SERIAL_PORT}")
        print(f"Baud: {BAUD_RATE}")
        
        # Reset before starting
        print("\nResetting device...")
        self.reset()
        time.sleep(0.5)
        
        # Run test suite
        self.test_basic_flashes()
        self.test_white_strip_flashes()
        self.test_timing_variations()
        self.test_color_variations()
        self.test_sequential_storm()
        self.test_all_segments_simultaneous()
        self.test_realistic_lightning()
        self.test_intensity_variations()
        
        # Final reset
        print("Resetting device...")
        self.reset()
        
        print("="*70)
        print(" ALL TESTS COMPLETE")
        print("="*70)
        print("\nFor manual testing, run with --interactive flag\n")
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Serial connection closed.")


def main():
    """Main entry point."""
    # Check command line arguments
    port = SERIAL_PORT
    interactive = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            interactive = True
        else:
            port = sys.argv[1]
    
    if len(sys.argv) > 2 and (sys.argv[2] == "--interactive" or sys.argv[2] == "-i"):
        interactive = True
    
    # Run tests
    tester = None
    try:
        tester = LightningTester(port, BAUD_RATE)
        
        if interactive:
            tester.run_interactive_mode()
        else:
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
