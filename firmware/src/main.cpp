/**
 * Cloud Lamp ESP32-C3 Firmware
 * 
 * This firmware controls a suspended cloud lamp with:
 * - SK6812 RGBW addressable LEDs (40 LEDs in 4 segments)
 * - Warm white LED strip (PWM control)
 * - Cool white LED strip (PWM control)
 * 
 * Communication: Serial JSON commands from Raspberry Pi Zero W
 */

#include <Arduino.h>
#include <FastLED.h>
#include <ArduinoJson.h>

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================

// SK6812 RGBW LED Strip Configuration
#define LED_PIN         5          // Data pin for SK6812
#define LED_COUNT       40          // Total number of LEDs
#define SEGMENT_SIZE    10          // LEDs per segment
#define NUM_SEGMENTS    4           // Number of segments

// PWM Configuration for Static White Strips
#define WARM_WHITE_PIN  3          // PWM pin for warm white strip
#define COOL_WHITE_PIN  4          // PWM pin for cool white strip
#define PWM_FREQ        5000        // PWM frequency in Hz
#define PWM_RESOLUTION  8           // 8-bit resolution (0-255)
#define PWM_CHANNEL_WARM 0          // PWM channel for warm white
#define PWM_CHANNEL_COOL 1          // PWM channel for cool white

// Virtual segment numbers for white strips (for lightning animations)
#define SEGMENT_COOL_WHITE  4       // Cool white strip as virtual segment
#define SEGMENT_WARM_WHITE  5       // Warm white strip as virtual segment
#define TOTAL_SEGMENTS      6       // Total including virtual white strip segments

// LED Array - FastLED native RGBW support
CRGB leds[LED_COUNT];

// Current brightness levels for white strips
uint8_t warmWhiteBrightness = 0;
uint8_t coolWhiteBrightness = 0;

// Lightning animation state
struct LightningState {
    bool active;
    uint8_t segment;
    unsigned long startTime;
    unsigned long attackMs;
    unsigned long plateauMs;
    unsigned long releaseMs;
    float intensity;
    CRGB color;
} lightning = {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White};

// Demo mode variables
#ifdef DEMO_MODE
unsigned long lastDemoUpdate = 0;
uint16_t demoStep = 0;  // uint16_t to handle step counts > 255
uint8_t demoPattern = 0;
#endif

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================

void setupHardware();
void processSerialCommand();
void setSegmentColor(uint8_t segment, CRGB color);
void setAllLEDs(CRGB color);
void updateWhiteStrips(float warm, float cool);
void safeDefaultState();
void updateLightningAnimation();
void startLightning(uint8_t segment, CRGB color, unsigned long attack, unsigned long plateau, unsigned long release, float intensity);
#ifdef DEMO_MODE
void runDemoMode();
#endif

// ============================================================================
// SETUP
// ============================================================================

void setup() {
    // Initialize serial communication
    Serial.begin(115200);
    while (!Serial && millis() < 3000); // Wait up to 3s for serial
    
#ifdef DEMO_MODE
    Serial.println("Cloud Lamp ESP32-C3 Initializing...");
#endif
    
    // Initialize hardware
    setupHardware();
    
    // Set safe default state
    safeDefaultState();
    
#ifdef DEMO_MODE
    Serial.println("{\"status\":\"ready\",\"device\":\"cloud_lamp_esp32c3\",\"mode\":\"DEMO\"}");
    Serial.println("\n=== DEMO MODE - SK6812 RGBW LED TESTING ===");
    Serial.println("Testing SK6812 RGBW LEDs on pin 5");
    Serial.println("Using FastLED .setRgbw(RgbwDefault()) for automatic W channel");
    Serial.println("Patterns: Segment Test -> Rainbow -> Chase -> Color Cycle -> White Strips -> Finale");
    Serial.println("Full demo cycle running...\\n");
#else
    Serial.println("{\"status\":\"ready\",\"device\":\"cloud_lamp_esp32c3\"}");
    Serial.flush(); // Ensure startup message is sent
#endif
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
#ifdef DEMO_MODE
    // Run demo mode patterns
    runDemoMode();
#else
    // Process incoming serial commands
    if (Serial.available()) {
        processSerialCommand();
    }
    
    // Update active animations
    updateLightningAnimation();
    
    delay(10); // Small delay to prevent tight loop
#endif
}

