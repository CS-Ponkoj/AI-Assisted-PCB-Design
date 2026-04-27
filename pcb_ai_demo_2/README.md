# AI‑Assisted PCB Design Generator

This repository contains a showcase prototype of an AI‑powered PCB design
generator.  It demonstrates that a user can describe a simple
sensing board in natural language and the system can convert that
requirement into a structured design report.  The prototype keeps the
PCB architecture fixed while allowing a small number of controlled sensor
substitutions.

## Features

* **Fixed architecture:** USB‑C 5 V input → 3.3 V regulator → ESP32‑WROOM‑32
  microcontroller → shared I²C bus.
* **Controlled sensor selection:** Supports temperature, humidity, light,
  air quality and pressure sensing, mapped to AHT20, BH1750, SGP30 and
  BMP280 components.
* **Natural language input:** A simple parser extracts the requested
  connectivity and sensing functions from a free‑form description.
* **Structured output:** The app generates a JSON representation of the
  design, a block diagram, component list, netlist summary, schematic and
  PCB layout view, plus a short explanation.
* **Web‑sourced data:** Sensor datasheets and product guides are summarised
  in `data/web_sources/sensor_info.md` with citations to original sources.【764409156739556†L23-L29】【47281359819431†L209-L214】

## Installation

Install Python 3.8 or later and the required packages.  The prototype
depends on `streamlit` and `graphviz` which are not included in the
default environment:

```bash
pip install streamlit graphviz
```

Running the app requires Graphviz to be installed on the system so that
the Python `graphviz` package can generate diagrams.  On Debian/Ubuntu
systems you can install Graphviz with:

```bash
sudo apt‑get install graphviz
```

## Usage

Navigate into the `pcb_ai_demo` directory and run the app with Streamlit:

```bash
cd pcb_ai_demo
streamlit run app.py
```

Enter a natural language description of your desired sensing board and click
**Generate Design**.  The app will display the parsed requirements,
selected sensors, block diagram, component list, netlist, schematic, PCB
layout and a design explanation.

## Project structure

```
pcb_ai_demo/
├── app.py                # Streamlit app implementing the prototype
├── data/
│   ├── supported_sensors.json  # Mapping of sensing functions to components
│   ├── design_template.json    # Base architecture and component list
│   └── web_sources/
│       └── sensor_info.md      # Summaries of sensor datasheets with citations
├── prompts/
│   └── extraction_prompt.txt   # Prompt used for requirement extraction
└── README.md              # Project overview and usage instructions
```

## Licence

This prototype is provided for demonstration purposes only.  It is not a
production‑ready PCB design tool.