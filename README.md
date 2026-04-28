# AI-Assisted PCB Design Generator

Live Link: https://ai-assisted-pcb-design.streamlit.app/

Showcase prototype for a controlled AI-assisted PCB design workflow. A user
describes a small sensor board in natural language, and the app converts that
request into a structured PCB design handoff.

The architecture is intentionally fixed:

```text
USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus
```

Only the selected I2C sensor footprints change.

## Features

* Folder-based sensor definitions in `data/sensors/<sensor>/sensor.json`.
* Built-in sensor plugin validation panel in the Streamlit UI.
* Controlled natural-language extraction using sensor keywords from data files.
* Detailed output: parsed requirement, I/O table, BOM, pin map, netlist, power budget, schematic notes, layout notes, PCB visual, and build checks.
* Table-adjacent export buttons for BOM CSV, pin map CSV, and netlist CSV, plus full Markdown and JSON report exports.
* Unsupported requests are reported instead of being turned into imaginary hardware.

## Installation

Install Python 3.8 or later:

```bash
pip install -r requirements.txt
```

The Graphviz Python package is used for schematic/architecture diagrams. Some
systems also require the Graphviz `dot` executable to be installed separately.

## Usage

Run:

```bash
streamlit run app.py
```

Then enter a requirement such as:

```text
Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, temperature, humidity, and light sensing.
```

## Project Structure

```text
AI_PCB_Design/
  .gitignore
  app.py
  requirements.txt
  README.md
  src/
    __init__.py
    data_loader.py
    design_generator.py
    exports.py
    parser.py
    validation.py
    visuals.py
  data/
    board_template.json
    requirement_keywords.json
    sensors/
      README.md
      AHT20/sensor.json
      BH1750/sensor.json
      SGP30/sensor.json
      BMP280/sensor.json
    legacy/
      README.md
    web_sources/
      sensor_info.md
  prompts/
    extraction_prompt.txt
  tests/
    test_app.py
  files/
    generated demo/export artifacts
```

## Code Organization

* `app.py` contains the Streamlit UI and keeps the generated PCB visual first.
* `src/data_loader.py` contains JSON loading and sensor-library indexing helpers.
* `src/validation.py` contains sensor plugin schema checks.
* `src/parser.py` contains controlled requirement extraction from user input.
* `src/design_generator.py` contains BOM, pin map, netlist, power budget, checklist, and report data generation.
* `src/visuals.py` contains the PCB SVG, architecture diagram, and schematic diagram generation.
* `src/exports.py` contains CSV, Markdown, and JSON handoff export generation.

## Adding A Sensor

Create:

```text
data/sensors/NEW_SENSOR/
  sensor.json
```

Follow the schema in `data/sensors/README.md`.

For a normal 3.3 V I2C sensor, no `app.py` change is required. The app will
automatically use the folder data for parsing, selected component mapping, BOM,
pin map, power budget, netlist notes, layout notes, and PCB visual placement.

If `sensor.json` includes a `visual` block, the app uses that placement. If it
does not, the app auto-places the footprint in the PCB visual.

Use `data/sensors/TEMPLATE_SENSOR/sensor.json` as a copyable starting point. It
is marked `"enabled": false`, so it validates as a template but does not appear
as a supported sensor.

Optional pins such as `INT`, `EN`, `ADDR`, or `CS` are allowed in the `pins`
object. Standard I2C pins are handled automatically; non-standard nets are also
shown in the generated netlist for designer review.

## Tests

Run:

```bash
python -m unittest
```

## Notes

This is a showcase prototype, not a production PCB design tool. It does not
perform real PCB autorouting, KiCad generation, Gerber generation, electrical
simulation, or certification checks.
