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

// Color Temperature Configuration
#define CCT_WARM_KELVIN 2700        // Warm white color temperature in Kelvin
#define CCT_COOL_KELVIN 6000        // Cool white color temperature in Kelvin

// Virtual segment numbers for white strips (for lightning animations)
#define SEGMENT_COOL_WHITE  4       // Cool white strip as virtual segment
#define SEGMENT_WARM_WHITE  5       // Warm white strip as virtual segment
#define TOTAL_SEGMENTS      6       // Total including virtual white strip segments

// Pattern buffer configuration
#define MAX_PATTERN_EVENTS  32      // Maximum number of events in a pattern

// LED Array - FastLED native RGBW support
CRGB leds[LED_COUNT];

// Current brightness levels for white strips
uint8_t warmWhiteBrightness = 0;
uint8_t coolWhiteBrightness = 0;

// Per-LED animation collision prevention
// Indices 0-39: RGB LEDs, 40: Cool White Strip, 41: Warm White Strip
#define LED_BLOCK_COOL_WHITE 40
#define LED_BLOCK_WARM_WHITE 41
#define LED_BLOCK_TOTAL 42
bool ledBlocked[LED_BLOCK_TOTAL] = {false};  // Tracks which LEDs are currently being animated

// Lightning animation state - support up to 5 concurrent animations
#define MAX_LIGHTNING_ANIMATIONS 5
struct LightningState {
    bool active;
    uint8_t segment;
    unsigned long startTime;
    unsigned long attackMs;
    unsigned long plateauMs;
    unsigned long releaseMs;
    float intensity;
    CRGB color;
    // Backup state for restoration after flash
    CRGB segmentBackup[SEGMENT_SIZE];
    uint8_t warmWhiteBackup;
    uint8_t coolWhiteBackup;
};
LightningState lightning[MAX_LIGHTNING_ANIMATIONS] = {
    {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White, {}, 0, 0},
    {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White, {}, 0, 0},
    {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White, {}, 0, 0},
    {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White, {}, 0, 0},
    {false, 0, 0, 50, 100, 200, 1.0f, CRGB::White, {}, 0, 0}
};

// Pattern event structure
struct PatternEvent {
    unsigned long timeMs;       // Time offset from pattern start (milliseconds)
    uint8_t segment;            // Segment to flash
    CRGB color;                 // Flash color
    unsigned long attack;       // Attack time (ms)
    unsigned long plateau;      // Plateau time (ms)
    unsigned long release;      // Release time (ms)
    float intensity;            // Flash intensity (0.0-1.0)
};

// Pattern playback state
struct PatternState {
    bool active;
    unsigned long startTime;
    uint8_t eventCount;
    uint8_t currentEventIndex;
    PatternEvent events[MAX_PATTERN_EVENTS];
} pattern = {false, 0, 0, 0, {}};

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
void writeWarmWhitePWM(uint8_t value);
void writeCoolWhitePWM(uint8_t value);
void updateWhiteStrips(float warm, float cool);
void safeDefaultState();
void updateLightningAnimation();
void startLightning(uint8_t segment, CRGB color, unsigned long attack, unsigned long plateau, unsigned long release, float intensity);
void updatePatternPlayback();
void startPattern();
void stopPattern();
CRGB parsePresetColor(const char* preset);

// LED blocking helper functions
bool checkLEDsAvailable(uint8_t startLED, uint8_t count);
bool checkSegmentAvailable(uint8_t segment);
void blockLEDs(uint8_t startLED, uint8_t count);
void blockSegment(uint8_t segment);
void unblockLEDs(uint8_t startLED, uint8_t count);
void unblockSegment(uint8_t segment);

// Lightning animation helper functions
int8_t findAvailableLightningSlot();
bool anyLightningActive();
void stopAllLightning();

#ifdef DEMO_MODE
void runDemoMode();
#endif

// ============================================================================
// SETUP
// ============================================================================

