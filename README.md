# Cloud Lamp Project Overview

## Goal

Build a large suspended cloud lamp with dynamic lighting effects.

The system must support:
- animated storm/lightning effects inside the cloud;
- chained lightning propagation between cloud zones;
- soft sunrise and sunset simulation;
- static high-quality white lighting using dedicated high-CRI LED strips;
- future audio synchronization from a Raspberry Pi Zero W.

## Hardware Architecture

### High-level controller

- Raspberry Pi Zero W mk1
- Runs Python
- Connects to Wi-Fi
- Retrieves local time and sunrise/sunset information
- Runs lighting scenarios
- Plays ambient audio / thunder sounds
- Sends high-level lighting commands to the low-level LED controller

### Low-level LED controller

- Seeed Studio XIAO ESP32-C3
- Responsible for real-time LED control
- Receives commands from the Raspberry Pi over serial UART or USB serial
- Generates LED animations locally
- Handles PWM dimming for static white LED strips
- Handles SK6812 RGBW timing

## LED Configuration

### Addressable strip

- 1x SK6812 RGBW strip
- Initial configuration: 40 LEDs total
- Divided into 4 logical segments of 10 LEDs each

Segments:

```text
Segment 0: LEDs 0–9
Segment 1: LEDs 10–19
Segment 2: LEDs 20–29
Segment 3: LEDs 30–39
```

The SK6812 strip is used for:

- lightning flashes;
- intra-cloud movement;
- colored ambience;
- localized light pulses;
- blue/white storm effects.

### Static white strips

There are two non-addressable high-CRI white LED strips:

- Cool white strip → PWM dimming
- Warm white strip → PWM dimming

These are used for:

- realistic white light;
- sunrise/sunset transitions;
- soft ambient illumination;
- high-quality warm/cool color temperature blending.

The static strips should be controlled independently with PWM.

## Suggested Control Model

The Raspberry Pi should not stream individual LED frames continuously.

Instead, it should send high-level commands to the ESP32-C3, such as:

```json
{"cmd":"mode","name":"idle"}
{"cmd":"mode","name":"sunrise","duration_s":900}
{"cmd":"mode","name":"sunset","duration_s":1200}
{"cmd":"flash","segment":1,"intensity":1.0,"duration_ms":80}
{"cmd":"chain_lightning","start_segment":0,"direction":1,"intensity":1.0}
{"cmd":"storm","enabled":true,"density":0.4}
{"cmd":"white","warm":0.35,"cool":0.65}
```

The ESP32-C3 should execute animations locally once commanded.

## Firmware Responsibilities

The ESP32-C3 firmware should provide:

- SK6812 RGBW output control;
- 4 logical LED segments;
- independent PWM output for warm white strip;
- independent PWM output for cool white strip;
- serial command parser;
- basic animation engine;
- non-blocking timing using millis();
- brightness limiting;
- safe default state on boot;
- optional watchdog / failsafe if Raspberry Pi stops sending commands.

## Lighting Modes

### Idle

Soft low-level cloud glow.

Example:

- warm white: low brightness
- cool white: very low brightness
- SK6812: subtle slow breathing

### Sunrise

Slow transition:

- start from very dim warm amber;
- increase warm white gradually;
- add cool white slowly near the end;
- optionally add soft orange/pink RGBW tones on the SK6812.

### Sunset

Reverse of sunrise:

- reduce cool white;
- increase warm/orange tones;
- fade to dim warm night mode.

### Storm

Randomized lightning behavior:

- sudden bright white flashes;
- short bursts between 20 ms and 150 ms;
- chained propagation across segments;
- occasional blue/cold afterglow;
- random delays between flashes.

Example lightning chain:

1. Segment 0 flash
2. 30 ms delay
3. Segment 1 flash
4. 20 ms delay
5. Segment 2 flash
6. 50 ms delay
7. Segment 3 diffuse afterglow

### Manual white mode

Directly set warm/cool brightness:

```json
{"cmd":"white","warm":0.8,"cool":0.2}
```

Useful for calibration and normal lamp behavior.

## Raspberry Pi Software Responsibilities

The Raspberry Pi Python app should:

- open the serial connection to the ESP32-C3;
- send JSON line commands;
- calculate sunrise/sunset times using astral;
- schedule daily lighting scenarios;
- play audio files for rain/thunder;
- optionally synchronize thunder sound delay with lightning events;
- expose future API/MQTT/Home Assistant integration.

## Python Libraries

Suggested libraries:

- pyserial
- astral
- pygame or sounddevice

## Communication Protocol

Use newline-delimited JSON over serial.

Each command is one JSON object followed by \n.

Example:

```json
{"cmd":"ping"}
{"cmd":"mode","name":"storm"}
{"cmd":"chain_lightning","start_segment":2,"direction":-1,"intensity":0.8}
```

ESP32-C3 should respond with simple status messages:

```json
{"status":"ok"}
{"status":"error","message":"unknown command"}
{"status":"ready"}
```

## Development Priorities

### Phase 1: ESP32-C3 Firmware Foundation

- Bring up ESP32-C3 firmware
- Control SK6812 RGBW strip
- Define 4 segments
- Control warm/cool PWM channels
- Implement serial JSON commands

### Phase 2: Lighting Effects Implementation

- Implement basic lighting modes
- Implement lightning flash and chain effects
- Add brightness limiting and fades

### Phase 3: Raspberry Pi Controller

- Raspberry Pi Python controller
- Serial communication
- Sunrise/sunset scheduling
- Simple command-line test interface

### Phase 4: Audio & Advanced Integration

- Audio playback
- Storm mode with synchronized thunder
- Optional web/MQTT/Home Assistant integration

## Design Philosophy

The Raspberry Pi is the high-level scenario controller.

The ESP32-C3 is the real-time lighting engine.

- Avoid relying on the Raspberry Pi for precise LED timing.
- Avoid streaming LED frames from the Pi unless absolutely necessary.
- Prefer high-level commands and local animation execution on the ESP32-C3.