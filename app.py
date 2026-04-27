"""AI-assisted PCB design handoff generator.

This Streamlit app turns a controlled natural-language sensor-board request
into a PCB-designer-ready handoff for a small 2-layer ESP32 prototype. The
architecture is intentionally fixed: USB-C power input, 3.3 V regulation,
ESP32-WROOM-32, and a shared I2C bus for supported sensors.
"""

from typing import Any, Dict, List
from urllib.parse import quote

import graphviz
import streamlit as st

from pcb_data import (
    analyze_sensor_definition,
    build_requirement_groups,
    build_sensor_keywords,
    build_sensor_reference_map,
    build_supported_sensors,
    collect_sensor_validation,
    load_json,
    load_sensor_definitions,
    validate_sensor_definition,
)
from pcb_exports import generate_export_package, rows_to_csv


def ordered_requirements(requirements: List[str]) -> List[str]:
    """Return requested sensing categories in sensor-folder order."""
    ordered: List[str] = []
    for sensor in SENSOR_LIBRARY.values():
        for category in sensor.get("categories", []):
            name = category["name"]
            if name in requirements and name not in ordered:
                ordered.append(name)
    for requirement in requirements:
        if requirement not in ordered:
            ordered.append(requirement)
    return ordered


SENSOR_LIBRARY: Dict[str, Dict[str, Any]] = load_sensor_definitions()
SUPPORTED_SENSORS: Dict[str, Dict[str, str]] = build_supported_sensors(SENSOR_LIBRARY)
SENSOR_KEYWORDS: Dict[str, str] = build_sensor_keywords(SENSOR_LIBRARY)
REQUIREMENT_GROUPS: List[List[str]] = build_requirement_groups(SENSOR_LIBRARY)
REQUIREMENT_CONFIG: Dict[str, Any] = load_json("data/requirement_keywords.json")
BOARD_TEMPLATE: Dict[str, Any] = load_json("data/board_template.json")
SENSOR_REFS: Dict[str, str] = build_sensor_reference_map(SENSOR_LIBRARY, BOARD_TEMPLATE)


def parse_requirements(user_input: str) -> Dict[str, Any]:
    """Parse free-form requirements into the controlled board architecture."""
    text = user_input.lower()

    connectivity: List[str] = []
    for label, keywords in REQUIREMENT_CONFIG["connectivity_keywords"].items():
        if any(keyword in text for keyword in keywords):
            connectivity.append(label)
    if not connectivity:
        connectivity = REQUIREMENT_CONFIG["default_connectivity"]

    requested_sensing: List[str] = []
    for phrase, key in SENSOR_KEYWORDS.items():
        if phrase in text and key not in requested_sensing:
            requested_sensing.append(key)

    for group in REQUIREMENT_GROUPS:
        if any(requirement in requested_sensing for requirement in group):
            for requirement in group:
                if requirement not in requested_sensing:
                    requested_sensing.append(requirement)
    requested_sensing = ordered_requirements(requested_sensing)

    selected_components: List[str] = []
    for requirement in requested_sensing:
        component = SUPPORTED_SENSORS.get(requirement, {}).get("component")
        if component and component not in selected_components:
            selected_components.append(component)

    unsupported = [kw for kw in REQUIREMENT_CONFIG["unsupported_keywords"] if kw in text]

    return {
        "power_input": "USB-C 5 V power only",
        "wireless": connectivity,
        "mcu": "ESP32-WROOM-32",
        "logic_voltage": "3.3 V",
        "communication_bus": "I2C",
        "requested_sensing": requested_sensing,
        "selected_components": selected_components,
        "unsupported_requirements": unsupported,
    }


def assign_sensor_refs(selected_components: List[str]) -> Dict[str, str]:
    """Assign stable reference designators to populated sensor ICs."""
    return {component: SENSOR_REFS[component] for component in selected_components}


def generate_design_package(user_input: str) -> Dict[str, Any]:
    """Generate the complete PCB handoff data structure."""
    parsed = parse_requirements(user_input)
    selected_components = parsed["selected_components"]
    sensor_refs = assign_sensor_refs(selected_components)

    bom = generate_bom(selected_components, sensor_refs)
    netlist = generate_netlist_table(selected_components, sensor_refs)
    pin_map = generate_pin_map(selected_components, sensor_refs)
    power_budget = generate_power_budget(selected_components)

    return {
        "parsed": parsed,
        "summary": generate_project_summary(user_input, parsed),
        "assumptions": generate_assumptions(parsed),
        "io_table": generate_io_table(parsed, selected_components),
        "bom": bom,
        "pin_map": pin_map,
        "netlist": netlist,
        "power_budget": power_budget,
        "layout_guidance": generate_layout_guidance(selected_components, sensor_refs),
        "fabrication_checklist": generate_fabrication_checklist(),
        "bringup_checklist": generate_bringup_checklist(selected_components, sensor_refs),
        "schematic_summary": generate_schematic_summary(selected_components, sensor_refs),
        "sensor_refs": sensor_refs,
    }