// ============================================================================
// HARDWARE SETUP
// ============================================================================

void setupHardware() {
    // Initialize FastLED for SK6812 RGBW with native RGBW support
    FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, LED_COUNT).setRgbw(RgbwDefault());
    FastLED.setBrightness(255);
    FastLED.clear();
    FastLED.show();
    
    // Initialize PWM for white strips (ESP32 Arduino Core 3.x API)
    ledcAttach(WARM_WHITE_PIN, PWM_FREQ, PWM_RESOLUTION);
    ledcAttach(COOL_WHITE_PIN, PWM_FREQ, PWM_RESOLUTION);
    
    // Set white strips to off
    ledcWrite(WARM_WHITE_PIN, 0);
    ledcWrite(COOL_WHITE_PIN, 0);
    
#ifdef DEMO_MODE
    Serial.println("Hardware initialized");
#endif
}

// ============================================================================
// SAFE DEFAULT STATE
// ============================================================================

void safeDefaultState() {
    // Turn off all LEDs
    FastLED.clear();
    FastLED.show();
    
    // Turn off white strips
    ledcWrite(WARM_WHITE_PIN, 0);
    ledcWrite(COOL_WHITE_PIN, 0);
    warmWhiteBrightness = 0;
    coolWhiteBrightness = 0;
}

// ============================================================================
// SERIAL COMMAND PROCESSING
// ============================================================================

