"""PCB handoff data generation."""

from typing import Any, Dict, List


def assign_sensor_refs(selected_components: List[str], sensor_refs: Dict[str, str]) -> Dict[str, str]:
    """Assign stable reference designators to populated sensor ICs."""
    return {component: sensor_refs[component] for component in selected_components}


def generate_design_package(
    user_input: str,
    parsed: Dict[str, Any],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
    all_sensor_refs: Dict[str, str],
) -> Dict[str, Any]:
    """Generate the complete PCB handoff data structure."""
    selected_components = parsed["selected_components"]
    sensor_refs = assign_sensor_refs(selected_components, all_sensor_refs)

    return {
        "parsed": parsed,
        "summary": generate_project_summary(user_input, parsed, board_template),
        "assumptions": generate_assumptions(parsed, board_template),
        "io_table": generate_io_table(parsed, selected_components, sensor_library, board_template),
        "bom": generate_bom(selected_components, sensor_refs, sensor_library, board_template),
        "pin_map": generate_pin_map(selected_components, sensor_refs, sensor_library, board_template),
        "netlist": generate_netlist_table(selected_components, sensor_refs, sensor_library, board_template),
        "power_budget": generate_power_budget(selected_components, sensor_library, board_template),
        "layout_guidance": generate_layout_guidance(selected_components, sensor_refs, sensor_library, board_template),
        "fabrication_checklist": generate_fabrication_checklist(board_template),
        "bringup_checklist": generate_bringup_checklist(selected_components, sensor_refs, sensor_library, board_template),
        "schematic_summary": generate_schematic_summary(selected_components, sensor_refs, sensor_library, board_template),
        "sensor_refs": sensor_refs,
    }


def generate_project_summary(user_input: str, parsed: Dict[str, Any], board_template: Dict[str, Any]) -> List[Dict[str, str]]:
    """Summarize the generated board in designer-facing terms."""
    sensors = parsed["selected_components"]
    rows = [{"Item": "Original requirement", "Decision": user_input}]
    rows.extend(dict(row) for row in board_template["project_summary_static"])
    rows.append({"Item": "Sensors populated", "Decision": ", ".join(sensors) if sensors else "No supported sensors selected"})
    return rows


def generate_assumptions(parsed: Dict[str, Any], board_template: Dict[str, Any]) -> List[Dict[str, str]]:
    """State the fixed engineering assumptions for the handoff."""
    unsupported = parsed["unsupported_requirements"]
    unsupported_text = ", ".join(unsupported) if unsupported else "None"
    rows = [dict(row) for row in board_template["assumptions_base"]]
    rows.append({"Assumption": "Unsupported requests", "Value": unsupported_text})
    return rows


def generate_io_table(
    parsed: Dict[str, Any],
    selected_components: List[str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Define electrical and functional inputs/outputs."""
    rows = [dict(row) for row in board_template["io_table_base"]]
    for row in rows:
        if row["Interface"] == "Wireless":
            row["Electrical"] = row["Electrical"].format(wireless=", ".join(parsed["wireless"]))

    for component in selected_components:
        sensor = sensor_library[component]
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


def generate_bom(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate a full BOM for the selected board variant."""
    rows = [dict(row) for row in board_template["bom_base"]]

    sensor_decoupling_index = 6
    for component in selected_components:
        sensor = sensor_library[component]
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


def generate_pin_map(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate a pin-level implementation map."""
    rows = [dict(row) for row in board_template["pin_map_base"]]

    for component in selected_components:
        ref = sensor_refs[component]
        sensor = sensor_library[component]
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


def generate_netlist_table(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate a PCB netlist table with routing intent."""
    rows = [dict(row) for row in board_template["netlist_base"]]
    common_sensor_nets = {"3V3", "GND", "I2C_SDA", "I2C_SCL"}

    for component in selected_components:
        ref = sensor_refs[component]
        sensor = sensor_library[component]
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


def generate_power_budget(
    selected_components: List[str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Estimate current draw and regulator margin."""
    power_template = board_template["power_budget_base"]
    rows = [dict(row) for row in power_template["rows"]]

    total_ma = float(power_template["base_load_ma"])
    for component in selected_components:
        sensor = sensor_library[component]
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


def generate_layout_guidance(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate 2-layer PCB placement and routing instructions."""
    rows = [dict(row) for row in board_template["layout_guidance_base"]]

    for component in selected_components:
        rows.append({"Area": f"{sensor_refs[component]} {component}", "Instruction": sensor_library[component]["placement"]})
    return rows


def generate_fabrication_checklist(board_template: Dict[str, Any]) -> List[Dict[str, str]]:
    return [dict(row) for row in board_template["fabrication_checklist"]]


def generate_bringup_checklist(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[Dict[str, str]]:
    rows = [dict(row) for row in board_template["bringup_checklist_base"]]
    for component in selected_components:
        sensor = sensor_library[component]
        rows.append(
            {
                "Step": f"Verify {sensor_refs[component]} {component}",
                "Expected result": f"I2C address {sensor['i2c_address']} responds and reports plausible {sensor['functions'].lower()} data.",
            }
        )
    return rows


def generate_schematic_summary(
    selected_components: List[str],
    sensor_refs: Dict[str, str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> List[str]:
    """Create a compact schematic implementation summary."""
    lines = list(board_template["schematic_summary_base"])
    for component in selected_components:
        ref = sensor_refs[component]
        sensor = sensor_library[component]
        lines.append(
            f"{ref} {component} connects to 3V3, GND, I2C_SDA, and I2C_SCL at address {sensor['i2c_address']}; add local 0.1 uF decoupling."
        )
    return lines