def generate_project_summary(user_input: str, parsed: Dict[str, Any]) -> List[Dict[str, str]]:
    """Summarize the generated board in designer-facing terms."""
    sensors = parsed["selected_components"]
    rows = [{"Item": "Original requirement", "Decision": user_input}]
    rows.extend(dict(row) for row in BOARD_TEMPLATE["project_summary_static"])
    rows.append({"Item": "Sensors populated", "Decision": ", ".join(sensors) if sensors else "No supported sensors selected"})
    return rows


def generate_assumptions(parsed: Dict[str, Any]) -> List[Dict[str, str]]:
    """State the fixed engineering assumptions for the handoff."""
    unsupported = parsed["unsupported_requirements"]
    unsupported_text = ", ".join(unsupported) if unsupported else "None"
    rows = [dict(row) for row in BOARD_TEMPLATE["assumptions_base"]]
    rows.append({"Assumption": "Unsupported requests", "Value": unsupported_text})
    return rows


def generate_io_table(parsed: Dict[str, Any], selected_components: List[str]) -> List[Dict[str, str]]:
    """Define electrical and functional inputs/outputs."""
    rows = [dict(row) for row in BOARD_TEMPLATE["io_table_base"]]
    for row in rows:
        if row["Interface"] == "Wireless":
            row["Electrical"] = row["Electrical"].format(wireless=", ".join(parsed["wireless"]))

    for component in selected_components:
        sensor = SENSOR_LIBRARY[component]
        rows.append(
            {
                "Interface": f"{component} sensor output",
                "Direction": "Input to MCU",
                "Pins/Nets": f"{component} at I2C address {sensor['i2c_address']} on I2C_SDA/I2C_SCL",
                "Electrical": sensor["supply"],
                "Designer note": sensor["functions"],
            }
        )
    return rows


