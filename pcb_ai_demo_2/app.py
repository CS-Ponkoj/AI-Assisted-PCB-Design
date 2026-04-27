"""AI-Assisted PCB Design Generator Prototype

This Streamlit app is a demonstration of a controlled AI‑assisted hardware design
pipeline.  It accepts a natural language description of a small sensing board
and produces a structured design report.  The architecture is fixed – a
USB‑C input feeding a 3.3 V regulator and an ESP32‑WROOM‑32 microcontroller
with a shared I²C bus.  Only the sensor selection changes based on the
requested sensing functions.  Unsupported requests are reported back to the
user rather than generating imaginary components.

The app generates:

  • The original user requirement
  • A parsed JSON structure identifying power, connectivity and requested sensors
  • A block diagram of the fixed architecture with selected sensors
  • A component list highlighting base parts and selected sensors
  • A netlist‑style summary of how everything is wired together
  • A simple schematic view and PCB layout view using Graphviz
  • A short design explanation

To run the app install the dependencies (streamlit and graphviz) and run
```
streamlit run app.py
```

"""

import json
import os
from typing import Dict, List

import graphviz
import streamlit as st


def load_supported_sensors(path: str = "data/supported_sensors.json") -> Dict[str, Dict[str, str]]:
    """Load supported sensor definitions from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


SUPPORTED_SENSORS = load_supported_sensors()


def parse_requirements(user_input: str) -> Dict[str, object]:
    """Parse the user's natural language description into a structured design.

    For this prototype we use a simple keyword search to identify requested
    sensing functions and connectivity options.  Unsupported requests are
    collected in a list rather than being silently ignored.
    """
    text = user_input.lower()
    # connectivity
    connectivity: List[str] = []
    if "wifi" in text or "wi-fi" in text:
        connectivity.append("WiFi")
    if "bluetooth" in text:
        connectivity.append("Bluetooth")
    # always include both connectivity options if not explicitly requested
    if not connectivity:
        connectivity = ["WiFi", "Bluetooth"]
    # requested sensing
    requested_sensing: List[str] = []
    sensor_keywords = {
        "temperature": "temperature",
        "humidity": "humidity",
        "light": "light",
        "air quality": "air_quality",
        "air-quality": "air_quality",
        "voc": "air_quality",
        "pressure": "pressure",
        "barometric": "pressure",
    }
    for phrase, key in sensor_keywords.items():
        if phrase in text and key not in requested_sensing:
            requested_sensing.append(key)
    # map to selected components – combine temp/humidity into one AHT20
    selected_components: List[str] = []
    if "temperature" in requested_sensing or "humidity" in requested_sensing:
        selected_components.append("AHT20")
    if "light" in requested_sensing:
        selected_components.append("BH1750")
    if "air_quality" in requested_sensing:
        selected_components.append("SGP30")
    if "pressure" in requested_sensing:
        selected_components.append("BMP280")
    # unsupported requirements
    unsupported_keywords = ["gps", "camera", "microphone", "sound", "video", "accelerometer", "gyroscope"]
    unsupported: List[str] = [kw for kw in unsupported_keywords if kw in text]
    return {
        "power_input": "USB-C 5V",
        "wireless": connectivity,
        "mcu": "ESP32-WROOM-32",
        "logic_voltage": "3.3V",
        "communication_bus": "I2C",
        "requested_sensing": requested_sensing,
        "selected_components": selected_components,
        "unsupported_requirements": unsupported,
    }


def generate_block_diagram(selected_components: List[str]) -> graphviz.Digraph:
    """Create a Graphviz block diagram of the system architecture.

    This diagram shows the fixed power and microcontroller chain with a
    shared I²C bus feeding optional sensors. It uses a neutral colour
    palette for improved readability.
    """
    dot = graphviz.Digraph(name="architecture", format="png")
    dot.attr(rankdir="TB", concentrate="false", fontsize="10")
    # base nodes
    dot.node("USB", "USB‑C\n5 V Input", shape="rectangle", style="rounded,filled", fillcolor="#EDEDED")
    dot.node("REG", "3.3 V Regulator", shape="rectangle", style="rounded,filled", fillcolor="#EDEDED")
    dot.node("MCU", "ESP32‑WROOM‑32", shape="rectangle", style="rounded,filled", fillcolor="#EDEDED")
    dot.node("BUS", "I²C Bus", shape="rectangle", style="rounded,filled", fillcolor="#EDEDED")
    # edges
    dot.edge("USB", "REG", label="5 V")
    dot.edge("REG", "MCU", label="3.3 V")
    dot.edge("MCU", "BUS", label="SDA/SCL")
    # sensor nodes
    for comp in selected_components:
        if comp == "AHT20":
            label = "AHT20\nTemp+Hum"
        elif comp == "BH1750":
            label = "BH1750\nLight"
        elif comp == "SGP30":
            label = "SGP30\nAir Quality"
        elif comp == "BMP280":
            label = "BMP280\nPressure"
        else:
            label = comp
        dot.node(comp, label, shape="rectangle", style="rounded,filled", fillcolor="#DDEBF7")
        dot.edge("BUS", comp, label="I²C")
    return dot


def generate_schematic_diagram(selected_components: List[str]) -> graphviz.Digraph:
    """
    Create a detailed schematic‑style diagram.

    This diagram models a small MCU‑based sensing board more like a real
    electrical schematic. It includes the USB‑C power input, a 3.3 V
    regulator, pull‑up resistors on the I²C bus, a status LED and reset
    button, and the microcontroller with labelled pins.  Selected
    sensors are drawn with their own VCC, GND, SDA and SCL pins.  Power
    nets (VBUS, 3.3 V, GND) and bus lines (SDA, SCL) are colour‑coded
    for clarity.  While this is still an abstract representation, it
    conveys the information someone would need to implement the
    connections on a real PCB.
    """
    dot = graphviz.Digraph(name="schematic", format="png")
    dot.attr(rankdir="LR", fontsize="9")

    # Colour palette for nets
    col_vbus = "#EF6C00"  # orange for 5 V
    col_3v3 = "#E69138"  # warm orange for 3.3 V
    col_gnd = "#666666"  # grey for ground
    col_i2c = "#6C8CD5"  # blue for I²C bus

    # USB‑C connector with power and CC pins
    usb_label = "USB‑C\nConnector|<VBUS> VBUS|<GND> GND|<CC1> CC1|<CC2> CC2"
    dot.node("USB", usb_label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

    # 3.3 V regulator with VIN, VOUT and GND
    reg_label = "3.3 V Regulator|<VIN> VIN|<VOUT> VOUT|<GND> GND"
    dot.node("REG", reg_label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

    # Pull‑up resistor pack for SDA/SCL to 3.3 V
    pullup_label = "I²C Pull‑ups|<SDA> SDA →3V3|<SCL> SCL →3V3"
    dot.node("PULL", pullup_label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

    # Status LED
    led_label = "Status LED|<AN> Anode|<CA> Cathode"
    dot.node("LED", led_label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

    # Reset button
    rst_label = "Reset Button|<SW> SW|<GND> GND"
    dot.node("RST", rst_label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

    # ESP32 microcontroller with labelled pins
    mcu_label = "ESP32‑WROOM‑32|<3V3> 3V3|<EN> EN|<SDA> GPIO21 (SDA)|<SCL> GPIO22 (SCL)|<GND> GND|<RST> RST"
    dot.node("MCU", mcu_label, shape="record", style="filled", fillcolor="#1F2338", fontcolor="white")

    # Sensors – only include selected sensors
    for comp in selected_components:
        if comp == "AHT20":
            label = "AHT20 (Temp+Hum)|<VCC> VCC|<GND> GND|<SDA> SDA|<SCL> SCL"
        elif comp == "BH1750":
            label = "BH1750 (Light)|<VCC> VCC|<GND> GND|<SDA> SDA|<SCL> SCL"
        elif comp == "SGP30":
            label = "SGP30 (Air Quality)|<VCC> VCC|<GND> GND|<SDA> SDA|<SCL> SCL"
        elif comp == "BMP280":
            label = "BMP280 (Pressure)|<VCC> VCC|<GND> GND|<SDA> SDA|<SCL> SCL"
        else:
            label = f"{comp}|<VCC> VCC|<GND> GND|<SDA> SDA|<SCL> SCL"
        dot.node(comp, label, shape="record", style="filled", fillcolor="#2A2E45", fontcolor="white")

        # Power connections to sensors
        dot.edge("REG:VOUT", f"{comp}:VCC", color=col_3v3)
        dot.edge("MCU:GND", f"{comp}:GND", color=col_gnd)
        # Bus connections
        dot.edge("MCU:SDA", f"{comp}:SDA", color=col_i2c)
        dot.edge("MCU:SCL", f"{comp}:SCL", color=col_i2c)

    # Base interconnects
    # USB → Regulator
    dot.edge("USB:VBUS", "REG:VIN", label="5 V", color=col_vbus)
    dot.edge("USB:GND", "MCU:GND", color=col_gnd)
    dot.edge("USB:GND", "REG:GND", color=col_gnd)

    # Regulator output → MCU and pull‑ups
    dot.edge("REG:VOUT", "MCU:3V3", color=col_3v3)
    dot.edge("REG:VOUT", "PULL:SDA", color=col_3v3, style="dashed")
    dot.edge("REG:VOUT", "PULL:SCL", color=col_3v3, style="dashed")

    # Pull‑up resistors connect bus lines to 3V3
    dot.edge("MCU:SDA", "PULL:SDA", color=col_i2c)
    dot.edge("MCU:SCL", "PULL:SCL", color=col_i2c)

    # Status LED connected to 3V3 and MCU
    dot.edge("REG:VOUT", "LED:AN", color=col_3v3)
    dot.edge("LED:CA", "MCU:GND", color=col_gnd)

    # Reset button to EN pin
    dot.edge("RST:SW", "MCU:EN", color=col_i2c, style="dotted")
    dot.edge("RST:GND", "MCU:GND", color=col_gnd, style="dotted")

    return dot


def generate_component_list(selected_components: List[str]) -> List[Dict[str, str]]:
    """Construct a table of base and sensor components for display."""
    base_components = [
        "USB-C Power Connector",
        "3.3V Voltage Regulator",
        "ESP32-WROOM-32 MCU",
        "Status LED",
        "Reset Button",
        "CC1 5.1kΩ resistor",
        "CC2 5.1kΩ resistor",
        "Pull-up resistors (4.7kΩ)",
    ]
    table = []
    for comp in base_components:
        table.append({"Component": comp, "Type": "Base"})
    for comp in selected_components:
        description = SUPPORTED_SENSORS.get(comp.lower(), {}).get("function", "Sensor")
        table.append({"Component": comp, "Type": "Sensor"})
    return table


def generate_netlist(selected_components: List[str]) -> str:
    """Generate a netlist‑style wiring summary as a multiline string."""
    lines: List[str] = []
    lines.extend([
        "USB_C.VBUS → REGULATOR.VIN",
        "USB_C.GND → SYSTEM.GND",
        "USB_C.CC1 → 5.1kΩ → SYSTEM.GND",
        "USB_C.CC2 → 5.1kΩ → SYSTEM.GND",
        "",
        # regulator outputs
        "REGULATOR.VOUT → 3V3_RAIL",
        "REGULATOR.GND → SYSTEM.GND",
        "",
        # MCU power
        "3V3_RAIL → ESP32.3V3",
        "SYSTEM.GND → ESP32.GND",
        "",
        # I²C bus connections
        "ESP32.GPIO21 (SDA) → I2C_SDA",
        "ESP32.GPIO22 (SCL) → I2C_SCL",
        "",
        # Pull‑up resistors on I²C lines
        "I2C_SDA → 4.7kΩ → 3V3_RAIL",
        "I2C_SCL → 4.7kΩ → 3V3_RAIL",
        "",
        # Status LED wiring
        "3V3_RAIL → STATUS_LED.ANODE",
        "STATUS_LED.CATHODE → ESP32.GPIO02 (or other IO) → SYSTEM.GND",
        "",
        # Reset button wiring
        "ESP32.EN → RESET_BUTTON.SW → SYSTEM.GND",
        "",
    ])
    for comp in selected_components:
        if comp == "AHT20":
            lines.extend([
                "3V3_RAIL → AHT20.VCC",
                "SYSTEM.GND → AHT20.GND",
                "I2C_SDA → AHT20.SDA",
                "I2C_SCL → AHT20.SCL",
                "",
            ])
        elif comp == "BH1750":
            lines.extend([
                "3V3_RAIL → BH1750.VCC",
                "SYSTEM.GND → BH1750.GND",
                "I2C_SDA → BH1750.SDA",
                "I2C_SCL → BH1750.SCL",
                "",
            ])
        elif comp == "SGP30":
            lines.extend([
                "3V3_RAIL → SGP30.VCC",
                "SYSTEM.GND → SGP30.GND",
                "I2C_SDA → SGP30.SDA",
                "I2C_SCL → SGP30.SCL",
                "",
            ])
        elif comp == "BMP280":
            lines.extend([
                "3V3_RAIL → BMP280.VCC",
                "SYSTEM.GND → BMP280.GND",
                "I2C_SDA → BMP280.SDA",
                "I2C_SCL → BMP280.SCL",
                "",
            ])
    return "\n".join(lines)


def generate_pcb_layout(selected_components: List[str]) -> graphviz.Digraph:
    """
    Create a more detailed PCB layout diagram using Graphviz.

    The board is represented as a rounded rectangle cluster containing
    footprints for the USB‑C connector, regulator, MCU, pull‑up resistors,
    status LED, reset button and sensor modules.  Populated sensors are
    highlighted while unselected sensors are shown as unpopulated
    placeholders.  Coloured traces indicate power nets and bus lines.
    This view is still symbolic but it provides the spatial context and
    signal flow a PCB designer would expect when translating the design
    to CAD software.
    """
    dot = graphviz.Digraph(name="layout", format="png")
    dot.attr(rankdir="TB", fontsize="8")

    # Colour palette matching the schematic
    col_vbus = "#EF6C00"
    col_3v3 = "#E69138"
    col_gnd = "#666666"
    col_i2c = "#6C8CD5"

    # board outline as a cluster
    with dot.subgraph(name="cluster_board") as c:
        c.attr(label="", style="rounded,filled", fillcolor="#1F2338", color="#888888")
        # Place footprints
        c.node("USB", "USB‑C", shape="box", style="filled", fillcolor="#FFDEA6", fontcolor="black")
        c.node("REG", "Regulator", shape="box", style="filled", fillcolor="#FFDEA6", fontcolor="black")
        c.node("MCU", "ESP32", shape="box", style="filled", fillcolor="#FFB657", fontcolor="black")
        c.node("PULL", "I²C Pull‑ups", shape="box", style="filled", fillcolor="#FFDEA6", fontcolor="black")
        c.node("LED", "Status LED", shape="box", style="filled", fillcolor="#FFDEA6", fontcolor="black")
        c.node("RST", "Reset Button", shape="box", style="filled", fillcolor="#FFDEA6", fontcolor="black")
        # Sensor footprints; indicate population status
        sensors = ["AHT20", "BH1750", "SGP30", "BMP280"]
        for comp in sensors:
            if comp in selected_components:
                fill = "#6FA8DC"  # blue for populated
                label = comp
            else:
                fill = "#AAAAAA"  # grey for not populated
                label = f"{comp}\n(not populated)"
            c.node(comp, label, shape="box", style="filled", fillcolor=fill, fontcolor="black")

    # Draw power traces
    dot.edge("USB", "REG", label="VBUS", color=col_vbus)
    dot.edge("REG", "MCU", label="3.3 V", color=col_3v3)
    dot.edge("REG", "PULL", label="3.3 V", color=col_3v3, style="dashed")
    dot.edge("MCU", "LED", label="3.3 V", color=col_3v3, style="dashed")

    # Ground connections (dashed grey traces for clarity)
    dot.edge("USB", "MCU", label="GND", color=col_gnd, style="dotted")
    dot.edge("USB", "REG", label="GND", color=col_gnd, style="dotted")
    dot.edge("MCU", "PULL", label="GND", color=col_gnd, style="dotted")
    dot.edge("MCU", "LED", label="GND", color=col_gnd, style="dotted")
    dot.edge("MCU", "RST", label="GND", color=col_gnd, style="dotted")

    # I²C bus traces from MCU to sensors and pull‑ups
    for comp in sensors:
        if comp in selected_components:
            dot.edge("MCU", comp, label="SDA/SCL", color=col_i2c)
    # Bus to pull‑ups
    dot.edge("MCU", "PULL", label="SDA/SCL", color=col_i2c, style="dashed")

    # Reset button trace to MCU
    dot.edge("RST", "MCU", label="EN", color=col_i2c, style="dotted")

    return dot


def generate_explanation(parsed: Dict[str, object]) -> str:
    """Generate a brief human‑readable explanation of the design."""
    lines: List[str] = []
    lines.append(
        "The generated board uses USB‑C as a 5 V input and converts it to a 3.3 V logic rail for the ESP32 and sensors."
    )
    lines.append(
        "The ESP32‑WROOM‑32 provides WiFi and Bluetooth connectivity for wireless communication."
    )
    if parsed["selected_components"]:
        lines.append(
            "The selected sensors communicate over a shared I²C bus, which allows the board to support different sensor combinations without changing the main architecture."
        )
        descriptions = {
            "AHT20": "temperature and humidity sensing",
            "BH1750": "ambient light sensing",
            "SGP30": "air quality sensing",
            "BMP280": "pressure sensing",
        }
        selected_desc = [f"{comp} for {descriptions.get(comp, 'unknown')}" for comp in parsed["selected_components"]]
        lines.append("For this request, the system selected " + ", ".join(selected_desc) + ".")
    else:
        lines.append("No supported sensing functions were requested.")
    return " ".join(lines)


def main() -> None:
    """Streamlit entry point for the prototype."""
    st.set_page_config(page_title="AI‑Assisted PCB Design Generator Prototype")
    st.title("AI‑Assisted PCB Design Generator Prototype")
    st.markdown(
        "Enter a natural language description of your desired sensing board.  This prototype uses a fixed architecture (USB‑C → 3.3 V regulator → ESP32‑WROOM‑32 → I²C bus) and supports a controlled set of sensors: temperature, humidity, light, air quality and pressure."
    )
    user_input = st.text_area("Board requirements", value="Make me a USB‑C powered indoor monitoring board with WiFi, Bluetooth, temperature, humidity, and light sensing.")
    generate = st.button("Generate Design")
    if generate and user_input.strip():
        parsed = parse_requirements(user_input)
        st.subheader("Section A: Original User Requirement")
        st.write(user_input)
        st.subheader("Section B: Parsed Requirement")
        st.json(parsed)
        st.subheader("Section C: Generated System Architecture")
        arch_dot = generate_block_diagram(parsed["selected_components"])
        st.graphviz_chart(arch_dot)
        st.subheader("Section D: Generated Component List")
        table_data = generate_component_list(parsed["selected_components"])
        st.table(table_data)
        st.subheader("Section E: Generated Netlist‑Style Connection Summary")
        st.text(generate_netlist(parsed["selected_components"]))
        st.subheader("Section F: Generated Schematic Output")
        # Use the new schematic diagram for a more detailed view
        schematic_dot = generate_schematic_diagram(parsed["selected_components"])
        st.graphviz_chart(schematic_dot)
        st.subheader("Section G: Generated PCB Layout Output")
        pcb_dot = generate_pcb_layout(parsed["selected_components"])
        st.graphviz_chart(pcb_dot)
        st.subheader("Section H: Design Explanation")
        st.write(generate_explanation(parsed))


if __name__ == "__main__":
    main()