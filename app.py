"""Streamlit UI for the PCB design generator."""

from typing import Any, Dict, List, Optional, Tuple
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
from src.ai_assistant import LOCAL_ASSISTANT_NAME, run_ai_requirement_assistant
from src.design_generator import (
    assign_sensor_refs as assign_sensor_refs_for_context,
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
)
from src.exports import generate_export_package, rows_to_csv
from src.llm_assistant import (
    OLLAMA_MODEL_DEFAULT,
    check_ollama_status,
    run_ollama_requirement_assistant,
)
from src.parser import ordered_requirements as ordered_requirements_for_context
from src.parser import parse_requirements as parse_requirements_for_context
from src.readiness import generate_design_readiness_review as generate_design_readiness_review_for_context
from src.readiness import status_message_level
from src.validation import analyze_sensor_definition, validate_sensor_definition
from src.visuals import (
    calculate_pcb_visual_height as calculate_pcb_visual_height_for_context,
    generate_block_diagram as generate_block_diagram_for_context,
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


def generate_design_package(user_input: str, parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate the complete PCB handoff data structure."""
    parsed = parsed or parse_requirements(user_input)
    return generate_design_package_for_context(
        user_input,
        parsed,
        SENSOR_LIBRARY,
        BOARD_TEMPLATE,
        SENSOR_REFS,
    )


def generate_ai_requirements(user_input: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run the local requirement assistant and return validated requirements."""
    return run_ai_requirement_assistant(
        user_input,
        SENSOR_LIBRARY,
        SUPPORTED_SENSORS,
        SENSOR_KEYWORDS,
        REQUIREMENT_GROUPS,
        REQUIREMENT_CONFIG,
    )


def generate_llm_requirements(user_input: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run the optional Ollama LLM assistant and return validated requirements."""
    return run_ollama_requirement_assistant(
        user_input,
        SENSOR_LIBRARY,
        SUPPORTED_SENSORS,
        SENSOR_KEYWORDS,
        REQUIREMENT_GROUPS,
        REQUIREMENT_CONFIG,
    )


def generate_design_readiness_review(
    package: Dict[str, Any],
    validation_rows: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Generate Ready / Needs Review / Blocked status for the current package."""
    return generate_design_readiness_review_for_context(
        package,
        SENSOR_LIBRARY,
        BOARD_TEMPLATE,
        validation_rows or collect_sensor_validation(),
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


def render_ai_summary(parsed: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """Render assistant notes when an assistant mode is requested."""
    ai_info = parsed.get("ai_assistant")
    if not ai_info:
        return

    with st.expander("Requirement Assistant", expanded=bool(metadata.get("used_ai"))):
        mode = metadata.get("mode", ai_info.get("mode", "local"))
        if mode == "ollama":
            st.success(f"LLM assistant used Ollama model {metadata.get('model', OLLAMA_MODEL_DEFAULT)}.")
        elif mode == "local_fallback":
            st.warning("LLM assistant was requested, but the app used Base assistant fallback.")
        elif metadata.get("used_ai"):
            st.success(f"Base assistant used: {metadata.get('model', LOCAL_ASSISTANT_NAME)}.")
        else:
            st.info("Assistant was requested, but the app used the rule-based parser.")
        st.table(
            [
                {"Item": "Assistant enabled", "Value": str(ai_info.get("enabled"))},
                {"Item": "Mode", "Value": str(ai_info.get("mode", mode))},
                {"Item": "Model", "Value": str(metadata.get("model", ai_info.get("model", LOCAL_ASSISTANT_NAME)))},
                {"Item": "Provider", "Value": str(metadata.get("provider", "In-app Base"))},
                {"Item": "Endpoint", "Value": str(metadata.get("base_url", "Not used"))},
                {"Item": "Confidence", "Value": str(ai_info.get("confidence"))},
                {"Item": "Selected sensors", "Value": ", ".join(parsed["selected_components"]) or "None"},
                {"Item": "Unsupported requests", "Value": ", ".join(parsed["unsupported_requirements"]) or "None"},
            ]
        )
        for note in ai_info.get("notes", []):
            st.markdown(f"- {note}")


def render_readiness_review(review: Dict[str, Any]) -> None:
    """Render the Ready / Needs Review / Blocked panel."""
    status = review["status"]
    level = status_message_level(status)
    message = f"Design readiness: {status}"
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)

    st.table(review["rows"])
    if review["blockers"]:
        st.subheader("Blockers")
        for item in review["blockers"]:
            st.markdown(f"- {item}")
    if review["review_items"]:
        st.subheader("Needs Review")
        for item in review["review_items"]:
            st.markdown(f"- {item}")
    if review["passed"]:
        with st.expander("Passed Checks", expanded=False):
            for item in review["passed"]:
                st.markdown(f"- {item}")


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


def render_sensor_validation_panel() -> List[Dict[str, str]]:
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
    return validation_rows


def build_handoff(
    user_input: str,
    parser_mode: str,
    validation_rows: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Build and cache the complete generated handoff for the submitted form."""
    if parser_mode == "LLM assistant":
        parsed, ai_metadata = generate_llm_requirements(user_input)
    else:
        parsed, ai_metadata = generate_ai_requirements(user_input)

    package = generate_design_package(user_input, parsed=parsed)
    readiness = generate_design_readiness_review(package, validation_rows)
    package["readiness_review"] = readiness
    return {
        "package": package,
        "ai_metadata": ai_metadata,
        "mode": parser_mode,
        "input": user_input,
    }


def render_mode_selector() -> str:
    """Render the requirement extraction mode selector with Base selected first."""
    parser_mode = st.radio(
        "Requirement extraction mode",
        ["Base", "LLM assistant"],
        horizontal=True,
        help=(
            "Base needs no setup. LLM assistant uses an Ollama-compatible model server "
            "and falls back to Base if unavailable."
        ),
    )
    if parser_mode == "Base":
        st.info("Base mode is active by default. It is free, offline, and runs inside the app.")
    else:
        render_llm_provider_status()
    return parser_mode


def render_llm_provider_status() -> None:
    """Render the configured LLM provider endpoint and availability."""
    status = check_ollama_status()
    rows = [
        {"Item": "Provider", "Value": status["provider"]},
        {"Item": "Endpoint", "Value": status["base_url"]},
        {"Item": "Model", "Value": status["model"]},
        {"Item": "Server reachable", "Value": "Yes" if status["reachable"] else "No"},
        {"Item": "Model available", "Value": "Yes" if status["model_available"] else "No"},
        {"Item": "Auth configured", "Value": "Yes" if status["auth_configured"] else "No"},
    ]
    with st.expander("LLM Provider Status", expanded=True):
        if status["reachable"] and status["model_available"]:
            st.success("LLM assistant is ready. The app will still validate its output before generating the PCB handoff.")
        elif status["reachable"]:
            st.warning(
                f"LLM server is reachable, but model {status['model']} was not listed. "
                "Generation may fall back to Base mode."
            )
        else:
            st.warning("LLM server is unavailable. Generate will use Base fallback if LLM mode is selected.")
        st.table(rows)
        if status["models"]:
            st.caption("Available models: " + ", ".join(status["models"]))
        if status["error"]:
            st.caption(f"Last status error: {status['error']}")
        st.caption(
            "Configure deployment with OLLAMA_URL for a remote server. Optional auth can use "
            "OLLAMA_API_KEY or OLLAMA_AUTH_HEADER."
        )


def render_requirement_form() -> Tuple[bool, str]:
    """Render requirement input controls and return submitted values."""
    default_input = (
        "Make me a USB-C powered indoor monitoring board with WiFi, Bluetooth, "
        "temperature, humidity, and light sensing."
    )
    with st.form("pcb_requirement_form"):
        user_input = st.text_area("Board requirements", value=default_input, height=110)
        submitted = st.form_submit_button("Generate PCB Handoff", type="primary")
    return submitted, user_input.strip()


def render_cached_handoff(cached_handoff: Dict[str, Any]) -> None:
    """Render the last generated handoff without recomputing it."""
    package = cached_handoff["package"]
    ai_metadata = cached_handoff["ai_metadata"]
    selected_components = package["parsed"]["selected_components"]
    variant = export_variant_slug(package)

    st.caption(f"Generated from {cached_handoff['mode']} mode for: {cached_handoff['input']}")
    render_ai_summary(package["parsed"], ai_metadata)
    render_readiness_review(package["readiness_review"])
    render_visual_section(package, selected_components)
    render_detail_sections(package, variant)

    with st.expander("5. Build Checks", expanded=False):
        render_checklist("Fabrication and Assembly Checklist", package["fabrication_checklist"])
        render_checklist("Bring-Up Checklist", package["bringup_checklist"])

    st.header("Export Package")
    st.caption("Download the full generated handoff report. Table-specific CSV exports are inside section 3.")
    render_export_buttons(package)


def main() -> None:
    """Streamlit entry point."""
    st.set_page_config(page_title="PCB Designer Generator", layout="wide")
    st.title("PCB Designer Handoff Generator")
    st.markdown(
        "Generate a build-oriented 2-layer ESP32 sensor-board handoff from a controlled natural-language requirement."
    )
    render_scope_panel()
    validation_rows = render_sensor_validation_panel()
    parser_mode = render_mode_selector()
    submitted, user_input = render_requirement_form()

    if submitted:
        if user_input:
            with st.spinner("Generating PCB handoff..."):
                st.session_state["pcb_handoff"] = build_handoff(user_input, parser_mode, validation_rows)
        else:
            st.warning("Enter a board requirement before generating the PCB handoff.")

    if "pcb_handoff" in st.session_state:
        render_cached_handoff(st.session_state["pcb_handoff"])
    else:
        st.info("Enter a requirement, choose a mode, then click **Generate PCB Handoff**.")


if __name__ == "__main__":
    main()
