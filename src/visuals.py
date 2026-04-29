"""PCB visual and schematic diagram generation."""

import html
import json
from typing import Any, Dict, List, Optional, Tuple

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


def svg_text(x: int, y: int, text: str, size: int = 13, weight: str = "500", fill: str = "#102018") -> str:
    """Create an SVG text element."""
    safe_text = html.escape(str(text))
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{safe_text}</text>'
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


def svg_trace(
    points: List[Tuple[int, int]],
    color: str,
    width: int = 4,
    dashed: bool = False,
    detail_id: str = "",
    title: str = "",
) -> str:
    """Draw a routed PCB trace through a list of points."""
    path = f"M {points[0][0]} {points[0][1]} " + " ".join(f"L {x} {y}" for x, y in points[1:])
    dash = ' stroke-dasharray="10 7"' if dashed else ""
    interaction = f' class="trace-hotspot" data-detail="{html.escape(detail_id)}"' if detail_id else ""
    title_node = f"<title>{html.escape(title)}</title>" if title else ""
    if title_node:
        return (
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash}{interaction}>{title_node}</path>'
        )
    return (
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round"{dash}{interaction}/>'
    )


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

    template_visual = board_template.get("pcb_visual", {})
    for component, position in template_visual.get("sensor_positions", {}).items():
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
    return board_height + 340


def row_matches_ref(row_ref: str, ref: str) -> bool:
    """Return whether a BOM or pin-map reference field contains a reference designator."""
    normalized_row_ref = row_ref.replace(" ", "")
    normalized_ref = ref.replace(" ", "")
    return normalized_ref in normalized_row_ref


def compact_row(row: Dict[str, str], fields: List[str]) -> str:
    """Format a table row into one readable inspector line."""
    return " | ".join(f"{field}: {row[field]}" for field in fields if row.get(field))


def rows_for_ref(rows: List[Dict[str, str]], ref: str) -> List[Dict[str, str]]:
    """Return table rows related to a reference designator."""
    return [row for row in rows if row_matches_ref(row.get("Ref", ""), ref)]


def rows_for_nets(rows: List[Dict[str, str]], nets: List[str]) -> List[Dict[str, str]]:
    """Return netlist rows related to any net in the provided list."""
    net_set = set(nets)
    return [row for row in rows if row.get("Net") in net_set]