void setup() {
    // Initialize serial communication with larger RX buffer for pattern commands
    Serial.setRxBufferSize(4096);  // Increase from default 256 bytes to 4KB
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
    updatePatternPlayback();
    
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
    writeWarmWhitePWM(0);
    writeCoolWhitePWM(0);
    
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
    writeWarmWhitePWM(0);
    writeCoolWhitePWM(0);
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
    else if (strcmp(cmd, "cctWhite") == 0) {
        // CCT-based white control: specify target color temperature and intensity
        uint16_t targetCCT = doc["cct"] | 3500;  // Default to mid-range 3500K
        float intensity = doc["intensity"] | 1.0f;
        
        // Clamp CCT to valid range (2700K - 6000K)
        targetCCT = constrain(targetCCT, CCT_WARM_KELVIN, CCT_COOL_KELVIN);
        intensity = constrain(intensity, 0.0f, 1.0f);
        
        // Calculate warm/cool mix using linear interpolation
        // cool_ratio increases as temperature rises from 2700K to 6000K
        float cool_ratio = (float)(targetCCT - CCT_WARM_KELVIN) / (float)(CCT_COOL_KELVIN - CCT_WARM_KELVIN);
        float warm_ratio = 1.0f - cool_ratio;
        
        // Apply intensity to both channels
        float warm = warm_ratio * intensity;
        float cool = cool_ratio * intensity;
        
        updateWhiteStrips(warm, cool);
        Serial.println("{\"status\":\"ok\",\"cmd\":\"cctWhite\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "reset") == 0) {
        safeDefaultState();
        stopAllLightning();  // Stop all lightning animations
        stopPattern();       // Stop any active pattern
        // Clear all LED blocking flags
        for (uint8_t i = 0; i < LED_BLOCK_TOTAL; i++) {
            ledBlocked[i] = false;
        }
        Serial.println("{\"status\":\"ok\",\"cmd\":\"reset\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "lightning") == 0) {
        // Check if we have available animation slots
        if (findAvailableLightningSlot() == -1) {
            Serial.println("{\"status\":\"error\",\"message\":\"Max concurrent animations reached (5)\"}" );
            Serial.flush();
            return;
        }
        
        uint8_t segment = doc["segment"] | 0;
        
        // Check for animation collision on this specific segment
        if (!checkSegmentAvailable(segment)) {
            Serial.println("{\"status\":\"error\",\"message\":\"Segment already being animated\"}");
            Serial.flush();
            return;
        }
        
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
    else if (strcmp(cmd, "solid_color") == 0) {
        uint8_t segment = doc["segment"] | 255;  // 255 = all segments
        CRGB color;
        
        // Check for preset color first
        if (doc["preset"].is<const char*>()) {
            const char* preset = doc["preset"];
            color = parsePresetColor(preset);
        }
        // Check for HSV
        else if (doc["h"].is<uint8_t>()) {
            uint8_t h = doc["h"] | 0;
            uint8_t s = doc["s"] | 255;
            uint8_t v = doc["v"] | 255;
            color = CHSV(h, s, v);
        }
        // Default to RGB
        else {
            uint8_t r = doc["r"] | 0;
            uint8_t g = doc["g"] | 0;
            uint8_t b = doc["b"] | 0;
            color = CRGB(r, g, b);
        }
        
        // Apply to specified segment or all
        if (segment == 255) {
            setAllLEDs(color);
        } else if (segment < NUM_SEGMENTS) {
            setSegmentColor(segment, color);
        }
        
        Serial.println("{\"status\":\"ok\",\"cmd\":\"solid_color\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "pattern") == 0) {
        // Parse pattern events from JSON array
        JsonArray events = doc["events"];
        if (!events.isNull() && events.size() > 0) {
            pattern.eventCount = min((int)events.size(), (int)MAX_PATTERN_EVENTS);
            
            for (uint8_t i = 0; i < pattern.eventCount; i++) {
                JsonObject event = events[i];
                
                pattern.events[i].timeMs = event["time_ms"] | 0;
                pattern.events[i].segment = event["segment"] | 0;
                pattern.events[i].attack = event["attack"] | 50;
                pattern.events[i].plateau = event["plateau"] | 100;
                pattern.events[i].release = event["release"] | 200;
                pattern.events[i].intensity = event["intensity"] | 1.0f;
                
                // Parse color
                uint8_t r = event["r"] | 255;
                uint8_t g = event["g"] | 255;
                uint8_t b = event["b"] | 255;
                pattern.events[i].color = CRGB(r, g, b);
            }
            
            startPattern();
            Serial.print("{\"status\":\"ok\",\"cmd\":\"pattern\",\"event_count\":");
            Serial.print(pattern.eventCount);
            Serial.println("}");
            Serial.flush();
        } else {
            Serial.println("{\"status\":\"error\",\"message\":\"No events in pattern\"}");
            Serial.flush();
        }
    }
    else if (strcmp(cmd, "stop_pattern") == 0) {
        stopPattern();
        Serial.println("{\"status\":\"ok\",\"cmd\":\"stop_pattern\"}");
        Serial.flush();
    }
    else if (strcmp(cmd, "randomSegFlash") == 0) {
        // Check if we have available animation slots
        if (findAvailableLightningSlot() == -1) {
            Serial.println("{\"status\":\"error\",\"message\":\"Max concurrent animations reached (5)\"}" );
            Serial.flush();
            return;
        }
        
        uint8_t intensity = doc["intensity"] | 5;  // Default intensity 5 (mid-range)
        intensity = constrain(intensity, 1, 10);   // Clamp to 1-10
        
        // Random segment (0-3 for RGB segments)
        uint8_t segment = random(0, NUM_SEGMENTS);
        
        // Check for animation collision on this specific segment
        if (!checkSegmentAvailable(segment)) {
            Serial.println("{\"status\":\"error\",\"message\":\"Segment already being animated\"}");
            Serial.flush();
            return;
        }
        
        // Random color (default white)
        CRGB color = CRGB::White;
        if (doc["r"].is<uint8_t>() || doc["g"].is<uint8_t>() || doc["b"].is<uint8_t>()) {
            uint8_t r = doc["r"] | 255;
            uint8_t g = doc["g"] | 255;
            uint8_t b = doc["b"] | 255;
            color = CRGB(r, g, b);
        }
        
        // Scale timing based on intensity (1-10)
        // Attack: Always sudden (1-15ms) - lightning is always sudden
        unsigned long attack = random(1, 16);
        // Plateau: 5-20ms (low) to 50-150ms (high)
        unsigned long plateau = map(intensity, 1, 10, random(5, 21), random(50, 151));
        // Release: 50-150ms (low) to 150-300ms (high)
        unsigned long release = map(intensity, 1, 10, random(50, 151), random(150, 301));
        // Intensity as brightness (0.5-1.0 range)
        float flashIntensity = map(intensity, 1, 10, 50, 100) / 100.0f;
        
        startLightning(segment, color, attack, plateau, release, flashIntensity);
        
        Serial.print("{\"status\":\"ok\",\"cmd\":\"randomSegFlash\",\"segment\":");
        Serial.print(segment);
        Serial.print(",\"intensity\":");
        Serial.print(intensity);
        Serial.print(",\"timing\":[");
        Serial.print(attack);
        Serial.print(",");
        Serial.print(plateau);
        Serial.print(",");
        Serial.print(release);
        Serial.println("]}");
        Serial.flush();
    }
    else if (strcmp(cmd, "randomFlash") == 0) {
        uint8_t intensity = doc["intensity"] | 5;  // Default intensity 5 (mid-range)
        intensity = constrain(intensity, 1, 10);   // Clamp to 1-10
        
        // Random color (default white)
        CRGB color = CRGB::White;
        if (doc["r"].is<uint8_t>() || doc["g"].is<uint8_t>() || doc["b"].is<uint8_t>()) {
            uint8_t r = doc["r"] | 255;
            uint8_t g = doc["g"] | 255;
            uint8_t b = doc["b"] | 255;
            color = CRGB(r, g, b);
        }
        
        // Scale number of LEDs based on intensity
        // Intensity 1: 1-2 LEDs, Intensity 10: 5-20 LEDs
        uint8_t minLEDs = map(intensity, 1, 10, 1, 5);
        uint8_t maxLEDs = map(intensity, 1, 10, 2, 20);
        uint8_t numLEDs = random(minLEDs, maxLEDs + 1);
        numLEDs = constrain(numLEDs, 1, LED_COUNT);
        
        // Try to find an available LED range (up to 5 attempts)
        uint8_t startLED = 0;
        bool foundAvailableRange = false;
        for (uint8_t attempt = 0; attempt < 5; attempt++) {
            uint8_t maxStart = LED_COUNT - numLEDs;
            startLED = random(0, maxStart + 1);
            
            if (checkLEDsAvailable(startLED, numLEDs)) {
                foundAvailableRange = true;
                break;
            }
        }
        
        if (!foundAvailableRange) {
            Serial.println("{\"status\":\"error\",\"message\":\"No available LED range found\"}");
            Serial.flush();
            return;
        }
        
        // Block the LEDs to prevent collisions
        blockLEDs(startLED, numLEDs);
        
        // Backup current LED states
        CRGB ledBackup[LED_COUNT];
        for (uint8_t i = 0; i < LED_COUNT; i++) {
            ledBackup[i] = leds[i];
        }
        
        // Scale timing based on intensity (1-10)
        // Attack: Always sudden (1-15ms) - lightning is always sudden
        unsigned long attack = random(1, 16);
        // Plateau: 5-20ms (low) to 50-150ms (high)
        unsigned long plateau = map(intensity, 1, 10, random(5, 21), random(50, 151));
        // Release: 50-150ms (low) to 150-300ms (high)
        unsigned long release = map(intensity, 1, 10, random(50, 151), random(150, 301));
        // Intensity as brightness (0.5-1.0 range)
        float flashIntensity = map(intensity, 1, 10, 50, 100) / 100.0f;
        
        // Create temporary animation manually since we can't use segment-based approach
        unsigned long startTime = millis();
        unsigned long totalDuration = attack + plateau + release;
        bool animationActive = true;
        
        while (animationActive) {
            unsigned long elapsed = millis() - startTime;
            
            if (elapsed >= totalDuration) {
                // Restore original state
                for (uint8_t i = startLED; i < startLED + numLEDs && i < LED_COUNT; i++) {
                    leds[i] = ledBackup[i];
                }
                FastLED.show();
                animationActive = false;
                break;
            }
            
            float brightness = 0.0f;
            
            // Attack phase
            if (elapsed < attack) {
                brightness = (float)elapsed / (float)attack;
            }
            // Plateau phase
            else if (elapsed < attack + plateau) {
                brightness = 1.0f;
            }
            // Release phase
            else {
                unsigned long releaseElapsed = elapsed - attack - plateau;
                brightness = 1.0f - ((float)releaseElapsed / (float)release);
            }
            
            float finalBrightness = brightness * flashIntensity;
            
            // Apply to random LEDs
            for (uint8_t i = startLED; i < startLED + numLEDs && i < LED_COUNT; i++) {
                CRGB scaledColor = color;
                scaledColor.nscale8_video((uint8_t)(finalBrightness * 255));
                leds[i] = scaledColor;
            }
            FastLED.show();
            delay(5);  // Small delay for smooth animation
        }
        
        Serial.print("{\"status\":\"ok\",\"cmd\":\"randomFlash\",\"start_led\":");
        Serial.print(startLED);
        Serial.print(",\"num_leds\":");
        Serial.print(numLEDs);
        Serial.print(",\"intensity\":");
        Serial.print(intensity);
        Serial.print(",\"timing\":[");
        Serial.print(attack);
        Serial.print(",");
        Serial.print(plateau);
        Serial.print(",");
        Serial.print(release);
        Serial.println("]}");
        Serial.flush();
        
        // Unblock the LEDs after animation completes
        unblockLEDs(startLED, numLEDs);
    }    else if (strcmp(cmd, "fullFlash") == 0) {
        // Check if ALL LEDs and white strips are available
        bool allAvailable = checkLEDsAvailable(0, LED_COUNT) && 
                           !ledBlocked[LED_BLOCK_COOL_WHITE] && 
                           !ledBlocked[LED_BLOCK_WARM_WHITE];
        
        if (!allAvailable) {
            Serial.println("{\"status\":\"error\",\"message\":\"Some LEDs already being animated\"}");
            Serial.flush();
            return;
        }
        
        // Block all LEDs and white strips
        blockLEDs(0, LED_COUNT);
        ledBlocked[LED_BLOCK_COOL_WHITE] = true;
        ledBlocked[LED_BLOCK_WARM_WHITE] = true;
        
        uint8_t intensity = doc["intensity"] | 5;  // Default intensity 5 (mid-range)
        intensity = constrain(intensity, 1, 10);   // Clamp to 1-10
        
        // Color (default white)
        CRGB color = CRGB::White;
        if (doc["r"].is<uint8_t>() || doc["g"].is<uint8_t>() || doc["b"].is<uint8_t>()) {
            uint8_t r = doc["r"] | 255;
            uint8_t g = doc["g"] | 255;
            uint8_t b = doc["b"] | 255;
            color = CRGB(r, g, b);
        }
        
        // Backup current LED states and white strip values
        CRGB ledBackup[LED_COUNT];
        for (uint8_t i = 0; i < LED_COUNT; i++) {
            ledBackup[i] = leds[i];
        }
        uint8_t warmBackup = warmWhiteBrightness;
        uint8_t coolBackup = coolWhiteBrightness;
        
        // Scale timing based on intensity (1-10)
        // Attack: Always sudden (1-15ms) - lightning is always sudden
        unsigned long attack = random(1, 16);
        // Plateau: 5-20ms (low) to 50-150ms (high)
        unsigned long plateau = map(intensity, 1, 10, random(5, 21), random(50, 151));
        // Release: 50-150ms (low) to 150-300ms (high)
        unsigned long release = map(intensity, 1, 10, random(50, 151), random(150, 301));
        // Intensity as brightness (0.5-1.0 range)
        float flashIntensity = map(intensity, 1, 10, 50, 100) / 100.0f;
        
        // Animation loop - flash ALL LEDs and white strips
        unsigned long startTime = millis();
        unsigned long totalDuration = attack + plateau + release;
        bool animationActive = true;
        
        while (animationActive) {
            unsigned long elapsed = millis() - startTime;
            
            if (elapsed >= totalDuration) {
                // Restore original state for all LEDs and white strips
                for (uint8_t i = 0; i < LED_COUNT; i++) {
                    leds[i] = ledBackup[i];
                }
                FastLED.show();
                warmWhiteBrightness = warmBackup;
                coolWhiteBrightness = coolBackup;
                writeWarmWhitePWM(warmWhiteBrightness);
                writeCoolWhitePWM(coolWhiteBrightness);
                animationActive = false;
                break;
            }
            
            float brightness = 0.0f;
            
            // Attack phase
            if (elapsed < attack) {
                brightness = (float)elapsed / (float)attack;
            }
            // Plateau phase
            else if (elapsed < attack + plateau) {
                brightness = 1.0f;
            }
            // Release phase
            else {
                unsigned long releaseElapsed = elapsed - attack - plateau;
                brightness = 1.0f - ((float)releaseElapsed / (float)release);
            }
            
            float finalBrightness = brightness * flashIntensity;
            
            // Apply to ALL RGB LEDs
            for (uint8_t i = 0; i < LED_COUNT; i++) {
                CRGB scaledColor = color;
                scaledColor.nscale8_video((uint8_t)(finalBrightness * 255));
                leds[i] = scaledColor;
            }
            FastLED.show();
            
            // Apply to white strips
            uint8_t whiteBrightness = (uint8_t)(finalBrightness * 255);
            warmWhiteBrightness = whiteBrightness;
            coolWhiteBrightness = whiteBrightness;
            writeWarmWhitePWM(warmWhiteBrightness);
            writeCoolWhitePWM(coolWhiteBrightness);
            
            delay(5);  // Small delay for smooth animation
        }
        
        Serial.print("{\"status\":\"ok\",\"cmd\":\"fullFlash\",\"leds\":");
        Serial.print(LED_COUNT);
        Serial.print(",\"intensity\":");
        Serial.print(intensity);
        Serial.print(",\"timing\":[" );
        Serial.print(attack);
        Serial.print(",");
        Serial.print(plateau);
        Serial.print(",");
        Serial.print(release);
        Serial.println("]}" );
        Serial.flush();
        
        // Unblock all LEDs and white strips after animation completes
        unblockLEDs(0, LED_COUNT);
        ledBlocked[LED_BLOCK_COOL_WHITE] = false;
        ledBlocked[LED_BLOCK_WARM_WHITE] = false;
    }    else {
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

// ============================================================================
// COLOR PARSING
// ============================================================================

CRGB parsePresetColor(const char* preset) {
    // Convert preset name to lowercase for case-insensitive comparison
    String presetStr = String(preset);
    presetStr.toLowerCase();
    
    // FastLED color presets
    if (presetStr == "red") return CRGB::Red;
    if (presetStr == "green") return CRGB::Green;
    if (presetStr == "blue") return CRGB::Blue;
    if (presetStr == "white") return CRGB::White;
    if (presetStr == "black" || presetStr == "off") return CRGB::Black;
    if (presetStr == "yellow") return CRGB::Yellow;
    if (presetStr == "cyan") return CRGB::Cyan;
    if (presetStr == "magenta") return CRGB::Magenta;
    if (presetStr == "orange") return CRGB::Orange;
    if (presetStr == "purple") return CRGB::Purple;
    if (presetStr == "pink") return CRGB::Pink;
    if (presetStr == "lime") return CRGB::Lime;
    if (presetStr == "aqua") return CRGB::Aqua;
    if (presetStr == "navy") return CRGB::Navy;
    if (presetStr == "teal") return CRGB::Teal;
    if (presetStr == "olive") return CRGB::Olive;
    if (presetStr == "maroon") return CRGB::Maroon;
    if (presetStr == "silver") return CRGB::Silver;
    if (presetStr == "gray" || presetStr == "grey") return CRGB::Gray;
    if (presetStr == "gold") return CRGB::Gold;
    if (presetStr == "indigo") return CRGB::Indigo;
    if (presetStr == "violet") return CRGB::Violet;
    if (presetStr == "brown") return CRGB::Brown;
    if (presetStr == "crimson") return CRGB::Crimson;
    if (presetStr == "coral") return CRGB::Coral;
    if (presetStr == "turquoise") return CRGB::Turquoise;
    if (presetStr == "salmon") return CRGB::Salmon;
    if (presetStr == "khaki") return CRGB::Khaki;
    if (presetStr == "plum") return CRGB::Plum;
    if (presetStr == "orchid") return CRGB::Orchid;
    
    // Default to white if unknown
    return CRGB::White;
}

// ============================================================================
// WHITE STRIP PWM HELPERS (with optional inversion)
// ============================================================================

void writeWarmWhitePWM(uint8_t value) {
    // Write PWM value to warm white strip
    // Inverts output if INVERT_WHITE_PWM is defined (for inverted hardware)
#ifdef INVERT_WHITE_PWM
    ledcWrite(WARM_WHITE_PIN, 255 - value);
#else
    ledcWrite(WARM_WHITE_PIN, value);
#endif
}

void writeCoolWhitePWM(uint8_t value) {
    // Write PWM value to cool white strip
    // Inverts output if INVERT_WHITE_PWM is defined (for inverted hardware)
#ifdef INVERT_WHITE_PWM
    ledcWrite(COOL_WHITE_PIN, 255 - value);
#else
    ledcWrite(COOL_WHITE_PIN, value);
#endif
}

void updateWhiteStrips(float warm, float cool) {
    // Clamp values to 0.0-1.0 range
    warm = constrain(warm, 0.0f, 1.0f);
    cool = constrain(cool, 0.0f, 1.0f);
    
    // Convert to PWM values (0-255)
    warmWhiteBrightness = (uint8_t)(warm * 255);
    coolWhiteBrightness = (uint8_t)(cool * 255);
    
    // Update PWM outputs
    writeWarmWhitePWM(warmWhiteBrightness);
    writeCoolWhitePWM(coolWhiteBrightness);
}

// ============================================================================
// LED BLOCKING HELPER FUNCTIONS
// ============================================================================

bool checkLEDsAvailable(uint8_t startLED, uint8_t count) {
    // Check if a range of LEDs is available (not blocked)
    for (uint8_t i = startLED; i < startLED + count && i < LED_COUNT; i++) {
        if (ledBlocked[i]) {
            return false;  // At least one LED is blocked
        }
    }
    return true;  // All LEDs in range are available
}

bool checkSegmentAvailable(uint8_t segment) {
    // Check if a segment is available for animation
    if (segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3)
        uint8_t startLED = segment * SEGMENT_SIZE;
        return checkLEDsAvailable(startLED, SEGMENT_SIZE);
    } else if (segment == SEGMENT_COOL_WHITE) {
        // Cool white strip
        return !ledBlocked[LED_BLOCK_COOL_WHITE];
    } else if (segment == SEGMENT_WARM_WHITE) {
        // Warm white strip
        return !ledBlocked[LED_BLOCK_WARM_WHITE];
    }
    return false;  // Invalid segment
}

void blockLEDs(uint8_t startLED, uint8_t count) {
    // Mark a range of LEDs as blocked
    for (uint8_t i = startLED; i < startLED + count && i < LED_COUNT; i++) {
        ledBlocked[i] = true;
    }
}

void blockSegment(uint8_t segment) {
    // Mark a segment as blocked
    if (segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3)
        uint8_t startLED = segment * SEGMENT_SIZE;
        blockLEDs(startLED, SEGMENT_SIZE);
    } else if (segment == SEGMENT_COOL_WHITE) {
        // Cool white strip
        ledBlocked[LED_BLOCK_COOL_WHITE] = true;
    } else if (segment == SEGMENT_WARM_WHITE) {
        // Warm white strip
        ledBlocked[LED_BLOCK_WARM_WHITE] = true;
    }
}

void unblockLEDs(uint8_t startLED, uint8_t count) {
    // Mark a range of LEDs as available
    for (uint8_t i = startLED; i < startLED + count && i < LED_COUNT; i++) {
        ledBlocked[i] = false;
    }
}

void unblockSegment(uint8_t segment) {
    // Mark a segment as available
    if (segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3)
        uint8_t startLED = segment * SEGMENT_SIZE;
        unblockLEDs(startLED, SEGMENT_SIZE);
    } else if (segment == SEGMENT_COOL_WHITE) {
        // Cool white strip
        ledBlocked[LED_BLOCK_COOL_WHITE] = false;
    } else if (segment == SEGMENT_WARM_WHITE) {
        // Warm white strip
        ledBlocked[LED_BLOCK_WARM_WHITE] = false;
    }
}

// ============================================================================
// LIGHTNING ANIMATION HELPER FUNCTIONS
// ============================================================================

int8_t findAvailableLightningSlot() {
    // Find the first available (inactive) lightning animation slot
    // Returns slot index (0-4) or -1 if all slots are in use
    for (uint8_t i = 0; i < MAX_LIGHTNING_ANIMATIONS; i++) {
        if (!lightning[i].active) {
            return i;
        }
    }
    return -1;  // All slots are in use
}

bool anyLightningActive() {
    // Check if any lightning animation is currently active
    for (uint8_t i = 0; i < MAX_LIGHTNING_ANIMATIONS; i++) {
        if (lightning[i].active) {
            return true;
        }
    }
    return false;
}

void stopAllLightning() {
    // Stop all lightning animations and unblock their segments
    for (uint8_t i = 0; i < MAX_LIGHTNING_ANIMATIONS; i++) {
        if (lightning[i].active) {
            unblockSegment(lightning[i].segment);
            lightning[i].active = false;
        }
    }
}

// ============================================================================
// LIGHTNING ANIMATION
// ============================================================================

void startLightning(uint8_t segment, CRGB color, unsigned long attack, unsigned long plateau, unsigned long release, float intensity) {
    if (segment > SEGMENT_WARM_WHITE) return;  // Max segment is 5 (warm white)
    
    // Find an available lightning slot
    int8_t slot = findAvailableLightningSlot();
    if (slot == -1) return;  // No slots available
    
    // Block the segment to prevent collisions
    blockSegment(segment);
    
    lightning[slot].active = true;
    lightning[slot].segment = segment;
    lightning[slot].startTime = millis();
    lightning[slot].attackMs = attack;
    lightning[slot].plateauMs = plateau;
    lightning[slot].releaseMs = release;
    lightning[slot].intensity = intensity;
    lightning[slot].color = color;
    
    // Backup current state before lightning flash
    if (segment < NUM_SEGMENTS) {
        // RGB LED segment (0-3): backup segment colors
        uint8_t startLED = segment * SEGMENT_SIZE;
        for (uint8_t i = 0; i < SEGMENT_SIZE && (startLED + i) < LED_COUNT; i++) {
            lightning[slot].segmentBackup[i] = leds[startLED + i];
        }
    } else if (segment == SEGMENT_COOL_WHITE) {
        // Cool white strip: backup current brightness
        lightning[slot].coolWhiteBackup = coolWhiteBrightness;
    } else if (segment == SEGMENT_WARM_WHITE) {
        // Warm white strip: backup current brightness
        lightning[slot].warmWhiteBackup = warmWhiteBrightness;
    }
}

void updateLightningAnimation() {
    // Process all active lightning animations
    for (uint8_t slot = 0; slot < MAX_LIGHTNING_ANIMATIONS; slot++) {
        if (!lightning[slot].active) continue;  // Skip inactive slots
        
        unsigned long elapsed = millis() - lightning[slot].startTime;
        unsigned long totalDuration = lightning[slot].attackMs + lightning[slot].plateauMs + lightning[slot].releaseMs;
        
        // Check if animation is complete
        if (elapsed >= totalDuration) {
            // Restore previous state
            if (lightning[slot].segment < NUM_SEGMENTS) {
                // RGB LED segment: restore backed up colors
                uint8_t startLED = lightning[slot].segment * SEGMENT_SIZE;
                for (uint8_t i = 0; i < SEGMENT_SIZE && (startLED + i) < LED_COUNT; i++) {
                    leds[startLED + i] = lightning[slot].segmentBackup[i];
                }
                FastLED.show();
            } else if (lightning[slot].segment == SEGMENT_COOL_WHITE) {
                // Cool white strip: restore previous brightness
                coolWhiteBrightness = lightning[slot].coolWhiteBackup;
                writeCoolWhitePWM(coolWhiteBrightness);
            } else if (lightning[slot].segment == SEGMENT_WARM_WHITE) {
                // Warm white strip: restore previous brightness
                warmWhiteBrightness = lightning[slot].warmWhiteBackup;
                writeWarmWhitePWM(warmWhiteBrightness);
            }
            
            // Unblock the segment
            unblockSegment(lightning[slot].segment);
            lightning[slot].active = false;
            continue;  // Move to next slot
        }
        
        float brightness = 0.0f;
        
        // Attack phase (ramp up)
        if (elapsed < lightning[slot].attackMs) {
            brightness = (float)elapsed / (float)lightning[slot].attackMs;
        }
        // Plateau phase (hold at full brightness)
        else if (elapsed < lightning[slot].attackMs + lightning[slot].plateauMs) {
            brightness = 1.0f;
        }
        // Release phase (ramp down)
        else {
            unsigned long releaseElapsed = elapsed - lightning[slot].attackMs - lightning[slot].plateauMs;
            brightness = 1.0f - ((float)releaseElapsed / (float)lightning[slot].releaseMs);
        }
        
        // Apply brightness with intensity scaling and update segment
        float finalBrightness = brightness * lightning[slot].intensity;
        
        if (lightning[slot].segment < NUM_SEGMENTS) {
            // RGB LED segment (0-3): apply brightness to color
            CRGB scaledColor = lightning[slot].color;
            scaledColor.nscale8_video((uint8_t)(finalBrightness * 255));
            setSegmentColor(lightning[slot].segment, scaledColor);
        } else if (lightning[slot].segment == SEGMENT_COOL_WHITE) {
            // Cool white strip: apply brightness to PWM
            uint8_t pwmValue = (uint8_t)(finalBrightness * 255);
            writeCoolWhitePWM(pwmValue);
        } else if (lightning[slot].segment == SEGMENT_WARM_WHITE) {
            // Warm white strip: apply brightness to PWM
            uint8_t pwmValue = (uint8_t)(finalBrightness * 255);
            writeWarmWhitePWM(pwmValue);
        }
    }
}

// ============================================================================
// PATTERN PLAYBACK
// ============================================================================

void startPattern() {
    pattern.active = true;
    pattern.startTime = millis();
    pattern.currentEventIndex = 0;
}

void stopPattern() {
    pattern.active = false;
    pattern.currentEventIndex = 0;
    pattern.eventCount = 0;
}

void updatePatternPlayback() {
    if (!pattern.active) return;
    if (pattern.currentEventIndex >= pattern.eventCount) {
        // All events have been processed
        pattern.active = false;
        return;
    }
    
    unsigned long elapsed = millis() - pattern.startTime;
    
    // Check if it's time to trigger the next event
    while (pattern.currentEventIndex < pattern.eventCount && 
           elapsed >= pattern.events[pattern.currentEventIndex].timeMs) {
        
        // Only trigger if we have an available lightning slot and the segment isn't blocked
        PatternEvent* event = &pattern.events[pattern.currentEventIndex];
        
        if (findAvailableLightningSlot() != -1 && checkSegmentAvailable(event->segment)) {
            startLightning(
                event->segment,
                event->color,
                event->attack,
                event->plateau,
                event->release,
                event->intensity
            );
        }
        
        pattern.currentEventIndex++;
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
