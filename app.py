"""Streamlit UI for the AI-assisted PCB design generator."""

from typing import Any, Dict, List
from urllib.parse import quote

import streamlit as st

from src.data_loader import (
    build_requirement_groups,
    build_sensor_keywords,
    build_sensor_reference_map,
    build_supported_sensors,
    collect_sensor_validation,
    load_json,
    load_sensor_definitions,
)
from src.design_generator import (
    assign_sensor_refs as assign_sensor_refs_for_context,
    bom_row,
    generate_assumptions as generate_assumptions_for_context,
    generate_bom as generate_bom_for_context,
    generate_bringup_checklist as generate_bringup_checklist_for_context,
    generate_design_package as generate_design_package_for_context,
    generate_fabrication_checklist as generate_fabrication_checklist_for_context,
    generate_io_table as generate_io_table_for_context,
    generate_layout_guidance as generate_layout_guidance_for_context,
    generate_netlist_table as generate_netlist_table_for_context,
    generate_pin_map as generate_pin_map_for_context,
    generate_power_budget as generate_power_budget_for_context,
    generate_project_summary as generate_project_summary_for_context,
    generate_schematic_summary as generate_schematic_summary_for_context,
    net_row,
    pin_row,
)
from src.exports import generate_export_package, rows_to_csv
from src.parser import ordered_requirements as ordered_requirements_for_context
from src.parser import parse_requirements as parse_requirements_for_context
from src.validation import analyze_sensor_definition, validate_sensor_definition
from src.visuals import (
    calculate_pcb_visual_height as calculate_pcb_visual_height_for_context,
    generate_block_diagram as generate_block_diagram_for_context,
    generate_pcb_layout,
    generate_pcb_visual_svg as generate_pcb_visual_svg_for_context,
    generate_schematic_diagram as generate_schematic_diagram_for_context,
    get_sensor_visual_positions as get_sensor_visual_positions_for_context,
)


SENSOR_LIBRARY: Dict[str, Dict[str, Any]] = load_sensor_definitions()
SUPPORTED_SENSORS: Dict[str, Dict[str, str]] = build_supported_sensors(SENSOR_LIBRARY)
SENSOR_KEYWORDS: Dict[str, str] = build_sensor_keywords(SENSOR_LIBRARY)
REQUIREMENT_GROUPS: List[List[str]] = build_requirement_groups(SENSOR_LIBRARY)
REQUIREMENT_CONFIG: Dict[str, Any] = load_json("data/requirement_keywords.json")
BOARD_TEMPLATE: Dict[str, Any] = load_json("data/board_template.json")
SENSOR_REFS: Dict[str, str] = build_sensor_reference_map(SENSOR_LIBRARY, BOARD_TEMPLATE)


def ordered_requirements(requirements: List[str]) -> List[str]:
    """Compatibility wrapper for requirement ordering."""
    return ordered_requirements_for_context(requirements, SENSOR_LIBRARY)


def parse_requirements(user_input: str) -> Dict[str, Any]:
    """Parse free-form requirements using the loaded project data."""
    return parse_requirements_for_context(
        user_input,
        SENSOR_LIBRARY,
        SUPPORTED_SENSORS,
        SENSOR_KEYWORDS,
        REQUIREMENT_GROUPS,
        REQUIREMENT_CONFIG,
    )


def assign_sensor_refs(selected_components: List[str]) -> Dict[str, str]:
    """Assign stable reference designators to populated sensor ICs."""
    return assign_sensor_refs_for_context(selected_components, SENSOR_REFS)


def generate_design_package(user_input: str) -> Dict[str, Any]:
    """Generate the complete PCB handoff data structure."""
    parsed = parse_requirements(user_input)
    return generate_design_package_for_context(
        user_input,
        parsed,
        SENSOR_LIBRARY,
        BOARD_TEMPLATE,
        SENSOR_REFS,
    )


def generate_project_summary(user_input: str, parsed: Dict[str, Any]) -> List[Dict[str, str]]:
    return generate_project_summary_for_context(user_input, parsed, BOARD_TEMPLATE)


def generate_assumptions(parsed: Dict[str, Any]) -> List[Dict[str, str]]:
    return generate_assumptions_for_context(parsed, BOARD_TEMPLATE)