def build_visual_detail_data(
    selected_components: List[str],
    selected_sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    all_sensor_refs: Dict[str, str],
    bom_rows: Optional[List[Dict[str, str]]] = None,
    pin_map_rows: Optional[List[Dict[str, str]]] = None,
    netlist_rows: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Build click-target data for the interactive PCB inspector."""
    bom_rows = bom_rows or []
    pin_map_rows = pin_map_rows or []
    netlist_rows = netlist_rows or []
    details: Dict[str, Dict[str, Any]] = {}

    def add_detail(
        detail_id: str,
        title: str,
        status: str,
        placement: str,
        refs: Optional[List[str]] = None,
        nets: Optional[List[str]] = None,
        bom: Optional[List[str]] = None,
        pins: Optional[List[str]] = None,
    ) -> None:
        refs = refs or []
        nets = nets or []
        bom_lines = list(bom or [])
        pin_lines = list(pins or [])

        for ref in refs:
            bom_lines.extend(
                compact_row(row, ["Ref", "Item", "Value / Part", "Footprint / Package", "Notes"])
                for row in rows_for_ref(bom_rows, ref)
            )
            pin_lines.extend(
                compact_row(row, ["Ref", "Pin", "Net", "Connection / Function"])
                for row in rows_for_ref(pin_map_rows, ref)
            )

        net_lines = [
            compact_row(row, ["Net", "Connected pins", "Type", "Voltage", "Routing / PCB note"])
            for row in rows_for_nets(netlist_rows, nets)
        ]
        details[detail_id] = {
            "title": title,
            "status": status,
            "placement": placement,
            "bom": bom_lines or ["No BOM row is required for this visual-only item."],
            "pins": pin_lines or ["No pin-map row is required for this visual-only item."],
            "nets": net_lines or ["No dedicated netlist row is required for this visual-only item."],
        }

    add_detail(
        "BOARD",
        "Board Outline and Mechanical Constraints",
        "2-layer prototype",
        "Target compact 45 mm x 35 mm board. USB-C connector exits the left edge. H1-H4 mounting holes are approximately H1=(3,3) mm, H2=(42,3) mm, H3=(3,32) mm, H4=(42,32) mm.",
        refs=["H1-H4"],
    )
    add_detail(
        "J1",
        "J1 USB-C Power Input",
        "Assemble",
        "Place on the left board edge with connector overhang and shell pads per the selected connector drawing.",
        refs=["J1"],
        nets=["VBUS_5V", "GND", "USB_CC1", "USB_CC2"],
    )
    add_detail(
        "U1",
        "U1 3.3 V Regulator Zone",
        "Assemble",
        "Place U1, C1, C2, and C3 close to J1. Keep the VBUS path short and wider than signal traces.",
        refs=["U1", "C1", "C2", "C3"],
        nets=["VBUS_5V", "3V3", "GND"],
    )
    add_detail(
        "U2",
        "U2 ESP32-WROOM-32",
        "Assemble",
        "Place the ESP32 so the antenna faces a board edge. Keep the antenna region clear on all layers.",
        refs=["U2 ESP32", "C4", "C5"],
        nets=["3V3", "GND", "I2C_SDA", "I2C_SCL", "STATUS_LED", "ESP32_EN"],
    )
    add_detail(
        "ANTENNA",
        "ESP32 Antenna Keepout",
        "No copper or components",
        "Keep copper, traces, vias, components, enclosure metal, and mounting hardware out of this keepout.",
        nets=["GND"],
    )
    add_detail(
        "I2C_PULLUPS",
        "R3/R4 I2C Pullups",
        "Assemble",
        "Place near the ESP32 or I2C bus center. These bias SDA and SCL to 3.3 V.",
        refs=["R3", "R4"],
        nets=["I2C_SDA", "I2C_SCL", "3V3"],
    )
    add_detail(
        "STATUS_LED",
        "D1/R5 Status LED",
        "Assemble",
        "Place where visible on the top side. Confirm GPIO2 boot behavior with firmware.",
        refs=["D1", "R5"],
        nets=["STATUS_LED", "3V3"],
    )
    add_detail(
        "RESET",
        "SW1/R6 Reset Interface",
        "Assemble",
        "Place near an accessible board or enclosure edge. SW1 pulls ESP32_EN low for reset.",
        refs=["SW1", "R6"],
        nets=["ESP32_EN", "GND", "3V3"],
    )
    add_detail(
        "TEST_POINTS",
        "TP1-TP5 Bring-Up Test Points",
        "Assemble",
        "Place along an accessible board edge for first-power checks and I2C probing.",
        refs=["TP1", "TP2", "TP3", "TP4", "TP5"],
        nets=["VBUS_5V", "3V3", "GND", "I2C_SDA", "I2C_SCL"],
    )
    add_detail(
        "MOUNTING",
        "H1-H4 Mounting Holes",
        "Mechanical",
        "Approximate coordinates on the 45 mm x 35 mm target board: H1=(3,3) mm, H2=(42,3) mm, H3=(3,32) mm, H4=(42,32) mm. Keep hardware away from antenna keepout.",
        refs=["H1-H4"],
    )
    add_detail(
        "TRACE_5V",
        "VBUS_5V Trace",
        "5 V input path",
        "Route from J1 to U1 as a short, wider power trace.",
        nets=["VBUS_5V"],
    )
    add_detail(
        "TRACE_3V3",
        "3V3 Rail",
        "Regulated power rail",
        "Use a short rail or local pour to feed the ESP32, pullups, sensors, LED path, and test point.",
        nets=["3V3"],
    )
    add_detail(
        "TRACE_GND",
        "GND Return",
        "Ground reference",
        "Use a continuous bottom-layer ground pour with stitching vias around USB, regulator, ESP32, and sensors.",
        nets=["GND"],
    )
    add_detail(
        "TRACE_I2C",
        "I2C_SDA / I2C_SCL Bus",
        "3.3 V digital bus",
        "Route SDA and SCL as short traces with limited stubs, away from the ESP32 antenna and regulator noise.",
        nets=["I2C_SDA", "I2C_SCL"],
    )

    for component, sensor in sensor_library.items():
        selected = component in selected_components
        ref = selected_sensor_refs.get(component, all_sensor_refs.get(component, "--"))
        pin_lines = [
            f"{ref}.{pin} -> {net}"
            for pin, net in sensor.get("pins", {}).items()
        ]
        sensor_nets = sorted(set(sensor.get("pins", {}).values()))
        add_detail(
            component,
            f"{ref} {component}",
            "INSTALL" if selected else "DNP OPTION",
            sensor["placement"] if selected else f"Optional footprint only for this request. If not populated, leave {ref} and its local decoupling unassembled.",
            refs=[ref] if selected else [],
            nets=sensor_nets if selected else [],
            bom=None if selected else [f"{ref} {component}: footprint option is visible but not assembled for this variant."],
            pins=None if selected else pin_lines,
        )
        if selected:
            details[component]["pins"] = pin_lines
            details[component]["nets"].append(f"I2C address: {sensor['i2c_address']}; routing: {sensor['routing']}")
    return details


def generate_pcb_visual_svg(
    selected_components: List[str],
    selected_sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
    all_sensor_refs: Dict[str, str],
    bom_rows: Optional[List[Dict[str, str]]] = None,
    pin_map_rows: Optional[List[Dict[str, str]]] = None,
    netlist_rows: Optional[List[Dict[str, str]]] = None,
    show_all_footprints: bool = True,
) -> str:
    """Create one clear, user-friendly top-view PCB layout SVG."""
    sensor_positions = get_sensor_visual_positions(sensor_library, board_template)
    board_height = calculate_pcb_visual_height(sensor_library, board_template) - 80
    board_inner_height = board_height - 36
    footer_y = board_height - 12
    bottom_mount_y = board_height - 70
    visible_components = list(sensor_positions) if show_all_footprints else [
        component for component in selected_components if component in sensor_positions
    ]
    detail_data = build_visual_detail_data(
        selected_components,
        selected_sensor_refs,
        sensor_library,
        all_sensor_refs,
        bom_rows,
        pin_map_rows,
        netlist_rows,
    )
    detail_json = json.dumps(detail_data, ensure_ascii=True)
    default_detail = selected_components[0] if selected_components else "BOARD"

    mounting_holes = "".join(
        f"""
        <g class="click-target" data-detail="MOUNTING">
          <title>{label} mounting hole at approx {coord}</title>
          <circle cx="{x}" cy="{y}" r="18" fill="#DDE7E0" stroke="#0E4A35" stroke-width="4"/>
          <circle cx="{x}" cy="{y}" r="9" fill="#0B2B21"/>
          {svg_text(x - 10, y + 34, label, 11, "800", "#E8FFF1")}
        </g>
        """
        for x, y, label, coord in [
            (62, 60, "H1", "(3,3) mm"),
            (798, 60, "H2", "(42,3) mm"),
            (62, bottom_mount_y, "H3", "(3,32) mm"),
            (798, bottom_mount_y, "H4", "(42,32) mm"),
        ]
    )
    test_points = "".join(
        f"""
        <g class="click-target" data-detail="TEST_POINTS">
          <title>{label} test point</title>
          <circle cx="{x}" cy="480" r="10" fill="#FFE083" stroke="#8A6A00" stroke-width="2"/>
          {svg_text(x - 15, 506, label, 11, "800", "#193A2C")}
        </g>
        """
        for x, label in [(265, "5V"), (310, "3V3"), (360, "GND"), (412, "SDA"), (462, "SCL")]
    )

    sensor_shapes: List[str] = []
    sensor_traces: List[str] = []
    for component in visible_components:
        position = sensor_positions[component]
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
            + svg_trace(
                [(525, 230), (585, 230), (585, y + 24), (x, y + 24)],
                "#2E6FDC",
                3,
                detail_id="TRACE_I2C",
                title=f"I2C SDA route to {component}",
            )
            + svg_trace(
                [(525, 250), (596, 250), (596, y + 42), (x, y + 42)],
                "#2E6FDC",
                3,
                detail_id="TRACE_I2C",
                title=f"I2C SCL route to {component}",
            )
            + svg_trace(
                [(338, 214), (580, 214), (580, y + 12), (x, y + 12)],
                "#C79A19",
                4,
                detail_id="TRACE_3V3",
                title=f"3V3 rail to {component}",
            )
            + "</g>"
        )
        sensor_shapes.append(
            f"""
            <g class="click-target" data-detail="{html.escape(component)}">
              <title>{html.escape(ref)} {html.escape(component)} - {html.escape(status_text)}</title>
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

    if not visible_components:
        sensor_shapes.append(
            f"""
            <g class="click-target" data-detail="BOARD">
              <title>No populated sensor footprint selected</title>
              <rect x="614" y="82" width="170" height="82" rx="8" fill="#E8F5EA" stroke="#0C6B46" stroke-width="2"/>
              {svg_text(632, 112, "No sensor selected", 15, "800", "#113629")}
              {svg_text(632, 136, "Add a supported sensor", 11, "600", "#24483A")}
            </g>
            """
        )

    return f"""
    <div class="pcb-interactive-shell">
      <style>
        .pcb-interactive-shell {{
          width: 100%;
          overflow-x: auto;
          color: #102018;
          font-family: Inter, Segoe UI, Arial, sans-serif;
        }}
        .click-target, .trace-hotspot {{
          cursor: pointer;
        }}
        .click-target:hover rect,
        .click-target:hover circle {{
          stroke: #FFFFFF;
          stroke-width: 4;
        }}
        .trace-hotspot:hover {{
          stroke-width: 10;
          opacity: 0.82;
        }}
        .pcb-inspector {{
          margin-top: 10px;
          border: 1px solid #B7D3C4;
          border-radius: 8px;
          background: #F8FCF9;
          padding: 14px 16px;
          max-width: 980px;
          box-sizing: border-box;
        }}
        .pcb-inspector-title {{
          font-size: 17px;
          font-weight: 800;
          margin: 0 0 4px 0;
        }}
        .pcb-inspector-status {{
          display: inline-block;
          padding: 3px 8px;
          border-radius: 999px;
          background: #DCEFE3;
          color: #0D4A32;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 8px;
        }}
        .pcb-inspector-grid {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }}
        .pcb-inspector h4 {{
          margin: 6px 0 4px 0;
          font-size: 12px;
          text-transform: uppercase;
          color: #315A48;
        }}
        .pcb-inspector ul {{
          margin: 0;
          padding-left: 18px;
        }}
        .pcb-inspector li {{
          margin: 3px 0;
          font-size: 12px;
          line-height: 1.35;
        }}
        .pcb-inspector-placement {{
          margin: 0 0 8px 0;
          font-size: 13px;
          line-height: 1.4;
        }}
        @media (max-width: 760px) {{
          .pcb-inspector-grid {{
            grid-template-columns: 1fr;
          }}
        }}
      </style>
      <svg viewBox="0 0 860 {board_height}" width="100%" height="{board_height + 60}" role="img" aria-label="Clear top-view PCB layout visual">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#2A6B4F" stroke-width="0.7" opacity="0.14"/>
          </pattern>
          <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="#0A1D15" flood-opacity="0.22"/>
          </filter>
        </defs>

        <g class="click-target" data-detail="BOARD">
          <title>Board outline: target 45 mm x 35 mm, 2-layer FR-4</title>
          <rect x="12" y="12" width="836" height="{board_height - 24}" rx="30" fill="#166342" filter="url(#shadow)"/>
          <rect x="28" y="28" width="804" height="{board_inner_height}" rx="20" fill="url(#grid)" stroke="#D8F1DE" stroke-width="2" opacity="0.96"/>
          {svg_text(310, 50, "Target board: 45 mm x 35 mm, 2-layer FR-4", 13, "800", "#E8FFF1")}
        </g>
        <g class="click-target" data-detail="ANTENNA">
          <title>ESP32 antenna keepout: no copper, vias, components, or mounting hardware</title>
          <rect x="492" y="78" width="96" height="92" rx="8" fill="none" stroke="#FFE26F" stroke-width="3" stroke-dasharray="8 6"/>
          {svg_text(498, 68, "ESP32 antenna keepout", 12, "800", "#FFF3A5")}
        </g>
        {mounting_holes}

        <g class="click-target" data-detail="J1">
          <title>J1 USB-C power input on left edge</title>
          <rect x="30" y="236" width="78" height="94" rx="6" fill="#D8DEE2" stroke="#56636A" stroke-width="3"/>
          <rect x="10" y="258" width="42" height="50" rx="5" fill="#F4F6F7" stroke="#56636A" stroke-width="2"/>
          {svg_text(38, 224, "J1 USB-C", 15, "800", "#E8FFF1")}
          {svg_text(24, 350, "Connector side: left edge", 12, "800", "#E8FFF1")}
        </g>

        <g class="click-target" data-detail="U1">
          <title>U1 regulator and C1-C3 power capacitors</title>
          {svg_component(158, 238, 112, 76, "U1 LDO", "5 V to 3.3 V", "#F9C76B")}
          {svg_component(288, 236, 86, 42, "C1-C3", "power caps", "#F5E6A8")}
        </g>
        <g class="click-target" data-detail="I2C_PULLUPS">
          <title>R3/R4 I2C pullups to 3.3 V</title>
          {svg_component(288, 142, 92, 50, "R3/R4", "I2C pullups", "#F5E6A8")}
        </g>

        <g class="click-target" data-detail="U2">
          <title>U2 ESP32-WROOM-32 module</title>
          <rect x="405" y="176" width="140" height="170" rx="7" fill="#DDE8E4" stroke="#173A31" stroke-width="2"/>
          <rect x="497" y="176" width="48" height="170" fill="#F2D36B" stroke="#173A31" stroke-width="2"/>
          <path d="M505 200 h30 M505 224 h30 M505 248 h30 M505 272 h30 M505 296 h30" stroke="#8D7414" stroke-width="3"/>
          {svg_text(420, 206, "U2 ESP32", 17, "800")}
          {svg_text(420, 230, "WROOM-32", 13, "700")}
          {svg_text(420, 255, "WiFi / Bluetooth", 11, "600")}
        </g>

        <g class="click-target" data-detail="STATUS_LED">
          <title>D1/R5 status LED</title>
          {svg_component(110, 390, 95, 54, "D1/R5", "status LED", "#D4E9FF")}
        </g>
        <g class="click-target" data-detail="RESET">
          <title>SW1/R6 reset interface</title>
          {svg_component(218, 390, 95, 54, "SW1/R6", "reset", "#D4E9FF")}
        </g>
        {test_points}

        {svg_trace([(90, 284), (158, 284)], "#E67E22", 8, detail_id="TRACE_5V", title="VBUS_5V path")}
        {svg_trace([(270, 276), (338, 276), (338, 214), (405, 214)], "#C79A19", 7, detail_id="TRACE_3V3", title="3V3 rail")}
        {svg_trace([(475, 282), (475, 480), (100, 480)], "#7A8C82", 4, dashed=True, detail_id="TRACE_GND", title="GND return")}
        {svg_trace([(270, 258), (288, 258)], "#C79A19", 4, detail_id="TRACE_3V3", title="3V3 decoupling branch")}
        {svg_trace([(380, 168), (405, 230)], "#2E6FDC", 4, detail_id="TRACE_I2C", title="I2C_SDA route")}
        {svg_trace([(380, 182), (405, 250)], "#2E6FDC", 4, detail_id="TRACE_I2C", title="I2C_SCL route")}
        {svg_trace([(475, 346), (475, 390), (260, 390)], "#2E6FDC", 4, detail_id="STATUS_LED", title="GPIO / reset routing")}
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
      <div id="pcb-detail-panel" class="pcb-inspector" aria-live="polite"></div>
      <script>
        (function() {{
          const detailData = {detail_json};
          const defaultDetail = "{html.escape(default_detail)}";
          const panel = document.getElementById("pcb-detail-panel");
          function addList(section, title, items) {{
            const block = document.createElement("div");
            const heading = document.createElement("h4");
            heading.textContent = title;
            block.appendChild(heading);
            const list = document.createElement("ul");
            items.forEach(function(item) {{
              const li = document.createElement("li");
              li.textContent = item;
              list.appendChild(li);
            }});
            block.appendChild(list);
            section.appendChild(block);
          }}
          function renderDetail(id) {{
            const data = detailData[id] || detailData.BOARD;
            document.querySelectorAll("[data-detail]").forEach(function(node) {{
              node.classList.toggle("is-selected", node.dataset.detail === id);
            }});
            panel.innerHTML = "";
            const title = document.createElement("div");
            title.className = "pcb-inspector-title";
            title.textContent = data.title;
            const status = document.createElement("div");
            status.className = "pcb-inspector-status";
            status.textContent = data.status;
            const placement = document.createElement("p");
            placement.className = "pcb-inspector-placement";
            placement.textContent = data.placement;
            const grid = document.createElement("div");
            grid.className = "pcb-inspector-grid";
            addList(grid, "BOM", data.bom || []);
            addList(grid, "Pins", data.pins || []);
            addList(grid, "Nets", data.nets || []);
            panel.appendChild(title);
            panel.appendChild(status);
            panel.appendChild(placement);
            panel.appendChild(grid);
          }}
          document.querySelectorAll("[data-detail]").forEach(function(node) {{
            node.addEventListener("click", function(event) {{
              event.preventDefault();
              event.stopPropagation();
              renderDetail(node.dataset.detail);
            }});
          }});
          renderDetail(defaultDetail);
        }})();
      </script>
    </div>
    """
