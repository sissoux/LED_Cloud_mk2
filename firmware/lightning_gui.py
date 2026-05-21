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
        self.root.geometry("1100x700")  # Wider, shorter window
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
        """Create all GUI elements in a compact 2-column layout."""
        
        # ===== Connection Status (top, full width) =====
        status_frame = ttk.LabelFrame(self.root, text="Connection Status", padding=5)
        status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        connection_text = f"Connected to {SERIAL_PORT}" if self.serial_port else f"Not connected to {SERIAL_PORT}"
        connection_color = "green" if self.serial_port else "red"
        ttk.Label(status_frame, text=connection_text, foreground=connection_color, 
                 font=("Arial", 9, "bold")).pack(side="left", padx=10)
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="blue")
        self.status_label.pack(side="left", padx=10)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        
        # ===== LEFT COLUMN =====
        left_column = ttk.Frame(self.root)
        left_column.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Segment Selection (compact horizontal layout)
        segment_frame = ttk.LabelFrame(left_column, text="Segment", padding=5)
        segment_frame.pack(fill="x", pady=(0, 5))
        
        self.segment_var = tk.IntVar(value=0)
        
        # First row: RGB segments
        rgb_frame = ttk.Frame(segment_frame)
        rgb_frame.pack(fill="x")
        for i in range(4):
            ttk.Radiobutton(rgb_frame, text=f"S{i}", variable=self.segment_var, 
                           value=i, width=4).pack(side="left", padx=2)
        
        # Second row: White segments
        white_frame = ttk.Frame(segment_frame)
        white_frame.pack(fill="x")
        ttk.Radiobutton(white_frame, text="Cool W", variable=self.segment_var, 
                       value=4, width=7).pack(side="left", padx=2)
        ttk.Radiobutton(white_frame, text="Warm W", variable=self.segment_var, 
                       value=5, width=7).pack(side="left", padx=2)
        
        # Solid Color Controls (compact)
        solid_color_frame = ttk.LabelFrame(left_column, text="Base Solid Color", padding=5)
        solid_color_frame.pack(fill="x", pady=(0, 5))
        
        # Color mode selection
        mode_frame = ttk.Frame(solid_color_frame)
        mode_frame.pack(fill="x", pady=2)
        
        self.solid_color_mode = tk.StringVar(value="rgb")
        ttk.Radiobutton(mode_frame, text="RGB", variable=self.solid_color_mode, 
                       value="rgb", command=self.toggle_solid_color_mode).pack(side="left", padx=2)
        ttk.Radiobutton(mode_frame, text="HSV", variable=self.solid_color_mode, 
                       value="hsv", command=self.toggle_solid_color_mode).pack(side="left", padx=2)
        ttk.Radiobutton(mode_frame, text="Preset", variable=self.solid_color_mode, 
                       value="preset", command=self.toggle_solid_color_mode).pack(side="left", padx=2)
        
        # RGB controls (visible by default) - compact sliders
        self.rgb_solid_frame = ttk.Frame(solid_color_frame)
        self.rgb_solid_frame.pack(fill="x", pady=2)
        
        self.solid_r_var = tk.IntVar(value=255)
        self.solid_g_var = tk.IntVar(value=0)
        self.solid_b_var = tk.IntVar(value=0)
        
        for label, var in [("R", self.solid_r_var), ("G", self.solid_g_var), ("B", self.solid_b_var)]:
            frame = ttk.Frame(self.rgb_solid_frame)
            frame.pack(fill="x", pady=1)
            ttk.Label(frame, text=f"{label}:", width=2).pack(side="left")
            ttk.Scale(frame, from_=0, to=255, orient="horizontal", variable=var).pack(side="left", fill="x", expand=True, padx=2)
            value_label = ttk.Label(frame, text="255", width=3)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: lbl.config(text=str(v.get())))
        
        # HSV controls (hidden by default)
        self.hsv_solid_frame = ttk.Frame(solid_color_frame)
        
        self.solid_h_var = tk.IntVar(value=0)
        self.solid_s_var = tk.IntVar(value=255)
        self.solid_v_var = tk.IntVar(value=255)
        
        for label, var in [("H", self.solid_h_var), ("S", self.solid_s_var), ("V", self.solid_v_var)]:
            frame = ttk.Frame(self.hsv_solid_frame)
            frame.pack(fill="x", pady=1)
            ttk.Label(frame, text=f"{label}:", width=2).pack(side="left")
            ttk.Scale(frame, from_=0, to=255, orient="horizontal", variable=var).pack(side="left", fill="x", expand=True, padx=2)
            value_label = ttk.Label(frame, text=str(var.get()), width=3)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: lbl.config(text=str(v.get())))
        
        # Preset controls (hidden by default)
        self.preset_solid_frame = ttk.Frame(solid_color_frame)
        
        self.preset_color_var = tk.StringVar(value="red")
        preset_colors = ["red", "green", "blue", "white", "yellow", "cyan", "magenta", 
                        "orange", "purple", "pink", "lime", "aqua", "navy", "teal"]
        ttk.Combobox(self.preset_solid_frame, textvariable=self.preset_color_var, 
                    values=preset_colors, state="readonly", width=10).pack(fill="x", padx=2)
        
        # Solid color buttons
        solid_btn_frame = ttk.Frame(solid_color_frame)
        solid_btn_frame.pack(fill="x", pady=2)
        
        ttk.Button(solid_btn_frame, text="Set Segment", 
                  command=self.set_solid_color).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(solid_btn_frame, text="Set All", 
                  command=self.set_solid_color_all).pack(side="left", padx=2, expand=True, fill="x")
        
        # CCT White Controls (compact)
        cct_white_frame = ttk.LabelFrame(left_column, text="CCT White", padding=5)
        cct_white_frame.pack(fill="x", pady=(0, 5))
        
        # Temperature
        cct_temp_frame = ttk.Frame(cct_white_frame)
        cct_temp_frame.pack(fill="x", pady=1)
        ttk.Label(cct_temp_frame, text="Temp:", width=5).pack(side="left")
        self.cct_temp_var = tk.IntVar(value=3500)
        ttk.Scale(cct_temp_frame, from_=2700, to=6000, orient="horizontal", 
                 variable=self.cct_temp_var).pack(side="left", fill="x", expand=True, padx=2)
        self.cct_temp_label = ttk.Label(cct_temp_frame, text="3500K", width=6)
        self.cct_temp_label.pack(side="left")
        self.cct_temp_var.trace_add("write", lambda *args: 
                                   self.cct_temp_label.config(text=f"{self.cct_temp_var.get()}K"))
        
        # Intensity
        cct_int_frame = ttk.Frame(cct_white_frame)
        cct_int_frame.pack(fill="x", pady=1)
        ttk.Label(cct_int_frame, text="Int:", width=5).pack(side="left")
        self.cct_intensity_var = tk.DoubleVar(value=1.0)
        ttk.Scale(cct_int_frame, from_=0.0, to=1.0, orient="horizontal", 
                 variable=self.cct_intensity_var).pack(side="left", fill="x", expand=True, padx=2)
        self.cct_intensity_label = ttk.Label(cct_int_frame, text="100%", width=6)
        self.cct_intensity_label.pack(side="left")
        self.cct_intensity_var.trace_add("write", lambda *args: 
                                        self.cct_intensity_label.config(text=f"{int(self.cct_intensity_var.get()*100)}%"))
        
        # CCT presets (compact)
        cct_preset_frame = ttk.Frame(cct_white_frame)
        cct_preset_frame.pack(fill="x", pady=2)
        
        cct_presets = [("Warm", 2700), ("Neutral", 3500), ("Cool", 6000)]
        for name, temp in cct_presets:
            ttk.Button(cct_preset_frame, text=name, width=7,
                      command=lambda t=temp: self.set_cct_preset(t)).pack(side="left", padx=1)
        
        ttk.Button(cct_white_frame, text="Apply CCT", 
                  command=self.send_cct_white).pack(fill="x", pady=2)
        
        # ===== RIGHT COLUMN =====
        right_column = ttk.Frame(self.root)
        right_column.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Lightning Flash Color (compact)
        color_frame = ttk.LabelFrame(right_column, text="Lightning Color", padding=5)
        color_frame.pack(fill="x", pady=(0, 5))
        
        # Color preview and picker
        color_top = ttk.Frame(color_frame)
        color_top.pack(fill="x", pady=2)
        
        self.color_preview = tk.Canvas(color_top, width=60, height=30, bg="white", 
                                      highlightthickness=1, highlightbackground="gray")
        self.color_preview.pack(side="left", padx=2)
        
        ttk.Button(color_top, text="Pick Color", 
                  command=self.choose_color).pack(side="left", padx=2)
        
        self.color_label = ttk.Label(color_top, text="RGB(255,255,255)", font=("Arial", 8))
        self.color_label.pack(side="left", padx=5)
        
        # RGB sliders (compact)
        self.r_var = tk.IntVar(value=255)
        self.g_var = tk.IntVar(value=255)
        self.b_var = tk.IntVar(value=255)
        
        for label, var in [("R", self.r_var), ("G", self.g_var), ("B", self.b_var)]:
            frame = ttk.Frame(color_frame)
            frame.pack(fill="x", pady=1)
            ttk.Label(frame, text=f"{label}:", width=2).pack(side="left")
            ttk.Scale(frame, from_=0, to=255, orient="horizontal", variable=var,
                     command=lambda v, var=var: self.update_color_preview()).pack(side="left", fill="x", expand=True, padx=2)
            value_label = ttk.Label(frame, text="255", width=3)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: lbl.config(text=str(v.get())))
        
        # Timing Controls (compact)
        timing_frame = ttk.LabelFrame(right_column, text="Timing (ms)", padding=5)
        timing_frame.pack(fill="x", pady=(0, 5))
        
        self.attack_var = tk.IntVar(value=50)
        self.plateau_var = tk.IntVar(value=100)
        self.release_var = tk.IntVar(value=200)
        
        for label, var, default in [("Attack", self.attack_var, 50),
                                    ("Plateau", self.plateau_var, 100),
                                    ("Release", self.release_var, 200)]:
            frame = ttk.Frame(timing_frame)
            frame.pack(fill="x", pady=1)
            ttk.Label(frame, text=f"{label}:", width=7).pack(side="left")
            ttk.Scale(frame, from_=10, to=500, orient="horizontal", variable=var).pack(side="left", fill="x", expand=True, padx=2)
            value_label = ttk.Label(frame, text=f"{default}ms", width=5)
            value_label.pack(side="left")
            var.trace_add("write", lambda *args, lbl=value_label, v=var: 
                         lbl.config(text=f"{v.get()}ms"))
        
        # Intensity
        intensity_frame = ttk.LabelFrame(right_column, text="Intensity", padding=5)
        intensity_frame.pack(fill="x", pady=(0, 5))
        
        self.intensity_var = tk.DoubleVar(value=1.0)
        
        frame = ttk.Frame(intensity_frame)
        frame.pack(fill="x", pady=1)
        ttk.Label(frame, text="Level:", width=7).pack(side="left")
        ttk.Scale(frame, from_=0.1, to=1.0, orient="horizontal", variable=self.intensity_var).pack(side="left", fill="x", expand=True, padx=2)
        self.intensity_label = ttk.Label(frame, text="100%", width=5)
        self.intensity_label.pack(side="left")
        self.intensity_var.trace_add("write", lambda *args: 
                                    self.intensity_label.config(text=f"{int(self.intensity_var.get()*100)}%"))
        
        # Action Buttons
        button_frame = ttk.LabelFrame(right_column, text="Actions", padding=5)
        button_frame.pack(fill="x", pady=(0, 5))
        
        # Strike button
        ttk.Button(button_frame, text="⚡ STRIKE LIGHTNING ⚡", 
                  command=self.strike_lightning).pack(fill="x", pady=2, ipady=5)
        
        # Utility buttons row
        util_frame = ttk.Frame(button_frame)
        util_frame.pack(fill="x", pady=2)
        
        ttk.Button(util_frame, text="Reset", 
                  command=self.reset_leds).pack(side="left", padx=1, expand=True, fill="x")
        ttk.Button(util_frame, text="Storm", 
                  command=self.quick_storm).pack(side="left", padx=1, expand=True, fill="x")
        ttk.Button(util_frame, text="Test All", 
                  command=self.test_all_segments).pack(side="left", padx=1, expand=True, fill="x")
        
        # Random Flash Effects (compact)
        random_frame = ttk.LabelFrame(right_column, text="Random Flash", padding=5)
        random_frame.pack(fill="x", pady=(0, 5))
        
        # Intensity selector
        int_frame = ttk.Frame(random_frame)
        int_frame.pack(fill="x", pady=2)
        
        ttk.Label(int_frame, text="Intensity:", width=7).pack(side="left")
        self.random_intensity_var = tk.IntVar(value=5)
        ttk.Scale(int_frame, from_=1, to=10, orient="horizontal", 
                 variable=self.random_intensity_var).pack(side="left", fill="x", expand=True, padx=2)
        self.random_intensity_label = ttk.Label(int_frame, text="5", width=3)
        self.random_intensity_label.pack(side="left")
        self.random_intensity_var.trace_add("write", lambda *args: 
                                           self.random_intensity_label.config(text=str(self.random_intensity_var.get())))
        
        # Random buttons
        btn_frame = ttk.Frame(random_frame)
        btn_frame.pack(fill="x", pady=2)
        
        ttk.Button(btn_frame, text="Rand Seg", 
                  command=self.random_seg_flash).pack(side="left", padx=1, expand=True, fill="x")
        ttk.Button(btn_frame, text="Rand LEDs", 
                  command=self.random_flash).pack(side="left", padx=1, expand=True, fill="x")
        ttk.Button(btn_frame, text="Full Flash", 
                  command=self.full_flash).pack(side="left", padx=1, expand=True, fill="x")
        
        # Presets
        preset_frame = ttk.LabelFrame(right_column, text="Quick Presets", padding=5)
        preset_frame.pack(fill="x")
        
        presets = [
            ("Slow", 100, 200, 300, 1.0),
            ("Quick", 30, 50, 100, 1.0),
            ("Gentle", 80, 150, 250, 0.5),
            ("Intense", 20, 80, 120, 1.0),
        ]
        
        for i, (name, attack, plateau, release, intensity) in enumerate(presets):
            row = i // 2
            col = i % 2
            ttk.Button(preset_frame, text=name, 
                      command=lambda a=attack, p=plateau, r=release, i=intensity: 
                      self.apply_preset(a, p, r, i)).grid(row=row, column=col, padx=2, pady=2, sticky="ew")
        
        preset_frame.columnconfigure(0, weight=1)
        preset_frame.columnconfigure(1, weight=1)
    
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
    
    def toggle_solid_color_mode(self):
        """Toggle between RGB, HSV, and Preset color modes for solid color."""
        mode = self.solid_color_mode.get()
        
        # Hide all frames
        self.rgb_solid_frame.pack_forget()
        self.hsv_solid_frame.pack_forget()
        self.preset_solid_frame.pack_forget()
        
        # Show selected frame
        if mode == "rgb":
            self.rgb_solid_frame.pack(fill="x", pady=5)
        elif mode == "hsv":
            self.hsv_solid_frame.pack(fill="x", pady=5)
        elif mode == "preset":
            self.preset_solid_frame.pack(fill="x", pady=5)
    
    def set_solid_color(self):
        """Set solid color for selected segment."""
        segment = self.segment_var.get()
        mode = self.solid_color_mode.get()
        
        cmd = {"cmd": "solid_color", "segment": segment}
        
        if mode == "rgb":
            cmd["r"] = self.solid_r_var.get()
            cmd["g"] = self.solid_g_var.get()
            cmd["b"] = self.solid_b_var.get()
        elif mode == "hsv":
            cmd["h"] = self.solid_h_var.get()
            cmd["s"] = self.solid_s_var.get()
            cmd["v"] = self.solid_v_var.get()
        elif mode == "preset":
            cmd["preset"] = self.preset_color_var.get()
        
        self.send_command(cmd)
    
    def set_solid_color_all(self):
        """Set solid color for all segments."""
        mode = self.solid_color_mode.get()
        
        cmd = {"cmd": "solid_color", "segment": 255}  # 255 = all segments
        
        if mode == "rgb":
            cmd["r"] = self.solid_r_var.get()
            cmd["g"] = self.solid_g_var.get()
            cmd["b"] = self.solid_b_var.get()
        elif mode == "hsv":
            cmd["h"] = self.solid_h_var.get()
            cmd["s"] = self.solid_s_var.get()
            cmd["v"] = self.solid_v_var.get()
        elif mode == "preset":
            cmd["preset"] = self.preset_color_var.get()
        
        self.send_command(cmd)
    
    def set_cct_preset(self, temp):
        """Set CCT temperature to a preset value."""
        self.cct_temp_var.set(temp)
    
    def send_cct_white(self):
        """Send CCT white command with current settings."""
        temp = self.cct_temp_var.get()
        intensity = self.cct_intensity_var.get()
        
        cmd = {
            "cmd": "cctWhite",
            "cct": temp,
            "intensity": intensity
        }
        
        self.send_command(cmd)
    
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
    
    def random_seg_flash(self):
        """Trigger random segment flash."""
        intensity = self.random_intensity_var.get()
        r, g, b = self.current_color
        
        cmd = {
            "cmd": "randomSegFlash",
            "intensity": intensity,
            "r": r,
            "g": g,
            "b": b
        }
        
        self.send_command(cmd)
    
    def random_flash(self):
        """Trigger random LEDs flash."""
        intensity = self.random_intensity_var.get()
        r, g, b = self.current_color
        
        cmd = {
            "cmd": "randomFlash",
            "intensity": intensity,
            "r": r,
            "g": g,
            "b": b
        }
        
        self.send_command(cmd)
    
    def full_flash(self):
        """Trigger full flash on ALL LEDs and white strips."""
        intensity = self.random_intensity_var.get()
        r, g, b = self.current_color
        
        cmd = {
            "cmd": "fullFlash",
            "intensity": intensity,
            "r": r,
            "g": g,
            "b": b
        }
        
        self.send_command(cmd)
    
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