def generate_io_table(parsed: Dict[str, Any], selected_components: List[str]) -> List[Dict[str, str]]:
    return generate_io_table_for_context(parsed, selected_components, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_bom(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    return generate_bom_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_pin_map(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    return generate_pin_map_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_netlist_table(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    return generate_netlist_table_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_power_budget(selected_components: List[str]) -> List[Dict[str, str]]:
    return generate_power_budget_for_context(selected_components, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_layout_guidance(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    return generate_layout_guidance_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_fabrication_checklist() -> List[Dict[str, str]]:
    return generate_fabrication_checklist_for_context(BOARD_TEMPLATE)


def generate_bringup_checklist(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[Dict[str, str]]:
    return generate_bringup_checklist_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_schematic_summary(selected_components: List[str], sensor_refs: Dict[str, str]) -> List[str]:
    return generate_schematic_summary_for_context(selected_components, sensor_refs, SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_block_diagram(selected_components: List[str]):
    return generate_block_diagram_for_context(selected_components, SENSOR_LIBRARY)


def generate_schematic_diagram(selected_components: List[str]):
    return generate_schematic_diagram_for_context(selected_components, SENSOR_LIBRARY)


def get_sensor_visual_positions() -> Dict[str, Dict[str, Any]]:
    return get_sensor_visual_positions_for_context(SENSOR_LIBRARY, BOARD_TEMPLATE)


def calculate_pcb_visual_height() -> int:
    return calculate_pcb_visual_height_for_context(SENSOR_LIBRARY, BOARD_TEMPLATE)


def generate_pcb_visual_svg(selected_components: List[str], sensor_refs: Dict[str, str]) -> str:
    return generate_pcb_visual_svg_for_context(
        selected_components,
        sensor_refs,
        SENSOR_LIBRARY,
        BOARD_TEMPLATE,
        SENSOR_REFS,
    )


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


def render_visual_section(package: Dict[str, Any], selected_components: List[str]) -> None:
    """Render the primary PCB visual before the detailed handoff tables."""
    st.header("PCB Layout Visual")
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

    with st.expander("System architecture and schematic connectivity", expanded=False):
        st.subheader("System Architecture")
        st.graphviz_chart(generate_block_diagram(selected_components))
        st.subheader("Schematic Connectivity")
        st.graphviz_chart(generate_schematic_diagram(selected_components))


def render_detail_sections(package: Dict[str, Any], variant: str) -> None:
    """Render the detailed designer handoff sections as collapsible dropdowns."""
    parsed = package["parsed"]

    with st.expander("1. Requirement and Controlled Decisions", expanded=False):
        render_table("Project Summary", package["summary"])
        render_table("Design Assumptions", package["assumptions"])
        if parsed["unsupported_requirements"]:
            st.warning(
                "Unsupported requests were detected and intentionally excluded: "
                + ", ".join(parsed["unsupported_requirements"])
            )
        st.subheader("Parsed Requirement JSON")
        st.json(parsed)

    with st.expander("2. Electrical Inputs and Outputs", expanded=False):
        render_table("I/O Definition", package["io_table"])

    with st.expander("3. Source-of-Truth Engineering Tables", expanded=False):
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

    with st.expander("4. Schematic and PCB Implementation Notes", expanded=False):
        st.subheader("Schematic Summary")
        for line in package["schematic_summary"]:
            st.markdown(f"- {line}")
        render_table("2-Layer PCB Layout Instructions", package["layout_guidance"])


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


def render_scope_panel() -> None:
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


def render_sensor_validation_panel() -> None:
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


def main() -> None:
    """Streamlit entry point."""
    st.set_page_config(page_title="PCB Designer Generator", layout="wide")
    st.title("PCB Designer Handoff Generator")
    st.markdown(
        "Generate a build-oriented 2-layer ESP32 sensor-board handoff from a controlled natural-language requirement."
    )
    render_scope_panel()
    render_sensor_validation_panel()

    default_input = (
        "Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, "
        "temperature, humidity, and light sensing."
    )
    user_input = st.text_area("Board requirements", value=default_input, height=110)
    st.button("Refresh PCB Handoff", type="primary")

    if user_input.strip():
        package = generate_design_package(user_input.strip())
        selected_components = package["parsed"]["selected_components"]
        variant = export_variant_slug(package)

        render_visual_section(package, selected_components)
        render_detail_sections(package, variant)

        with st.expander("5. Build Checks", expanded=False):
            render_checklist("Fabrication and Assembly Checklist", package["fabrication_checklist"])
            render_checklist("Bring-Up Checklist", package["bringup_checklist"])

        st.header("Export Package")
        st.caption("Download the full generated handoff report. Table-specific CSV exports are inside section 3.")
        render_export_buttons(package)


if __name__ == "__main__":
    main()
