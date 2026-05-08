---
name: termux-api
description: Termux:API — control Android phone hardware and system functions from Termux CLI. Covers location, calls, SMS, clipboard, notifications, camera, audio, sensors, and more. Tested on Android + Termux (Python 3.13, AArch64).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, termux, termux-api, phone-control, sms, location, clipboard, sensors]
    related_skills: [android-termux-python-packages]
---

# Termux:API

Control Android phone hardware and system functions from Termux command line. Requires the **Termux:API** app installed from F-Droid or Google Play.

## Verify Installation

```bash
termux-location -p gps -r once   # test call, returns JSON on success
termux-battery-status            # → {percentage: 22, status: "DISCHARGING", ...}
```

## Core Commands

### 📍 Location
```bash
termux-location -p <provider> -r <request>
# providers: gps / network / passive
# requests: once / last / updates
# example: termux-location -p gps -r once
# returns: {"latitude": 23.1242, "longitude": 113.6062, "accuracy": 3.79, ...}
```

### 🔋 Battery
```bash
termux-battery-status
# returns: {percentage, status, temperature, health, plugged, ...}
```

### 📱 Telephony
```bash
termux-telephony-call <number>          # call a number
termux-call-log                          # list recent calls
termux-telephony-deviceinfo             # device/carrier info
termux-telephony-cellinfo               # cell tower info
```

### 💬 SMS
```bash
termux-sms-send -n <number> -m <message>  # send SMS
termux-sms-inbox                          # read inbox
termux-sms-list                           # list messages
```

### 📋 Clipboard
```bash
termux-clipboard-get        # read clipboard
termux-clipboard-set "text"  # write clipboard
```

### 🔔 Notifications
```bash
termux-notification -t "title" -c "content"   # post notification
termux-notification-list                            # list active
termux-notification-remove <id>                    # dismiss
termux-notification-channel                         # manage channels
```

### 📷 Camera
```bash
termux-camera-info              # list cameras
termux-camera-photo <camera-id>  # take photo → stdout
```

### 🎤 Audio / Media
```bash
termux-microphone-record -f out.3gp      # record audio
termux-media-player play <file>           # play audio
termux-media-scan <path>                  # scan media into system
termux-tts-engines                         # list TTS engines
termux-tts-speak "hello"                   # text-to-speech
termux-audio-info                          # audio properties
```

### 💡 Hardware Controls
```bash
termux-torch on|off                        # flashlight
termux-vibrate [duration_ms]               # vibrate
termux-brightness <0-255>                  # screen brightness
termux-volume <type> <volume>              # volume control
```

### 🌐 Network
```bash
termux-wifi-connectioninfo        # current WiFi info
termux-wifi-scaninfo               # nearby networks
termux-wifi-enable on|off         # toggle WiFi
```

### 📡 IR / NFC / USB
```bash
termux-infrared-transmit <pattern>   # IR blaster transmit
termux-infrared-frequencies          # query supported IR frequencies
termux-nfc                           # NFC operations
termux-usb                           # USB device access
```

### ☁️ Sensors
```bash
termux-sensor -s <sensor-name>       # read sensor
termux-sensor -l                      # list all sensors
```

### 📲 Opening Apps / URLs
```bash
termux-open-url <url>                # open URL in browser/app
termux-open <file>                   # open file with system handler
termux-share <file>                  # share via system share sheet
```
> **Note:** `termux-open` cannot directly launch an app by name (e.g., "open WeChat"). It needs a URL (mailto:, tel:, https://...) or a file path. To open an app, use its registered URL scheme if known (e.g., `weixin://` for WeChat — if registered).

### 🔐 Security
```bash
termux-fingerprint                    # prompt fingerprint auth
termux-keystore                       # Android keystore access
```

### 📱 App Info
```bash
termux-apps-info-app-version-name     # version of an app
termux-apps-info-env-variable         # app environment vars
```

### 🛠️ System
```bash
termux-info          # full system info
termux-job-scheduler # schedule background jobs
termux-wake-lock     # prevent sleep
termux-wake-unlock   # allow sleep
termux-reload-settings
termux-reset
```

## Key Insights from Testing

1. **GPS works great** — `termux-location -p gps -r once` returns lat=23.1242, lon=113.6062 with ~3.8m accuracy on Android
2. **No `-g` flag** — the docs show `-p provider -r request`, not `-g` (tried `-g dense` and got illegal option error)
3. **Battery gives full JSON** — health, temperature (40.1°C), cycle count (496), current (889000μA), voltage (3667mV), percentage (22%)
4. **App launch requires URL scheme** — cannot say "open WeChat", need to know the URI scheme
5. **All commands return JSON** — machine-readable, good for scripting
6. **~70 commands available** — full list at `$PREFIX/bin/termux-*`, including infrared-frequencies, keystore, nfc, sensor batching, etc.

## Skill Dependencies

Requires:
- Termux app
- Termux:API app (separate from Termux)
- Termux API addon installed

Install Termux:API:
```bash
pkg install termux-api
# or install from F-Droid (recommended for latest version)
```
