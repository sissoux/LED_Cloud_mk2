#!/usr/bin/env python3
"""
Lightning Control GUI for Cloud Lamp ESP32-C3

Provides a graphical interface to send lightning commands with:
- Timing controls (attack, plateau, release)
- Intensity slider
- Segment selection (RGB segments and white strips)
- Color picker
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import serial
import json
import time

# Serial port configuration
SERIAL_PORT = "COM29"  # Change this to match your port
BAUD_RATE = 115200


class LightningControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cloud Lamp Lightning Control")
        self.root.geometry("600x900")
        self.root.resizable(True, True)
        
        self.serial_port = None
        self.current_color = (255, 255, 255)  # Default white
        
        # Try to connect to serial port
        self.connect_serial()
        
        # Create GUI elements
        self.create_widgets()
        
    def connect_serial(self):
        """Attempt to connect to the ESP32-C3."""
        try:
            self.serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)  # Wait for ESP32 to initialize
            print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", 
                f"Failed to connect to {SERIAL_PORT}\n{str(e)}\n\nYou can still use the GUI, but commands won't be sent.")
            print(f"Serial connection failed: {e}")
    
    def send_command(self, cmd_dict):
        """Send JSON command to ESP32-C3."""
        if self.serial_port and self.serial_port.is_open:
            try:
                cmd_str = json.dumps(cmd_dict) + "\n"
                self.serial_port.write(cmd_str.encode())
                self.serial_port.flush()
                
                # Read response
                time.sleep(0.05)
                if self.serial_port.in_waiting > 0:
                    response = self.serial_port.readline().decode().strip()
                    print(f"Sent: {cmd_str.strip()} -> Response: {response}")
                else:
                    print(f"Sent: {cmd_str.strip()}")
                    
                # Update status
                self.status_label.config(text=f"✓ Sent: {cmd_dict['cmd']}", foreground="green")
                
            except Exception as e:
                print(f"Error sending command: {e}")
                self.status_label.config(text=f"✗ Error: {str(e)}", foreground="red")
        else:
            print(f"Would send: {cmd_dict}")
            self.status_label.config(text="✗ Not connected", foreground="orange")
    
    def create_widgets(self):
        """Create all GUI elements."""
        
        # ===== Connection Status =====
        status_frame = ttk.LabelFrame(self.root, text="Connection Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        connection_text = f"Connected to {SERIAL_PORT}" if self.serial_port else f"Not connected to {SERIAL_PORT}"
        connection_color = "green" if self.serial_port else "red"
        ttk.Label(status_frame, text=connection_text, foreground=connection_color, 
                 font=("Arial", 10, "bold")).pack()
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="blue")
        self.status_label.pack()
        
        # ===== Segment Selection =====
        segment_frame = ttk.LabelFrame(self.root, text="Segment Selection", padding=10)
        segment_frame.pack(fill="x", padx=10, pady=5)
        
        self.segment_var = tk.IntVar(value=0)
        
        segments_info = [
            (0, "Segment 0 (RGB LEDs 0-9)"),
            (1, "Segment 1 (RGB LEDs 10-19)"),
            (2, "Segment 2 (RGB LEDs 20-29)"),
            (3, "Segment 3 (RGB LEDs 30-39)"),
            (4, "Segment 4 (Cool White Strip)"),
            (5, "Segment 5 (Warm White Strip)")
        ]
        
        for seg_num, seg_label in segments_info:
            ttk.Radiobutton(segment_frame, text=seg_label, variable=self.segment_var, 
                           value=seg_num).pack(anchor="w", pady=2)
        
        # ===== Color Selection =====
        color_frame = ttk.LabelFrame(self.root, text="Color Selection (RGB Segments Only)", padding=10)
        color_frame.pack(fill="x", padx=10, pady=5)
        
        # Color preview
        color_preview_frame = ttk.Frame(color_frame)
        color_preview_frame.pack(fill="x", pady=5)
        
        self.color_preview = tk.Canvas(color_preview_frame, width=100, height=40, bg="white", 
                                      highlightthickness=2, highlightbackground="gray")
        self.color_preview.pack(side="left", padx=5)
        
        ttk.Button(color_preview_frame, text="Choose Color", 
                  command=self.choose_color).pack(side="left", padx=5)
        
        self.color_label = ttk.Label(color_preview_frame, text="RGB(255, 255, 255)", 
                                    font=("Arial", 9))
        self.color_label.pack(side="left", padx=10)
        
        # RGB sliders
        ttk.Label(color_frame, text="Or use sliders:").pack(anchor="w", pady=(10, 5))
        
        self.r_var = tk.IntVar(value=255)
        self.g_var = tk.IntVar(value=255)
        self.b_var = tk.IntVar(value=255)
        
        for label, var, color in [("Red", self.r_var, "#ff0000"), 
                                  ("Green", self.g_var, "#00ff00"), 
                                  ("Blue", self.b_var, "#0000ff")]:
            frame = ttk.Frame(color_frame)
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=f"{label}:", width=6).pack(side="left")
            slider = ttk.Scale(frame, from_=0, to=255, orient="horizontal", variable=var,
                             command=lambda v, var=var: self.update_color_preview())
            slider.pack(side="left", fill="x", expand=True, padx=5)
            value_label = ttk.Label(frame, text="255", width=4)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: 
                         lbl.config(text=str(v.get())))
        
        # ===== Timing Controls =====
        timing_frame = ttk.LabelFrame(self.root, text="Lightning Timing (milliseconds)", padding=10)
        timing_frame.pack(fill="x", padx=10, pady=5)
        
        self.attack_var = tk.IntVar(value=50)
        self.plateau_var = tk.IntVar(value=100)
        self.release_var = tk.IntVar(value=200)
        
        for label, var, default in [("Attack", self.attack_var, 50),
                                    ("Plateau", self.plateau_var, 100),
                                    ("Release", self.release_var, 200)]:
            frame = ttk.Frame(timing_frame)
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=f"{label}:", width=10).pack(side="left")
            slider = ttk.Scale(frame, from_=10, to=500, orient="horizontal", variable=var)
            slider.pack(side="left", fill="x", expand=True, padx=5)
            value_label = ttk.Label(frame, text=f"{default}ms", width=6)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: 
                         lbl.config(text=f"{v.get()}ms"))
        
        # ===== Intensity Control =====
        intensity_frame = ttk.LabelFrame(self.root, text="Lightning Intensity", padding=10)
        intensity_frame.pack(fill="x", padx=10, pady=5)
        
        self.intensity_var = tk.DoubleVar(value=1.0)
        
        frame = ttk.Frame(intensity_frame)
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text="Intensity:", width=10).pack(side="left")
        slider = ttk.Scale(frame, from_=0.1, to=1.0, orient="horizontal", variable=self.intensity_var)
        slider.pack(side="left", fill="x", expand=True, padx=5)
        self.intensity_label = ttk.Label(frame, text="100%", width=6)
        self.intensity_label.pack(side="left")
        self.intensity_var.trace_add("write", lambda *args: 
                                    self.intensity_label.config(text=f"{int(self.intensity_var.get()*100)}%"))
        
        # ===== Action Buttons =====
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Strike button (large and prominent)
        strike_btn = ttk.Button(button_frame, text="⚡ STRIKE LIGHTNING ⚡", 
                               command=self.strike_lightning)
        strike_btn.pack(fill="x", pady=5, ipady=10)
        
        # Utility buttons
        utility_frame = ttk.Frame(button_frame)
        utility_frame.pack(fill="x", pady=5)
        
        ttk.Button(utility_frame, text="Reset LEDs", 
                  command=self.reset_leds).pack(side="left", padx=5, expand=True, fill="x")
        
        ttk.Button(utility_frame, text="Quick Storm", 
                  command=self.quick_storm).pack(side="left", padx=5, expand=True, fill="x")
        
        ttk.Button(utility_frame, text="Test All Segments", 
                  command=self.test_all_segments).pack(side="left", padx=5, expand=True, fill="x")
        
        # ===== Presets =====
        preset_frame = ttk.LabelFrame(self.root, text="Quick Presets", padding=10)
        preset_frame.pack(fill="x", padx=10, pady=5)
        
        presets = [
            ("Slow Flash", 100, 200, 300, 1.0),
            ("Quick Flash", 30, 50, 100, 1.0),
            ("Gentle", 80, 150, 250, 0.5),
            ("Intense", 20, 80, 120, 1.0),
        ]
        
        for i, (name, attack, plateau, release, intensity) in enumerate(presets):
            ttk.Button(preset_frame, text=name, 
                      command=lambda a=attack, p=plateau, r=release, i=intensity: 
                      self.apply_preset(a, p, r, i)).grid(row=0, column=i, padx=5, pady=2, sticky="ew")
            preset_frame.columnconfigure(i, weight=1)
    
    def update_color_preview(self):
        """Update color preview canvas when sliders change."""
        r = self.r_var.get()
        g = self.g_var.get()
        b = self.b_var.get()
        self.current_color = (r, g, b)
        
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.color_preview.config(bg=hex_color)
        self.color_label.config(text=f"RGB({r}, {g}, {b})")
    
    def choose_color(self):
        """Open color picker dialog."""
        color = colorchooser.askcolor(color=self.current_color, title="Choose Lightning Color")
        if color[0]:  # color[0] is RGB tuple, color[1] is hex
            r, g, b = [int(c) for c in color[0]]
            self.r_var.set(r)
            self.g_var.set(g)
            self.b_var.set(b)
            self.update_color_preview()
    
    def apply_preset(self, attack, plateau, release, intensity):
        """Apply a timing preset."""
        self.attack_var.set(attack)
        self.plateau_var.set(plateau)
        self.release_var.set(release)
        self.intensity_var.set(intensity)
        self.status_label.config(text="Preset applied", foreground="blue")
    
    def strike_lightning(self):
        """Send lightning command with current settings."""
        segment = self.segment_var.get()
        r, g, b = self.current_color
        attack = self.attack_var.get()
        plateau = self.plateau_var.get()
        release = self.release_var.get()
        intensity = round(self.intensity_var.get(), 2)
        
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
        
        self.send_command(cmd)
    
    def reset_leds(self):
        """Send reset command."""
        self.send_command({"cmd": "reset"})
    
    def quick_storm(self):
        """Trigger a quick storm sequence."""
        import random
        
        for _ in range(5):
            segment = random.randint(0, 3)
            cmd = {
                "cmd": "lightning",
                "segment": segment,
                "r": 255,
                "g": 255,
                "b": 255,
                "attack": random.randint(20, 60),
                "plateau": random.randint(50, 120),
                "release": random.randint(100, 250),
                "intensity": random.uniform(0.7, 1.0)
            }
            self.send_command(cmd)
            time.sleep(random.uniform(0.3, 0.8))
        
        self.status_label.config(text="Storm sequence complete", foreground="green")
    
    def test_all_segments(self):
        """Test each segment sequentially."""
        for segment in range(6):
            if segment <= 3:
                # RGB segments
                cmd = {
                    "cmd": "lightning",
                    "segment": segment,
                    "r": 255,
                    "g": 255,
                    "b": 255,
                    "attack": 50,
                    "plateau": 100,
                    "release": 200,
                    "intensity": 1.0
                }
            else:
                # White strips
                cmd = {
                    "cmd": "lightning",
                    "segment": segment,
                    "r": 0,
                    "g": 0,
                    "b": 0,
                    "attack": 50,
                    "plateau": 100,
                    "release": 200,
                    "intensity": 1.0
                }
            
            self.send_command(cmd)
            time.sleep(0.5)
        
        self.status_label.config(text="All segments tested", foreground="green")
    
    def close(self):
        """Clean up on exit."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()


def main():
    root = tk.Tk()
    app = LightningControlGUI(root)
    
    def on_closing():
        app.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
