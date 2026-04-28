# AI-Assisted PCB Design Generator

Live Link: https://ai-assisted-pcb-design.streamlit.app/

Showcase prototype for a controlled PCB design workflow. A user
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
* Two requirement modes: Base assistant and optional local LLM assistant.
* Optional local LLM extraction through Ollama with `qwen2.5:3b`, no API key, and validated output.
* Design readiness review with Ready, Needs Review, or Blocked status.
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

Base mode runs inside the app. It does not use an external API, does not require
a private key, and does not add usage cost. It uses controlled synonyms and
validation rules.

LLM assistant mode is optional and uses a local Ollama server. Install Ollama,
then run:

```bash
ollama pull qwen2.5:3b
ollama serve
```

The app calls `http://localhost:11434` by default and falls back to Base mode if
Ollama is unavailable. Override the defaults with `OLLAMA_MODEL`, `OLLAMA_URL`,
or `OLLAMA_TIMEOUT_SECONDS` if needed.

For Streamlit deployment, Base mode is the safest default because it runs fully
inside the app. LLM assistant mode needs `OLLAMA_URL` to point to a reachable
Ollama server; a deployed Streamlit app cannot use your laptop's `localhost`
unless the app is also running on that same machine.

Do not commit the Ollama model files into this repository. The `qwen2.5:3b`
model is about 1.9 GB after download and is served by Ollama as a local model
runtime. A direct model link in the code is not enough by itself because the app
also needs an inference server or runtime capable of loading that model. For a
portable Streamlit Cloud demo, use Base mode. For LLM mode in deployment, run
Ollama on a reachable host and set `OLLAMA_URL` in the Streamlit environment.

## Usage

Run:

```bash
streamlit run app.py
```

Then enter a requirement such as:

```text
Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, temperature, humidity, and light sensing.
```

Choose `Base` or `LLM assistant`, then click `Generate PCB Handoff`. The app
keeps the last generated result on screen so expanding sections or using export
buttons does not regenerate the design.

## Project Structure

```text
AI_PCB_Design/
  .gitignore
  app.py
  requirements.txt
  README.md
  docs/
    AI-Assisted PCB Design Generator.docx
  src/
    __init__.py
    ai_assistant.py
    data_loader.py
    design_generator.py
    exports.py
    llm_assistant.py
    parser.py
    readiness.py
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
* `src/ai_assistant.py` contains the Base local requirement assistant and output validation.
* `src/llm_assistant.py` contains the optional Ollama / `qwen2.5:3b` requirement assistant.
* `src/design_generator.py` contains BOM, pin map, netlist, power budget, checklist, and report data generation.
* `src/readiness.py` contains the Ready / Needs Review / Blocked design review logic.
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
