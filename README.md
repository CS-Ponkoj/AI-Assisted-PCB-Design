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
* Two requirement modes: Base assistant and optional LLM assistant.
* Optional LLM extraction through an Ollama-compatible server with `qwen2.5:3b`, validated output, and Base fallback.
* Design readiness review with Ready, Needs Review, or Blocked status.
* Detailed output: parsed requirement, I/O table, BOM, pin map, netlist, power budget, schematic notes, layout notes, PCB visual, and build checks.
* Table-adjacent export buttons for BOM CSV, pin map CSV, and netlist CSV, plus full Markdown and JSON report exports.
* Unsupported requests are reported instead of being turned into imaginary hardware.

## Quick Start

From the project root, install Python 3.8 or later, then install the project
dependencies:

```bash
pip install -r requirements.txt
```

The Graphviz Python package is used for schematic/architecture diagrams. Some
systems also require the Graphviz `dot` executable to be installed separately.

Run the app:

```bash
streamlit run app.py
```

Base mode works immediately after this step. It runs inside the app with no
model server, no API key, and no usage cost.

## Enable LLM Mode Locally

The app has two requirement modes:

* `Base`: controlled local parsing and validation, always available.
* `LLM assistant`: uses an Ollama-compatible model server with `qwen2.5:3b`, then validates the model output before generating the PCB handoff.

To use both modes locally, install Ollama if it is not already installed on your
device:

```text
https://ollama.com/download
```

If Ollama is already installed, you can skip the install step.

Pull the lightweight model:

```bash
ollama pull qwen2.5:3b
```

Confirm the model is available:

```bash
ollama list
```

Make sure Ollama is running. On many desktop installs, opening the Ollama app is
enough. If needed, run this in a separate terminal:

```bash
ollama serve
```

If `ollama serve` says the address is already in use, Ollama is already running.

Then start the Streamlit app:

```bash
streamlit run app.py
```

By default, LLM mode uses:

```text
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

If Ollama is not available, LLM mode falls back to Base mode so the prototype can
still generate a PCB handoff.

Do not commit the Ollama model files into this repository. The `qwen2.5:3b`
model is about 1.9 GB after download and is served by Ollama as a local model
runtime. The app needs a running model server, not just a model file or direct
download link.

## Usage

Enter a requirement such as:

```text
Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, temperature, humidity, and light sensing.
```

Choose `Base` or `LLM assistant`, then click `Generate PCB Handoff`. Base is the
default active mode. When `LLM assistant` is selected, the app shows the
configured provider endpoint, model, connection status, and whether the model is
available. The app keeps the last generated result on screen so expanding
sections or using export buttons does not regenerate the design.

## LLM Server Configuration

To use a remote Ollama-compatible server instead of local Ollama:

```bash
OLLAMA_URL=https://your-reachable-ollama-server.example
OLLAMA_MODEL=qwen2.5:3b
streamlit run app.py
```

On Windows PowerShell, use:

```powershell
$env:OLLAMA_URL="https://your-reachable-ollama-server.example"
$env:OLLAMA_MODEL="qwen2.5:3b"
streamlit run app.py
```

If the server needs auth, also set `OLLAMA_API_KEY` or `OLLAMA_AUTH_HEADER`.
If no model server is available, LLM mode falls back to Base mode, so the app
still generates a PCB handoff.

Optional environment variables:

```text
OLLAMA_URL=https://your-reachable-ollama-server.example
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_API_KEY=optional-bearer-token
OLLAMA_AUTH_HEADER=optional-custom-header
```

`OLLAMA_AUTH_HEADER` can be either a full header value for `Authorization` or a
`Header-Name: value` pair.

For Streamlit deployment, Base mode is the safest default because it runs fully
inside the app. LLM assistant mode needs `OLLAMA_URL` to point to a reachable
Ollama-compatible server; a deployed Streamlit app cannot use your laptop's
`localhost` unless the app is also running on that same machine.

## Project Structure

```text
AI_PCB_Design/
  .gitignore
  app.py
  requirements.txt
  README.md
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
