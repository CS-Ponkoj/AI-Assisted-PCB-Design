# AI-Assisted PCB Design Generator

Live Link: https://ai-assisted-pcb-design.streamlit.app/

Showcase prototype for a controlled PCB design workflow. A user
describes a small sensor board in natural language, and the app converts that
request into a structured PCB design handoff.

Current upgrade note: see `VERSION_4.md` for the interactive PCB visual upgrade details.

The architecture is intentionally fixed:

```text
USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus
```

Only the selected I2C sensor footprints change.

## Features

* Folder-based sensor definitions in `data/sensors/<sensor>/sensor.json`.
* Built-in sensor plugin validation panel in the Streamlit UI.
* Controlled natural-language extraction using sensor keywords from data files.
* Three requirement modes: Base assistant, Ollama LLM, and Gemini API.
* Optional LLM extraction through either an Ollama-compatible server or Gemini API, with validated output and Base fallback.
* Design readiness review with Ready, Needs Review, or Blocked status.
* Detailed output: parsed requirement, I/O table, BOM, pin map, netlist, power budget, schematic notes, layout notes, PCB visual, and build checks.
* Interactive PCB visual with component/trace inspection, populated-only view, board dimensions, connector side, antenna keepout, and mounting-hole coordinates.
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

## Convenient Full Setup For Ollama LLM Mode

`requirements.txt` only installs Python packages. It cannot install Ollama or
pull an LLM model by itself.

For convenience, this repo includes setup scripts that install the Python
requirements and pull the default local Ollama model. Install Ollama first from:

```text
https://ollama.com/download
```

If Ollama is already installed, skip that install step.

On Windows PowerShell:

```powershell
.\scripts\setup_llm.ps1
```

On macOS/Linux:

```bash
bash scripts/setup_llm.sh
```

The scripts pull:

```text
qwen2.5:3b
```

After setup, run:

```bash
streamlit run app.py
```

## Enable Ollama LLM Mode Locally

The app has three requirement modes:

* `Base`: controlled local parsing and validation, always available.
* `Ollama LLM`: uses an Ollama-compatible model server with `qwen2.5:3b`, then validates the model output before generating the PCB handoff.
* `Gemini API`: uses Google's Gemini API, then validates the model output before generating the PCB handoff.

To use Ollama LLM mode locally, install Ollama if it is not already installed on
your device:

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

If Ollama is not available, Ollama LLM mode falls back to Base mode so the
prototype can still generate a PCB handoff.

Do not commit the Ollama model files into this repository. The `qwen2.5:3b`
model is about 1.9 GB after download and is served by Ollama as a local model
runtime. The app needs a running model server, not just a model file or direct
download link.

## Usage

Enter a requirement such as:

```text
Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, temperature, humidity, and light sensing.
```

Choose `Base`, `Ollama LLM`, or `Gemini API`, then click `Generate PCB Handoff`.
Base is the default active mode. When an LLM mode is selected, the app shows the
configured provider status and fallback behavior. The app keeps the last
generated result on screen so expanding sections or using export buttons does
not regenerate the design.

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
inside the app. Ollama LLM mode needs `OLLAMA_URL` to point to a reachable
Ollama-compatible server; a deployed Streamlit app cannot use your laptop's
`localhost` unless the app is also running on that same machine.

## Gemini API Configuration

Gemini API mode does not require Ollama or a local model download. It does
require a Gemini API key.

For local development, create:

```text
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY = "your-key-here"
```

The `.streamlit/` folder is ignored by Git and must not be committed. You can
also set `GEMINI_API_KEY` as an environment variable for local testing.

For Streamlit Cloud, add the same secret in the app's secrets settings:

```toml
GEMINI_API_KEY = "your-key-here"
```

Optional Gemini environment variables:

```text
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODEL_FALLBACKS=gemini-2.5-flash,gemini-2.0-flash-lite
GEMINI_TIMEOUT_SECONDS=60
GEMINI_MAX_INPUT_CHARS=1200
GEMINI_MAX_OUTPUT_TOKENS=350
```

If the Gemini key is missing, the API returns an error, or the model returns
invalid JSON, Gemini mode first tries the configured fallback Gemini models and
then falls back to Base mode. The API key is never displayed in the app UI.

## Project Structure

```text
AI_PCB_Design/
  .gitignore
  app.py
  requirements.txt
  README.md
  scripts/
    setup_llm.ps1
    setup_llm.sh
  src/
    __init__.py
    base_assistant.py
    data_loader.py
    design_generator.py
    exports.py
    gemini_assistant.py
    ollama_assistant.py
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
    web_sources/
      sensor_info.md
  tests/
    test_app.py
```

## Local-Only Files

These folders are intentionally ignored by Git:

* `.streamlit/`: local Streamlit secrets such as `GEMINI_API_KEY`.
* `docs/`: personal demo notes or talking-point drafts.
* `prompts/`: local prompt experiments.
* `files/`: generated CSV, JSON, Markdown, or PDF handoff artifacts.
* `data/legacy/`: archived data from earlier prototype versions.

## Code Organization

* `app.py` contains the Streamlit UI and keeps the generated PCB visual first.
* `src/data_loader.py` contains JSON loading and sensor-library indexing helpers.
* `src/validation.py` contains sensor plugin schema checks.
* `src/parser.py` contains controlled requirement extraction from user input.
* `src/base_assistant.py` contains the Base local requirement assistant and output validation.
* `src/ollama_assistant.py` contains the optional Ollama / `qwen2.5:3b` requirement assistant.
* `src/gemini_assistant.py` contains the optional Gemini API requirement assistant.
* `src/design_generator.py` contains BOM, pin map, netlist, power budget, checklist, and report data generation.
* `src/readiness.py` contains the Ready / Needs Review / Blocked design review logic.
* `src/visuals.py` contains the interactive PCB SVG, architecture diagram, and schematic diagram generation.
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
