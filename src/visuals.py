"""PCB visual and schematic diagram generation."""

from typing import Any, Dict, List, Tuple

import graphviz


def generate_block_diagram(selected_components: List[str], sensor_library: Dict[str, Dict[str, Any]]) -> graphviz.Digraph:
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
        sensor = sensor_library[comp]
        dot.node(comp, f"{comp}\n{sensor['functions']}\n{sensor['i2c_address']}", fillcolor="#DCEFE3")
        dot.edge("BUS", comp, label="3.3 V I2C", color="#2E6FDC")
    return dot


def generate_schematic_diagram(selected_components: List[str], sensor_library: Dict[str, Dict[str, Any]]) -> graphviz.Digraph:
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
        sensor = sensor_library[comp]
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


def get_sensor_visual_positions(
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Return explicit or auto-generated PCB visual positions for all sensors."""
    sensor_positions: Dict[str, Dict[str, Any]] = {}
    for component, sensor in sensor_library.items():
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

    legacy_visual = board_template.get("pcb_visual", {})
    for component, position in legacy_visual.get("sensor_positions", {}).items():
        sensor_positions.setdefault(component, dict(position))

    next_auto_y = 72
    for component in sensor_library:
        if component in sensor_positions:
            next_auto_y = max(next_auto_y, int(sensor_positions[component]["y"]) + 96)
    for component, sensor in sensor_library.items():
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


def calculate_pcb_visual_height(
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> int:
    """Return iframe height needed for the current PCB visual."""
    sensor_positions = get_sensor_visual_positions(sensor_library, board_template)
    board_height = max(560, max(int(position["y"]) + int(position["h"]) + 104 for position in sensor_positions.values()))
    return board_height + 80


def generate_pcb_visual_svg(
    selected_components: List[str],
    selected_sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
    all_sensor_refs: Dict[str, str],
) -> str:
    """Create one clear, user-friendly top-view PCB layout SVG."""
    sensor_positions = get_sensor_visual_positions(sensor_library, board_template)
    board_height = calculate_pcb_visual_height(sensor_library, board_template) - 80
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
        ref = selected_sensor_refs.get(component, all_sensor_refs.get(component, "--"))
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
