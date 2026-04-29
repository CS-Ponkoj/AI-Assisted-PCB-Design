# Version 4: Interactive PCB Visual Upgrade

## Summary

Version 4 upgrades the prototype from a static PCB layout view into an interactive PCB design inspection experience. The main goal is to make the visual board output easier for a PCB designer, reviewer, or demo audience to understand before opening the detailed handoff tables.

The existing Base, Ollama LLM, and Gemini API requirement modes remain unchanged. The generated BOM, pin map, netlist, power budget, readiness review, exports, and dropdown handoff sections still work as before.

## What Changed

### Interactive PCB Layout Visual

The PCB layout visual now supports click-based inspection for:

- USB-C connector
- 3.3 V regulator zone
- ESP32 module
- ESP32 antenna keepout
- I2C pullups
- status LED
- reset circuit
- test points
- mounting holes
- populated sensors
- optional DNP sensor footprints
- key routed nets/traces

Clicking an item updates an inspector panel below the board visual.

### Inspector Panel

The inspector panel shows design information connected to the clicked board item:

- assembly status
- placement guidance
- related BOM rows
- related pin-map rows
- related netlist rows

This makes the visual output feel closer to a PCB review tool instead of only a drawing.

### Trace Inspection

Important traces are now interactive:

- `VBUS_5V`
- `3V3`
- `GND`
- `I2C_SDA`
- `I2C_SCL`
- status/reset routing

Hovering over traces visually highlights them, and clicking opens related net details.

### Footprint View Toggle

The Streamlit UI now includes a toggle:

```text
Show all footprint options
```

When enabled, the PCB visual shows both populated sensors and optional DNP footprints.

When disabled, the visual shows only the parts populated for the current user request.

### Board-Level Design Details

The visual now includes clearer board-level design information:

- target board size: `45 mm x 35 mm`
- board type: 2-layer FR-4 prototype
- USB-C connector side
- ESP32 antenna keepout
- mounting-hole coordinate notes
- test-point inspection notes

## Files Updated

```text
app.py
src/visuals.py
tests/test_app.py
README.md
VERSION_4.md
```

## Why This Matters

Before Version 4, the PCB visual helped users see where parts were placed, but it did not explain enough by itself. A PCB designer still had to jump between the visual, BOM, pin map, netlist, and layout notes.

Version 4 connects those pieces together. The visual now acts as the first review surface, while the detailed tables remain the source of truth.

## Validation

The upgrade was checked with:

```bash
python -m py_compile app.py src\base_assistant.py src\data_loader.py src\design_generator.py src\exports.py src\gemini_assistant.py src\ollama_assistant.py src\parser.py src\readiness.py src\validation.py src\visuals.py
python -m unittest
```

Result:

```text
31 tests passed
```

Streamlit smoke checks also returned HTTP `200` for both the local app and deployed app.

## Scope

Version 4 is still a controlled prototype upgrade. It does not add real PCB autorouting, KiCad generation, Gerber generation, electrical simulation, or manufacturing signoff.

The PCB visual remains a designer-facing handoff aid, not a replacement for CAD layout verification.
