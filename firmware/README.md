# Cloud Lamp ESP32-C3 Firmware

This is the firmware for the Cloud Lamp project running on a Seeed Studio XIAO ESP32-C3.

## Hardware

- **Board**: Seeed Studio XIAO ESP32-C3
- **LEDs**: 40x SK6812 RGBW addressable LEDs (4 segments of 10 LEDs each)
- **White Strips**: 
  - Warm white LED strip (PWM control on D1)
  - Cool white LED strip (PWM control on D2)

## Pin Configuration

| Function | Pin |
|----------|-----|
| SK6812 Data | D0 |
| Warm White PWM | D1 |
| Cool White PWM | D2 |

## Building and Uploading

### Using PlatformIO CLI

```bash
# Build the firmware
pio run

# Upload to board
pio run --target upload

# Open serial monitor
pio device monitor
```

### Using VS Code

1. Open the `firmware` folder in VS Code
2. Click the PlatformIO icon in the sidebar
3. Click "Build" to compile
4. Click "Upload" to flash the board
5. Click "Monitor" to view serial output

## Testing

Once uploaded, open the serial monitor at 115200 baud. You should see:

```
Cloud Lamp ESP32-C3 Initializing...
Hardware initialized
Safe default state set
{"status":"ready","device":"cloud_lamp_esp32c3"}
```

### Test Commands

Send these JSON commands over serial (each on a new line):

```json
{"cmd":"ping"}
{"cmd":"white","warm":0.5,"cool":0.3}
{"cmd":"reset"}
```

## Current Implementation Status

✅ Basic firmware structure  
✅ Serial JSON command parser  
✅ FastLED initialization  
✅ PWM control for white strips  
✅ Safe default state on boot  
✅ Ping command  
✅ White strip control command  

⏳ Lighting modes (Idle, Sunrise, Sunset, Storm)  
⏳ Lightning flash effects  
⏳ Chain lightning  
⏳ Segment control  

## Dependencies

- FastLED ^3.6.0 - For SK6812 control
- ArduinoJson ^7.0.0 - For JSON command parsing

## Notes

- FastLED doesn't natively support SK6812 RGBW's white channel
- The white channel will need custom handling or a different library
- Consider using NeoPixelBus library for full RGBW support if needed