void processSerialCommand() {
    String jsonString = Serial.readStringUntil('\n');
    jsonString.trim();
    
    if (jsonString.length() == 0) return;
    
    // Parse JSON command
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, jsonString);
    
    if (error) {
        Serial.print("{\"status\":\"error\",\"message\":\"JSON parse error: ");
        Serial.print(error.c_str());
        Serial.println("\"}");
        Serial.flush();
        return;
    }
    
    // Extract command
    const char* cmd = doc["cmd"];
    if (!cmd) {
        Serial.println("{\"status\":\"error\",\"message\":\"Missing cmd field\"}");
        Serial.flush();
        return;
    }
    
    // Process commands
    if (strcmp(cmd, "ping") == 0) {
        Serial.println("{\"status\":\"ok\",\"cmd\":\"ping\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "white") == 0) {
        float warm = doc["warm"] | 0.0f;
        float cool = doc["cool"] | 0.0f;
        updateWhiteStrips(warm, cool);
        Serial.println("{\"status\":\"ok\",\"cmd\":\"white\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "reset") == 0) {
        safeDefaultState();
        lightning.active = false;  // Stop any active animations
        Serial.println("{\"status\":\"ok\",\"cmd\":\"reset\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "lightning") == 0) {
        uint8_t segment = doc["segment"] | 0;
        unsigned long attack = doc["attack"] | 50;   // Default 50ms
        unsigned long plateau = doc["plateau"] | 100; // Default 100ms
        unsigned long release = doc["release"] | 200; // Default 200ms
        float intensity = doc["intensity"] | 1.0f;    // Default 100%
        
        // Parse color (default to white)
        uint8_t r = doc["r"] | 255;
        uint8_t g = doc["g"] | 255;
        uint8_t b = doc["b"] | 255;
        CRGB color = CRGB(r, g, b);
        
        // Clamp intensity to 0.0-1.0 range
        intensity = constrain(intensity, 0.0f, 1.0f);
        
        startLightning(segment, color, attack, plateau, release, intensity);
        Serial.println("{\"status\":\"ok\",\"cmd\":\"lightning\"}");
        Serial.flush();
    }
    else {
        Serial.print("{\"status\":\"error\",\"message\":\"Unknown command: ");
        Serial.print(cmd);
        Serial.println("\"}");
        Serial.flush();
    }
}

// ============================================================================
// LED CONTROL FUNCTIONS
// ============================================================================

void setSegmentColor(uint8_t segment, CRGB color) {
    if (segment >= NUM_SEGMENTS) return;
    
    uint8_t startLED = segment * SEGMENT_SIZE;
    uint8_t endLED = startLED + SEGMENT_SIZE;
    
    for (uint8_t i = startLED; i < endLED && i < LED_COUNT; i++) {
        leds[i] = color;
    }
    FastLED.show();
}

void setAllLEDs(CRGB color) {
    for (uint8_t i = 0; i < LED_COUNT; i++) {
        leds[i] = color;
    }
    FastLED.show();
}

void updateWhiteStrips(float warm, float cool) {
    // Clamp values to 0.0-1.0 range
    warm = constrain(warm, 0.0f, 1.0f);
    cool = constrain(cool, 0.0f, 1.0f);
    
    // Convert to PWM values (0-255)
    warmWhiteBrightness = (uint8_t)(warm * 255);
    coolWhiteBrightness = (uint8_t)(cool * 255);
    
    // Update PWM outputs
    ledcWrite(WARM_WHITE_PIN, warmWhiteBrightness);
    ledcWrite(COOL_WHITE_PIN, coolWhiteBrightness);
}

// ============================================================================
// LIGHTNING ANIMATION
// ============================================================================

void startLightning(uint8_t segment, CRGB color, unsigned long attack, unsigned long plateau, unsigned long release, float intensity) {
    if (segment > SEGMENT_WARM_WHITE) return;  // Max segment is 5 (warm white)
    
    lightning.active = true;
    lightning.segment = segment;
    lightning.startTime = millis();
    lightning.attackMs = attack;
    lightning.plateauMs = plateau;
    lightning.releaseMs = release;
    lightning.intensity = intensity;
    lightning.color = color;
    
    // Clear the segment initially
    if (segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3)
        setSegmentColor(segment, CRGB::Black);
    } else if (segment == SEGMENT_COOL_WHITE) {
        // Cool white strip
        ledcWrite(COOL_WHITE_PIN, 0);
    } else if (segment == SEGMENT_WARM_WHITE) {
        // Warm white strip
        ledcWrite(WARM_WHITE_PIN, 0);
    }
}

void updateLightningAnimation() {
    if (!lightning.active) return;
    
    unsigned long elapsed = millis() - lightning.startTime;
    unsigned long totalDuration = lightning.attackMs + lightning.plateauMs + lightning.releaseMs;
    
    // Check if animation is complete
    if (elapsed >= totalDuration) {
        if (lightning.segment < NUM_SEGMENTS) {
            // RGB LED segment
            setSegmentColor(lightning.segment, CRGB::Black);
        } else if (lightning.segment == SEGMENT_COOL_WHITE) {
            // Cool white strip
            ledcWrite(COOL_WHITE_PIN, 0);
        } else if (lightning.segment == SEGMENT_WARM_WHITE) {
            // Warm white strip
            ledcWrite(WARM_WHITE_PIN, 0);
        }
        lightning.active = false;
        return;
    }
    
    float brightness = 0.0f;
    
    // Attack phase (ramp up)
    if (elapsed < lightning.attackMs) {
        brightness = (float)elapsed / (float)lightning.attackMs;
    }
    // Plateau phase (hold at full brightness)
    else if (elapsed < lightning.attackMs + lightning.plateauMs) {
        brightness = 1.0f;
    }
    // Release phase (ramp down)
    else {
        unsigned long releaseElapsed = elapsed - lightning.attackMs - lightning.plateauMs;
        brightness = 1.0f - ((float)releaseElapsed / (float)lightning.releaseMs);
    }
    
    // Apply brightness with intensity scaling and update segment
    float finalBrightness = brightness * lightning.intensity;
    
    if (lightning.segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3): apply brightness to color
        CRGB scaledColor = lightning.color;
        scaledColor.nscale8_video((uint8_t)(finalBrightness * 255));
        setSegmentColor(lightning.segment, scaledColor);
    } else if (lightning.segment == SEGMENT_COOL_WHITE) {
        // Cool white strip: apply brightness to PWM
        uint8_t pwmValue = (uint8_t)(finalBrightness * 255);
        ledcWrite(COOL_WHITE_PIN, pwmValue);
    } else if (lightning.segment == SEGMENT_WARM_WHITE) {
        // Warm white strip: apply brightness to PWM
        uint8_t pwmValue = (uint8_t)(finalBrightness * 255);
        ledcWrite(WARM_WHITE_PIN, pwmValue);
    }
}