def generate_bom(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    """Generate a full BOM for the selected board variant."""
    rows = [dict(row) for row in BOARD_TEMPLATE["bom_base"]]

    sensor_decoupling_index = 6
    for component in selected_components:
        sensor = SENSOR_LIBRARY[component]
        ref = sensor_refs[component]
        rows.append(
            bom_row(
                ref,
                component,
                f"{component} {sensor['functions']} sensor",
                "1",
                sensor["footprint"],
                "Selected sensor",
                f"I2C address {sensor['i2c_address']}; {sensor['placement']}",
            )
        )
        rows.append(
            bom_row(
                f"C{sensor_decoupling_index}",
                f"{component} local decoupling",
                "0.1 uF, 16 V, X7R",
                "1",
                "0603",
                "Sensor decoupling",
                f"Place within 2-5 mm of {ref} supply and ground pins.",
            )
        )
        sensor_decoupling_index += 1
    return rows


def bom_row(ref: str, item: str, value: str, qty: str, footprint: str, role: str, notes: str) -> Dict[str, str]:
    return {
        "Ref": ref,
        "Item": item,
        "Value / Part": value,
        "Qty": qty,
        "Footprint / Package": footprint,
        "Role": role,
        "Notes": notes,
    }


def generate_pin_map(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    """Generate a pin-level implementation map."""
    rows = [dict(row) for row in BOARD_TEMPLATE["pin_map_base"]]

    for component in selected_components:
        ref = sensor_refs[component]
        sensor = SENSOR_LIBRARY[component]
        for pin, net in sensor["pins"].items():
            rows.append(pin_row(ref, pin, net, f"{component} {sensor['functions']} sensor pin", "Sensor"))
    return rows


def pin_row(ref: str, pin: str, net: str, connection: str, pin_type: str) -> Dict[str, str]:
    return {
        "Ref": ref,
        "Pin": pin,
        "Net": net,
        "Connection / Function": connection,
        "Type": pin_type,
    }


def generate_netlist_table(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    """Generate a PCB netlist table with routing intent."""
    rows = [dict(row) for row in BOARD_TEMPLATE["netlist_base"]]
    common_sensor_nets = {"3V3", "GND", "I2C_SDA", "I2C_SCL"}

    for component in selected_components:
        ref = sensor_refs[component]
        sensor = SENSOR_LIBRARY[component]
        rows.append(
            net_row(
                f"{component}_LOCAL_DECOUPLING",
                f"{ref} supply pin; local 0.1 uF capacitor; GND",
                "Decoupling",
                "3.3 V",
                f"Place capacitor next to {ref}; {sensor['routing']}",
            )
        )
        for pin, net in sensor["pins"].items():
            if net not in common_sensor_nets:
                rows.append(
                    net_row(
                        net,
                        f"{ref}.{pin}",
                        "Sensor extra pin",
                        sensor["supply"],
                        f"Optional {component} pin from sensor definition; verify firmware/strap behavior before release.",
                    )
                )
    return rows


def net_row(name: str, pins: str, signal_type: str, voltage: str, routing: str) -> Dict[str, str]:
    return {
        "Net": name,
        "Connected pins": pins,
        "Type": signal_type,
        "Voltage": voltage,
        "Routing / PCB note": routing,
    }


def generate_power_budget(selected_components: List[str]) -> List[Dict[str, str]]:
    """Estimate current draw and regulator margin."""
    power_template = BOARD_TEMPLATE["power_budget_base"]
    rows = [dict(row) for row in power_template["rows"]]

    total_ma = float(power_template["base_load_ma"])
    for component in selected_components:
        sensor = SENSOR_LIBRARY[component]
        total_ma += float(sensor["current_ma"])
        rows.append(
            {
                "Block": component,
                "Estimated current": f"{sensor['current_ma']:.1f} mA",
                "Rail": "3V3",
                "Notes": f"{sensor['functions']} sensor at I2C address {sensor['i2c_address']}.",
            }
        )

    regulator_min_ma = float(power_template["regulator_min_ma"])
    margin = regulator_min_ma - total_ma
    rows.append(
        {
            "Block": "3.3 V regulator requirement",
            "Estimated current": f"{total_ma:.1f} mA estimated peak load",
            "Rail": "3V3",
            "Notes": f"Use >={regulator_min_ma:.0f} mA LDO; estimated margin is {margin:.1f} mA before thermal derating.",
        }
    )
    rows.append(
        {
            "Block": "Thermal check",
            "Estimated current": "Review during layout",
            "Rail": "VBUS_5V to 3V3",
            "Notes": "LDO heat is roughly (5 V - 3.3 V) * load current; provide copper area near U1.",
        }
    )
    return rows


def generate_layout_guidance(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    """Generate 2-layer PCB placement and routing instructions."""
    rows = [dict(row) for row in BOARD_TEMPLATE["layout_guidance_base"]]

    for component in selected_components:
        rows.append({"Area": f"{sensor_refs[component]} {component}", "Instruction": SENSOR_LIBRARY[component]["placement"]})
    return rows


def generate_fabrication_checklist() -> List[Dict[str, str]]:
    return [dict(row) for row in BOARD_TEMPLATE["fabrication_checklist"]]


def generate_bringup_checklist(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    rows = [dict(row) for row in BOARD_TEMPLATE["bringup_checklist_base"]]
    for component in selected_components:
        sensor = SENSOR_LIBRARY[component]
        rows.append(
            {
                "Step": f"Verify {sensor_refs[component]} {component}",
                "Expected result": f"I2C address {sensor['i2c_address']} responds and reports plausible {sensor['functions'].lower()} data.",
            }
        )
    return rows


def generate_schematic_summary(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[str]:
    """Create a compact schematic implementation summary."""
    lines = list(BOARD_TEMPLATE["schematic_summary_base"])
    for component in selected_components:
        ref = sensor_refs[component]
        sensor = SENSOR_LIBRARY[component]
        lines.append(
            f"{ref} {component} connects to 3V3, GND, I2C_SDA, and I2C_SCL at address {sensor['i2c_address']}; add local 0.1 uF decoupling."
        )
    return lines


def generate_block_diagram(selected_components: List[str]) -> graphviz.Digraph:
    """Create a Graphviz block diagram of the fixed architecture."""
    dot = graphviz.Digraph(name="architecture", format="png")
    dot.attr(rankdir="TB", concentrate="false", fontsize="10", bgcolor="transparent")
    dot.attr("node", shape="rectangle", style="rounded,filled", color="#173A31", fontname="Arial")
    dot.attr("edge", fontname="Arial", fontsize="9", penwidth="2")
    dot.node("USB", "USB-C\n5 V Input", fillcolor="#F6C85F")
    dot.node("REG", "3.3 V LDO\n>=600 mA", fillcolor="#F5E6A8")
    dot.node("MCU", "ESP32-WROOM-32\nWiFi/Bluetooth", fillcolor="#DDE8E4")
    dot.node("BUS", "I2C Bus\nSDA GPIO21 / SCL GPIO22", fillcolor="#D4E9FF")
    dot.edge("USB", "REG", label="VBUS_5V", color="#E67E22")
    dot.edge("REG", "MCU", label="3V3", color="#C79A19")
    dot.edge("MCU", "BUS", label="SDA/SCL + pullups", color="#2E6FDC")
    for comp in selected_components:
        sensor = SENSOR_LIBRARY[comp]
        dot.node(comp, f"{comp}\n{sensor['functions']}\n{sensor['i2c_address']}", fillcolor="#DCEFE3")
        dot.edge("BUS", comp, label="3.3 V I2C", color="#2E6FDC")
    return dot


def generate_schematic_diagram(selected_components: List[str]) -> graphviz.Digraph:
    """Create a schematic-style connectivity diagram."""
    dot = graphviz.Digraph(name="schematic", format="png")
    dot.attr(rankdir="LR", fontsize="9")

    col_vbus = "#E67E22"
    col_3v3 = "#C79A19"
    col_gnd = "#7A8C82"
    col_i2c = "#2E6FDC"
    dot.attr(bgcolor="transparent")
    dot.attr("node", fontname="Arial")
    dot.attr("edge", fontname="Arial", fontsize="9", penwidth="2")

    dot.node("USB", "J1 USB-C|<VBUS> VBUS|<GND> GND|<CC1> CC1|<CC2> CC2", shape="record", style="filled", fillcolor="#F6C85F", color="#173A31")
    dot.node("REG", "U1 3.3 V LDO|<VIN> VIN|<VOUT> VOUT|<EN> EN|<GND> GND", shape="record", style="filled", fillcolor="#F5E6A8", color="#173A31")
    dot.node("MCU", "U2 ESP32-WROOM-32|<3V3> 3V3|<EN> EN|<SDA> GPIO21 SDA|<SCL> GPIO22 SCL|<LED> GPIO2 LED|<GND> GND", shape="record", style="filled", fillcolor="#DDE8E4", color="#173A31")
    dot.node("CC", "R1/R2\n5.1 kOhm\nCC pull-downs", shape="box", style="filled", fillcolor="#E8F5EA", color="#173A31")
    dot.node("PULL", "R3/R4\n4.7 kOhm\nI2C pullups", shape="box", style="filled", fillcolor="#D4E9FF", color="#173A31")
    dot.node("LED", "D1 + R5\nStatus LED", shape="box", style="filled", fillcolor="#D4E9FF", color="#173A31")
    dot.node("RST", "SW1 + R6\nReset/EN", shape="box", style="filled", fillcolor="#D4E9FF", color="#173A31")

    for comp in selected_components:
        sensor = SENSOR_LIBRARY[comp]
        dot.node(comp, f"{comp}|<VCC> 3V3|<GND> GND|<SDA> SDA|<SCL> SCL", shape="record", style="filled", fillcolor="#DCEFE3", color="#173A31")
        dot.edge("REG:VOUT", f"{comp}:VCC", color=col_3v3)
        dot.edge("MCU:GND", f"{comp}:GND", color=col_gnd)
        dot.edge("MCU:SDA", f"{comp}:SDA", label=sensor["i2c_address"], color=col_i2c)
        dot.edge("MCU:SCL", f"{comp}:SCL", color=col_i2c)

    dot.edge("USB:VBUS", "REG:VIN", label="VBUS_5V", color=col_vbus)
    dot.edge("USB:VBUS", "REG:EN", color=col_vbus, style="dashed")
    dot.edge("USB:GND", "REG:GND", color=col_gnd)
    dot.edge("USB:GND", "MCU:GND", color=col_gnd)
    dot.edge("USB:CC1", "CC", label="CC1", color=col_gnd)
    dot.edge("USB:CC2", "CC", label="CC2", color=col_gnd)
    dot.edge("CC", "MCU:GND", label="to GND", color=col_gnd)
    dot.edge("REG:VOUT", "MCU:3V3", label="3V3", color=col_3v3)
    dot.edge("REG:VOUT", "PULL", label="3V3", color=col_3v3, style="dashed")
    dot.edge("MCU:SDA", "PULL", label="SDA", color=col_i2c)
    dot.edge("MCU:SCL", "PULL", label="SCL", color=col_i2c)
    dot.edge("MCU:LED", "LED", label="GPIO2", color=col_i2c)
    dot.edge("RST", "MCU:EN", label="EN", color=col_i2c)
    return dot


def generate_pcb_layout(selected_components: List[str]) -> graphviz.Digraph:
    """Create a symbolic PCB layout guidance diagram."""
    dot = graphviz.Digraph(name="layout", format="png")
    dot.attr(rankdir="LR", fontsize="8")

    with dot.subgraph(name="cluster_board") as c:
        c.attr(label="2-layer PCB placement zones", style="rounded,filled", fillcolor="#F7F7F7", color="#888888")
        c.node("USB", "J1\nUSB-C\nboard edge", shape="box", style="filled", fillcolor="#F6C85F")
        c.node("PWR", "U1 + C1-C3\npower zone", shape="box", style="filled", fillcolor="#F6C85F")
        c.node("ESP", "U2 ESP32\nantenna at edge\nkeepout", shape="box", style="filled", fillcolor="#9DD9D2")
        c.node("DBG", "TP1-TP5\nbring-up pads", shape="box", style="filled", fillcolor="#D8D8D8")
        c.node("UI", "D1 + SW1\nuser access", shape="box", style="filled", fillcolor="#D8D8D8")
        for comp in selected_components:
            c.node(comp, f"{comp}\nexposed sensor zone", shape="box", style="filled", fillcolor="#B8D8F0")

    dot.edge("USB", "PWR", label="VBUS_5V / GND", color="#EF6C00")
    dot.edge("PWR", "ESP", label="3V3 / GND", color="#C47F00")
    dot.edge("ESP", "DBG", label="SDA/SCL test", color="#3366AA")
    dot.edge("ESP", "UI", label="GPIO2 / EN", color="#3366AA")
    for comp in selected_components:
        dot.edge("ESP", comp, label="I2C + 3V3 + GND", color="#3366AA")
    return dot


def svg_text(x: int, y: int, text: str, size: int = 13, weight: str = "500", fill: str = "#102018") -> str:
    """Create an SVG text element."""
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{text}</text>'
    )


def svg_component(
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    subtitle: str,
    fill: str,
    stroke: str = "#18382C",
) -> str:
    """Draw a labeled PCB component block."""
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
      {svg_text(x + 10, y + 22, title, 14, "700")}
      {svg_text(x + 10, y + 42, subtitle, 11, "500", "#24483A")}
    </g>
    """


def svg_trace(points: List[Tuple[int, int]], color: str, width: int = 4, dashed: bool = False) -> str:
    """Draw a routed PCB trace through a list of points."""
    path = f"M {points[0][0]} {points[0][1]} " + " ".join(f"L {x} {y}" for x, y in points[1:])
    dash = ' stroke-dasharray="10 7"' if dashed else ""
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{dash}/>'


def get_sensor_visual_positions() -> Dict[str, Dict[str, Any]]:
    """Return explicit or auto-generated PCB visual positions for all sensors."""
    sensor_positions: Dict[str, Dict[str, Any]] = {}
    for component, sensor in SENSOR_LIBRARY.items():
        visual = sensor.get("visual", {})
        if visual:
            sensor_positions[component] = {
                "x": visual.get("x", 620),
                "y": visual.get("y", 72),
                "w": visual.get("w", 138),
                "h": visual.get("h", 72),
                "purpose": visual.get("purpose", sensor["functions"]),
                "placement": visual.get("placement", "sensor zone"),
            }

    legacy_visual = BOARD_TEMPLATE.get("pcb_visual", {})
    for component, position in legacy_visual.get("sensor_positions", {}).items():
        sensor_positions.setdefault(component, dict(position))

    next_auto_y = 72
    for component in SENSOR_LIBRARY:
        if component in sensor_positions:
            next_auto_y = max(next_auto_y, int(sensor_positions[component]["y"]) + 96)
    for component, sensor in SENSOR_LIBRARY.items():
        if component not in sensor_positions:
            sensor_positions[component] = {
                "x": 620,
                "y": next_auto_y,
                "w": 138,
                "h": 72,
                "purpose": sensor["functions"],
                "placement": "auto-placed option",
            }
            next_auto_y += 96
    return sensor_positions


def calculate_pcb_visual_height() -> int:
    """Return iframe height needed for the current PCB visual."""
    sensor_positions = get_sensor_visual_positions()
    board_height = max(560, max(int(position["y"]) + int(position["h"]) + 104 for position in sensor_positions.values()))
    return board_height + 80


def generate_pcb_visual_svg(selected_components: List[str], sensor_refs: Dict[str, str]) -> str:
    """Create one clear, user-friendly top-view PCB layout SVG."""
    sensor_positions = get_sensor_visual_positions()
    board_height = calculate_pcb_visual_height() - 80
    board_inner_height = board_height - 36
    footer_y = board_height - 12
    bottom_mount_y = board_height - 70

    mounting_holes = "".join(
        f'<circle cx="{x}" cy="{y}" r="18" fill="#DDE7E0" stroke="#0E4A35" stroke-width="4"/>'
        f'<circle cx="{x}" cy="{y}" r="9" fill="#0B2B21"/>'
        for x, y in [(62, 60), (798, 60), (62, bottom_mount_y), (798, bottom_mount_y)]
    )
    test_points = "".join(
        f'<circle cx="{x}" cy="480" r="10" fill="#FFE083" stroke="#8A6A00" stroke-width="2"/>'
        f'{svg_text(x - 15, 506, label, 11, "800", "#193A2C")}'
        for x, label in [(265, "5V"), (310, "3V3"), (360, "GND"), (412, "SDA"), (462, "SCL")]
    )

    sensor_shapes: List[str] = []
    sensor_traces: List[str] = []
    for component, position in sensor_positions.items():
        x = int(position["x"])
        y = int(position["y"])
        w = int(position["w"])
        h = int(position["h"])
        purpose = position["purpose"]
        placement = position["placement"]
        selected = component in selected_components
        ref = sensor_refs.get(component, SENSOR_REFS.get(component, "--"))
        fill = "#DCEFE3" if selected else "#E2E4E1"
        stroke = "#0C6B46" if selected else "#8F9A94"
        text_fill = "#113629" if selected else "#68736D"
        status_fill = "#157A4F" if selected else "#9CA5A0"
        status_text = "INSTALL" if selected else "DNP OPTION"
        placement_text = placement if selected else "leave empty for this request"
        trace_opacity = "1" if selected else "0.22"
        sensor_traces.append(
            f'<g opacity="{trace_opacity}">'
            + svg_trace([(525, 230), (585, 230), (585, y + 24), (x, y + 24)], "#2E6FDC", 3)
            + svg_trace([(525, 250), (596, 250), (596, y + 42), (x, y + 42)], "#2E6FDC", 3)
            + svg_trace([(338, 214), (580, 214), (580, y + 12), (x, y + 12)], "#C79A19", 4)
            + "</g>"
        )
        sensor_shapes.append(
            f"""
            <g>
              <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
              <rect x="{x + 10}" y="{y + 10}" width="34" height="32" rx="4" fill="#F7FBF8" stroke="{stroke}" stroke-width="1.5"/>
              <circle cx="{x + 27}" cy="{y + 26}" r="8" fill="none" stroke="{stroke}" stroke-width="2"/>
              <rect x="{x + 68}" y="{y + 10}" width="60" height="18" rx="9" fill="{status_fill}"/>
              {svg_text(x + 74, y + 23, status_text, 8, "800", "white")}
              {svg_text(x + 52, y + 42, f"{ref} {component}", 14, "800", text_fill)}
              {svg_text(x + 52, y + 60, purpose, 11, "600", text_fill)}
              {svg_text(x + 10, y + h - 8, placement_text, 10, "600", text_fill)}
            </g>
            """
        )

    return f"""
    <div style="width:100%; overflow-x:auto;">
      <svg viewBox="0 0 860 {board_height}" width="100%" height="{board_height + 60}" role="img" aria-label="Clear top-view PCB layout visual">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#2A6B4F" stroke-width="0.7" opacity="0.14"/>
          </pattern>
          <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="#0A1D15" flood-opacity="0.22"/>
          </filter>
        </defs>

        <rect x="12" y="12" width="836" height="{board_height - 24}" rx="30" fill="#166342" filter="url(#shadow)"/>
        <rect x="28" y="28" width="804" height="{board_inner_height}" rx="20" fill="url(#grid)" stroke="#D8F1DE" stroke-width="2" opacity="0.96"/>
        <rect x="492" y="78" width="96" height="92" rx="8" fill="none" stroke="#FFE26F" stroke-width="3" stroke-dasharray="8 6"/>
        {svg_text(498, 68, "ESP32 antenna keepout", 12, "800", "#FFF3A5")}
        {mounting_holes}

        <rect x="30" y="236" width="78" height="94" rx="6" fill="#D8DEE2" stroke="#56636A" stroke-width="3"/>
        <rect x="10" y="258" width="42" height="50" rx="5" fill="#F4F6F7" stroke="#56636A" stroke-width="2"/>
        {svg_text(38, 224, "J1 USB-C", 15, "800", "#E8FFF1")}

        {svg_component(158, 238, 112, 76, "U1 LDO", "5 V to 3.3 V", "#F9C76B")}
        {svg_component(288, 236, 86, 42, "C1-C3", "power caps", "#F5E6A8")}
        {svg_component(288, 142, 92, 50, "R3/R4", "I2C pullups", "#F5E6A8")}

        <rect x="405" y="176" width="140" height="170" rx="7" fill="#DDE8E4" stroke="#173A31" stroke-width="2"/>
        <rect x="497" y="176" width="48" height="170" fill="#F2D36B" stroke="#173A31" stroke-width="2"/>
        <path d="M505 200 h30 M505 224 h30 M505 248 h30 M505 272 h30 M505 296 h30" stroke="#8D7414" stroke-width="3"/>
        {svg_text(420, 206, "U2 ESP32", 17, "800")}
        {svg_text(420, 230, "WROOM-32", 13, "700")}
        {svg_text(420, 255, "WiFi / Bluetooth", 11, "600")}

        {svg_component(110, 390, 95, 54, "D1/R5", "status LED", "#D4E9FF")}
        {svg_component(218, 390, 95, 54, "SW1/R6", "reset", "#D4E9FF")}
        {test_points}

        {svg_trace([(90, 284), (158, 284)], "#E67E22", 8)}
        {svg_trace([(270, 276), (338, 276), (338, 214), (405, 214)], "#C79A19", 7)}
        {svg_trace([(475, 282), (475, 480), (100, 480)], "#7A8C82", 4, dashed=True)}
        {svg_trace([(270, 258), (288, 258)], "#C79A19", 4)}
        {svg_trace([(380, 168), (405, 230)], "#2E6FDC", 4)}
        {svg_trace([(380, 182), (405, 250)], "#2E6FDC", 4)}
        {svg_trace([(475, 346), (475, 390), (260, 390)], "#2E6FDC", 4)}
        {"".join(sensor_traces)}
        {"".join(sensor_shapes)}

        <g>
          <rect x="394" y="390" width="178" height="100" rx="8" fill="#E8F5EA" opacity="0.96" stroke="#2C644A"/>
          {svg_text(412, 414, "Legend", 13, "800")}
          <line x1="412" y1="432" x2="452" y2="432" stroke="#E67E22" stroke-width="7"/>
          {svg_text(462, 437, "USB 5 V", 11, "700")}
          <line x1="412" y1="454" x2="452" y2="454" stroke="#C79A19" stroke-width="6"/>
          {svg_text(462, 459, "3.3 V", 11, "700")}
          <line x1="412" y1="476" x2="452" y2="476" stroke="#2E6FDC" stroke-width="4"/>
          {svg_text(462, 481, "I2C / GPIO", 11, "700")}
        </g>

        {svg_text(44, footer_y, "Clear PCB layout view: INSTALL means assemble this part. DNP OPTION means optional footprint exists, but leave it empty for this request.", 13, "800", "#E8FFF1")}
      </svg>
    </div>
    """


def generate_component_list(selected_components: List[str]) -> List[Dict[str, str]]:
    """Compatibility wrapper for the detailed BOM."""
    return generate_bom(selected_components, assign_sensor_refs(selected_components))


def generate_netlist(selected_components: List[str]) -> str:
    """Compatibility wrapper returning a readable netlist summary."""
    rows = generate_netlist_table(selected_components, assign_sensor_refs(selected_components))
    return "\n".join(f"{row['Net']}: {row['Connected pins']} [{row['Voltage']}]" for row in rows)


def render_table(title: str, rows: List[Dict[str, str]]) -> None:
    st.subheader(title)
    st.table(rows)


def export_variant_slug(package: Dict[str, Any]) -> str:
    """Return a stable file-name slug for the selected board variant."""
    selected = package["parsed"]["selected_components"]
    return "_".join(component.lower() for component in selected) if selected else "base_board"


def render_exportable_table(
    title: str,
    rows: List[Dict[str, str]],
    button_label: str,
    file_name: str,
) -> None:
    """Render a table with its CSV export action beside the table heading."""
    title_col, export_col = st.columns([4, 1])
    with title_col:
        st.subheader(title)
    with export_col:
        st.download_button(
            button_label,
            data=rows_to_csv(rows),
            file_name=file_name,
            mime="text/csv",
        )
    st.table(rows)


def render_checklist(title: str, rows: List[Dict[str, str]]) -> None:
    st.subheader(title)
    for row in rows:
        values = list(row.values())
        label = values[0]
        detail = values[1] if len(values) > 1 else ""
        st.markdown(f"- **{label}:** {detail}")


def render_html_iframe(html: str, height: int) -> None:
    """Render self-contained HTML without using deprecated components.html."""
    document = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden;}</style>"
        "</head><body>"
        f"{html}"
        "</body></html>"
    )
    st.iframe(f"data:text/html;charset=utf-8,{quote(document)}", height=height)


def render_pcb_legend() -> None:
    """Show a readable legend next to the PCB visual."""
    st.table(
        [
            {"Marking": "INSTALL", "Meaning": "Assemble this sensor for the current user request."},
            {"Marking": "DNP OPTION", "Meaning": "Optional footprint exists, but leave it empty for this request."},
            {"Marking": "Orange trace", "Meaning": "USB 5 V input path."},
            {"Marking": "Amber trace", "Meaning": "Regulated 3.3 V rail."},
            {"Marking": "Blue trace", "Meaning": "I2C / GPIO signals."},
            {"Marking": "Dashed gray", "Meaning": "Ground return / ground reference path."},
            {"Marking": "Yellow box", "Meaning": "ESP32 antenna keepout: no copper or components."},
        ]
    )


def render_export_buttons(package: Dict[str, Any]) -> None:
    """Render full-report download buttons for the generated PCB handoff package."""
    exports = generate_export_package(package)
    variant = export_variant_slug(package)

    report_col_1, report_col_2 = st.columns(2)
    with report_col_1:
        st.download_button(
            "Full Report Markdown",
            data=exports["report_markdown"],
            file_name=f"pcb_handoff_{variant}_report.md",
            mime="text/markdown",
        )
    with report_col_2:
        st.download_button(
            "Full Report JSON",
            data=exports["report_json"],
            file_name=f"pcb_handoff_{variant}_report.json",
            mime="application/json",
        )


def main() -> None:
    """Streamlit entry point."""
    st.set_page_config(page_title="PCB Designer Handoff Generator", layout="wide")
    st.title("PCB Designer Handoff Generator")
    st.markdown(
        "Generate a build-oriented 2-layer ESP32 sensor-board handoff from a controlled natural-language requirement."
    )
    sensor_options = ", ".join(requirement.replace("_", " ") for requirement in SUPPORTED_SENSORS)
    unsupported_options = ", ".join(REQUIREMENT_CONFIG["unsupported_keywords"][:7])
    st.markdown("### Supported Scope Before You Enter a Requirement")
    st.info(
        f"**Sensors available:** {sensor_options}.\n\n"
        "**Fixed board architecture:** USB-C 5 V power -> 3.3 V regulator -> "
        "ESP32-WROOM-32 -> shared I2C bus.\n\n"
        "**What can change:** the requested sensing functions and selected sensor footprints.\n\n"
        f"**Out of scope examples:** {unsupported_options}, arbitrary chips, auto-routing, "
        "and manufacturing-ready Gerber generation."
    )
    with st.expander("Sensor Plugin Validation", expanded=False):
        validation_rows = collect_sensor_validation()
        validation_statuses = {row["Status"] for row in validation_rows}
        active_statuses = validation_statuses - {"Disabled"}
        if "Error" in active_statuses:
            st.error("One or more sensor plugin files have schema errors.")
        elif "Warning" in active_statuses:
            st.warning("Sensor plugin files loaded with warnings. Review before relying on the output.")
        else:
            st.success("All enabled sensor plugin files passed validation.")
        st.table(validation_rows)

    default_input = (
        "Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, "
        "temperature, humidity, and light sensing."
    )
    user_input = st.text_area("Board requirements", value=default_input, height=110)
    generate = st.button("Refresh PCB Handoff", type="primary")

    if user_input.strip():
        package = generate_design_package(user_input.strip())
        parsed = package["parsed"]
        selected_components = parsed["selected_components"]
        variant = export_variant_slug(package)

        st.header("1. Requirement and Controlled Decisions")
        render_table("Project Summary", package["summary"])
        render_table("Design Assumptions", package["assumptions"])
        if parsed["unsupported_requirements"]:
            st.warning(
                "Unsupported requests were detected and intentionally excluded: "
                + ", ".join(parsed["unsupported_requirements"])
            )
        st.subheader("Parsed Requirement JSON")
        st.json(parsed)

        st.header("2. Electrical Inputs and Outputs")
        render_table("I/O Definition", package["io_table"])

        st.header("3. Source-of-Truth Engineering Tables")
        render_exportable_table(
            "Bill of Materials",
            package["bom"],
            "Export BOM CSV",
            f"pcb_handoff_{variant}_bom.csv",
        )
        render_exportable_table(
            "Pin Map",
            package["pin_map"],
            "Export Pin Map CSV",
            f"pcb_handoff_{variant}_pin_map.csv",
        )
        render_exportable_table(
            "PCB Netlist",
            package["netlist"],
            "Export Netlist CSV",
            f"pcb_handoff_{variant}_netlist.csv",
        )
        render_table("Power Budget", package["power_budget"])

        st.header("4. Schematic and PCB Implementation Notes")
        st.subheader("Schematic Summary")
        for line in package["schematic_summary"]:
            st.markdown(f"- {line}")
        render_table("2-Layer PCB Layout Instructions", package["layout_guidance"])

        st.header("5. Visual Diagrams")
        st.caption("Diagrams are implementation aids. The tables above are the source of truth for PCB capture.")
        st.subheader("PCB Layout Visual")
        st.info(
            "**How to read this board:** sensors marked **INSTALL** are part of the current design. "
            "Sensors marked **DNP OPTION** are optional footprints on the shared prototype PCB; "
            "DNP means 'do not populate,' so those parts are left empty during assembly for this user request."
        )
        visual_col, legend_col = st.columns([3, 1])
        with visual_col:
            render_html_iframe(
                generate_pcb_visual_svg(selected_components, package["sensor_refs"]),
                height=calculate_pcb_visual_height(),
            )
        with legend_col:
            st.subheader("PCB Legend")
            render_pcb_legend()
        st.subheader("System Architecture")
        st.graphviz_chart(generate_block_diagram(selected_components))
        st.subheader("Schematic Connectivity")
        st.graphviz_chart(generate_schematic_diagram(selected_components))

        st.header("6. Build Checks")
        render_checklist("Fabrication and Assembly Checklist", package["fabrication_checklist"])
        render_checklist("Bring-Up Checklist", package["bringup_checklist"])

        st.header("7. Export Package")
        st.caption("Download the full generated handoff report. Table-specific CSV exports are beside their tables above.")
        render_export_buttons(package)


if __name__ == "__main__":
    main()
