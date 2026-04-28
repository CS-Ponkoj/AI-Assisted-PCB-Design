# PCB Design Generator Demo Talking Points

## What Is This Prototype?

This prototype converts a controlled natural-language PCB request into a PCB designer handoff for a 2-layer ESP32 sensor board.

The fixed architecture is:

```text
USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus
```

The user can change the sensing requirements, but the app only selects from supported sensor modules. Unsupported requests are reported instead of being invented.

## What Data Does It Use?

The app uses local structured data files.

- `data/sensors/<sensor>/sensor.json`
  Contains sensor name, sensing keywords, I2C address, pins, supply voltage, current estimate, footprint guidance, and layout notes.

- `data/board_template.json`
  Contains the fixed board architecture: ESP32, USB-C input, regulator, reset circuit, LED, pullups, test points, and layout rules.

- `data/requirement_keywords.json`
  Contains unsupported request categories such as GPS, camera, microphone, battery, and display.

This keeps engineering data separate from the Streamlit UI code.

## How Is User Input Parsed?

The base parser uses custom Python logic, not an external NLP library.

The main parser file is:

```text
src/parser.py
```

It lowercases the user input and matches words or phrases against keywords loaded from the sensor JSON files.

Example:

```text
"temperature, humidity, and brightness"
```

maps to:

```text
temperature + humidity -> AHT20
brightness / light -> BH1750
```

`src/ai_assistant.py` adds controlled local synonyms, such as:

```text
room comfort -> temperature + humidity
air freshness -> air quality
```

No OpenAI API, LangChain, spaCy, or NLTK is required for Base mode.

## What Is The LLM Mode?

The LLM assistant is optional.

It uses:

```text
src/llm_assistant.py
```

The app can call an Ollama-compatible model server using:

```text
OLLAMA_URL
OLLAMA_MODEL
```

The default model is:

```text
qwen2.5:3b
```

Base mode is selected first and works without any model server. If LLM mode is selected but the server is unavailable, the app falls back to Base mode.

The LLM output is not trusted blindly. It is validated against the supported sensor library before any PCB output is generated.

## What Is The Workflow?

1. User enters a board requirement.
2. User selects Base or LLM assistant mode.
3. User clicks `Generate PCB Handoff`.
4. The app parses the requirement.
5. The app selects supported sensors.
6. Unsupported requests are flagged.
7. The app generates the PCB handoff package.
8. The app shows a Design Readiness Review.
9. The app displays the PCB layout visual first.
10. Detailed sections are available as dropdowns.
11. User can export BOM, pin map, netlist, Markdown report, or JSON report.

## How Is The PCB Layout Made?

The top-view PCB layout is generated with custom SVG code.

The main file is:

```text
src/visuals.py
```

The app does not use KiCad, Altium, or a real autorouter.

The layout visual is built from:

- fixed board outline
- fixed USB-C, regulator, ESP32, antenna keepout, and mounting-hole areas
- sensor positions from sensor JSON files
- selected sensors from the user input

Selected sensors are marked:

```text
INSTALL
```

Unselected optional footprints are marked:

```text
DNP OPTION
```

The SVG is displayed inside Streamlit using an HTML iframe.

## How Are The Engineering Outputs Made?

The app generates a structured design package using:

```text
src/design_generator.py
```

It creates:

- Project summary
- Design assumptions
- Electrical input/output table
- Bill of Materials
- Pin map
- Netlist
- Power budget
- Schematic summary
- PCB layout instructions
- Fabrication checklist
- Bring-up checklist

The outputs are generated from the board template plus the selected sensor JSON data.

## What Is The BOM?

BOM means Bill of Materials.

It is the list of parts needed to assemble the board.

It includes reference designators, part names, values, footprints, quantities, roles, and notes.

If the user removes a sensor from the input, the BOM changes because that sensor and its related entries are no longer part of the selected design.

## What Is The Netlist?

The netlist shows electrical connections.

Example nets:

```text
USB_5V
3V3
GND
I2C_SDA
I2C_SCL
```

The netlist tells a PCB designer which pins should be electrically connected.

## What Is The Design Readiness Review?

The readiness panel checks whether the generated design is ready to hand off.

It can return:

```text
Ready
Needs Review
Blocked
```

It checks selected sensors, unsupported requests, power margin, optional pins, and validation status.

## What Libraries And Technologies Are Used?

- `Streamlit`
  Used for the web UI, forms, tables, expanders, status panels, and download buttons.

- `Graphviz`
  Used for system architecture and schematic connectivity diagrams.

- Custom SVG generation
  Used for the main PCB top-view visual.

- Python standard library
  Used for JSON loading, CSV export, environment variables, HTTP calls to Ollama, and unit testing.

- Ollama-compatible model server
  Optional LLM provider for natural-language extraction.

- `unittest`
  Used for automated tests.

## What This Prototype Does Not Do Yet

This is not a production PCB CAD tool.

It does not:

- generate KiCad files
- generate Gerbers
- autoroute traces
- run electrical simulation
- replace a PCB designer

It creates a structured, human-readable PCB handoff that a designer can understand and use as a starting point.

## One-Sentence Summary

This prototype converts a constrained natural-language PCB request into a designer-readable ESP32 sensor-board handoff using structured sensor data, controlled validation, generated visuals, exportable engineering tables, and optional LLM assistance.