// ============================================================================
// DEMO MODE - LED CONNECTION TESTING
// ============================================================================

#ifdef DEMO_MODE
void runDemoMode() {
    unsigned long currentMillis = millis();
    
    // Update every 50ms for smooth animations
    if (currentMillis - lastDemoUpdate < 50) {
        return;
    }
    lastDemoUpdate = currentMillis;
    
    switch (demoPattern) {
        // Pattern 0: Individual segment color test (Red, Green, Blue, Yellow)
        case 0:
            if (demoStep == 0) {
                Serial.println("Pattern 1: Segment Color Test - Red");
                for (uint8_t seg = 0; seg < NUM_SEGMENTS; seg++) {
                    setSegmentColor(seg, CRGB::Black);
                }
                setSegmentColor(0, CRGB::Red);
            } else if (demoStep == 40) {  // 2 seconds per color (40 * 50ms)
                Serial.println("Pattern 1: Segment Color Test - Green");
                setSegmentColor(0, CRGB::Black);
                setSegmentColor(1, CRGB::Green);
            } else if (demoStep == 80) {
                Serial.println("Pattern 1: Segment Color Test - Blue");
                setSegmentColor(1, CRGB::Black);
                setSegmentColor(2, CRGB::Blue);
            } else if (demoStep == 120) {
                Serial.println("Pattern 1: Segment Color Test - Yellow");
                setSegmentColor(2, CRGB::Black);
                setSegmentColor(3, CRGB::Yellow);
            } else if (demoStep >= 160) {  // Total ~8 seconds
                setSegmentColor(3, CRGB::Black);
                demoPattern++;
                demoStep = 0;
                return;
            }
            demoStep++;
            break;
            
        // Pattern 1: Rainbow cycle through all LEDs
        case 1:
            if (demoStep == 0) {
                Serial.println("Pattern 2: Rainbow Cycle");
            }
            for (uint8_t i = 0; i < LED_COUNT; i++) {
                leds[i] = CHSV((demoStep*6 + i * 256 / LED_COUNT) % 256, 255, 255);
            }
            FastLED.show();
            demoStep++;
            if (demoStep >= 260) { // ~13 seconds (260 * 50ms)
                demoPattern++;
                demoStep = 0;
            }
            break;
            
        // Pattern 2: Chase pattern
        case 2:
            if (demoStep == 0) {
                Serial.println("Pattern 3: Chase Pattern");
            }
            FastLED.clear();
            for (uint8_t i = 0; i < LED_COUNT; i++) {
                if ((i + (demoStep / 1)) % 4 == 0) { // Divide by 1 to slow down chase
                    leds[i] = CRGB::Cyan;
                }
            }
            FastLED.show();
            demoStep++;
            if (demoStep >= 200) { // ~10 seconds (200 * 50ms)
                demoPattern++;
                demoStep = 0;
            }
            break;
            
        // Pattern 3: All segments same color cycling
        case 3:
            if (demoStep == 0) {
                Serial.println("Pattern 4: All Segments Color Cycle");
                setAllLEDs(CRGB::Red);
            } else if (demoStep == 20) {
                setAllLEDs(CRGB::Green);
            } else if (demoStep == 40) {
                setAllLEDs(CRGB::Blue);
            } else if (demoStep == 60) {
                setAllLEDs(CRGB::White);
            } else if (demoStep == 80) {
                setAllLEDs(CRGB::Purple);
            } else if (demoStep >= 100) {
                setAllLEDs(CRGB::Black);
                demoPattern++;
                demoStep = 0;
                return;
            }
            demoStep++;
            break;
            
        // Pattern 4: Warm white strip test
        case 4:
            if (demoStep == 0) {
                Serial.println("Pattern 5: Warm White Strip Test");
                updateWhiteStrips(0.0, 0.0);
            } else if (demoStep == 10) {
                updateWhiteStrips(0.25, 0.0);
            } else if (demoStep == 20) {
                updateWhiteStrips(0.5, 0.0);
            } else if (demoStep == 30) {
                updateWhiteStrips(0.75, 0.0);
            } else if (demoStep == 40) {
                updateWhiteStrips(1.0, 0.0);
            } else if (demoStep >= 60) {
                updateWhiteStrips(0.0, 0.0);
                demoPattern++;
                demoStep = 0;
                return;
            }
            demoStep++;
            break;
            
        // Pattern 5: Cool white strip test
        case 5:
            if (demoStep == 0) {
                Serial.println("Pattern 6: Cool White Strip Test");
                updateWhiteStrips(0.0, 0.0);
            } else if (demoStep == 10) {
                updateWhiteStrips(0.0, 0.25);
            } else if (demoStep == 20) {
                updateWhiteStrips(0.0, 0.5);
            } else if (demoStep == 30) {
                updateWhiteStrips(0.0, 0.75);
            } else if (demoStep == 40) {
                updateWhiteStrips(0.0, 1.0);
            } else if (demoStep >= 60) {
                updateWhiteStrips(0.0, 0.0);
                demoPattern++;
                demoStep = 0;
                return;
            }
            demoStep++;
            break;
            
        // Pattern 6: Both white strips together
        case 6:
            if (demoStep == 0) {
                Serial.println("Pattern 7: Both White Strips Test");
                updateWhiteStrips(0.0, 0.0);
            } else if (demoStep == 10) {
                updateWhiteStrips(0.5, 0.5);
            } else if (demoStep == 20) {
                updateWhiteStrips(1.0, 1.0);
            } else if (demoStep >= 40) {
                updateWhiteStrips(0.0, 0.0);
                demoPattern++;
                demoStep = 0;
                return;
            }
            demoStep++;
            break;
            
        // Pattern 7: Everything together - grand finale
        case 7:
            if (demoStep == 0) {
                Serial.println("Pattern 8: Grand Finale - All LEDs!");
            }
            // Rainbow on RGB LEDs
            for (uint8_t i = 0; i < LED_COUNT; i++) {
                leds[i] = CHSV((demoStep * 6 + i * 256 / LED_COUNT) % 256, 255, 255);
            }
            FastLED.show();
            // Pulse white strips
            float intensity = (sin(demoStep * 0.03) + 1.0) / 2.0;
            updateWhiteStrips(intensity, intensity);
            demoStep++;
            if (demoStep >= 400) { // ~20 seconds (400 * 50ms)
                Serial.println("\n=== Demo cycle complete. Restarting... ===\n");
                demoPattern = 0;
                demoStep = 0;
                setAllLEDs(CRGB::Black);
                updateWhiteStrips(0.0, 0.0);
                delay(2000); // 2 second pause before restart
            }
            break;
    }
}
#endif
