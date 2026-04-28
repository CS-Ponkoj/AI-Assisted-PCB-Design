"""Export helpers for PCB designer packages."""

import csv
import io
import json
from typing import Any, Dict, List


def rows_to_csv(rows: List[Dict[str, str]]) -> str:
    """Convert a list of table rows into UTF-8-safe CSV text."""
    if not rows:
        return ""

    headers: List[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def markdown_cell(value: Any) -> str:
    """Format a value for a compact Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def rows_to_markdown_table(title: str, rows: List[Dict[str, str]]) -> str:
    """Convert generated handoff rows into a Markdown table section."""
    if not rows:
        return f"## {title}\n\nNo rows generated.\n"

    headers: List[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)

    lines = [f"## {title}", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _header in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(row.get(header, "")) for header in headers) + " |")
    lines.append("")
    return "\n".join(lines)


def generate_design_report_markdown(package: Dict[str, Any]) -> str:
    """Generate a full Markdown PCB handoff report."""
    parsed = package["parsed"]
    lines = [
        "# PCB Designer Handoff Report",
        "",
        "## Parsed Requirement",
        "",
        f"- Power input: {parsed['power_input']}",
        f"- MCU: {parsed['mcu']}",
        f"- Logic voltage: {parsed['logic_voltage']}",
        f"- Communication bus: {parsed['communication_bus']}",
        f"- Wireless: {', '.join(parsed['wireless'])}",
        f"- Selected sensors: {', '.join(parsed['selected_components']) if parsed['selected_components'] else 'None'}",
        f"- Unsupported requests excluded: {', '.join(parsed['unsupported_requirements']) if parsed['unsupported_requirements'] else 'None'}",
        "",
    ]

    lines.append(rows_to_markdown_table("Project Summary", package["summary"]))
    lines.append(rows_to_markdown_table("Design Assumptions", package["assumptions"]))
    lines.append(rows_to_markdown_table("Electrical Inputs and Outputs", package["io_table"]))
    lines.append(rows_to_markdown_table("Bill of Materials", package["bom"]))
    lines.append(rows_to_markdown_table("Pin Map", package["pin_map"]))
    lines.append(rows_to_markdown_table("PCB Netlist", package["netlist"]))
    lines.append(rows_to_markdown_table("Power Budget", package["power_budget"]))
    lines.append(rows_to_markdown_table("2-Layer PCB Layout Instructions", package["layout_guidance"]))

    readiness = package.get("readiness_review")
    if readiness:
        lines.extend(["## Design Readiness Review", ""])
        lines.append(f"- Status: {readiness['status']}")
        for item in readiness.get("blockers", []):
            lines.append(f"- Blocker: {item}")
        for item in readiness.get("review_items", []):
            lines.append(f"- Needs review: {item}")
        for item in readiness.get("passed", []):
            lines.append(f"- Passed: {item}")
        lines.append("")

    lines.extend(["## Schematic Summary", ""])
    lines.extend(f"- {line}" for line in package["schematic_summary"])
    lines.append("")
    lines.append(rows_to_markdown_table("Fabrication and Assembly Checklist", package["fabrication_checklist"]))
    lines.append(rows_to_markdown_table("Bring-Up Checklist", package["bringup_checklist"]))
    return "\n".join(lines)


def generate_export_package(package: Dict[str, Any]) -> Dict[str, str]:
    """Generate the downloadable handoff files for the current board variant."""
    return {
        "bom_csv": rows_to_csv(package["bom"]),
        "pin_map_csv": rows_to_csv(package["pin_map"]),
        "netlist_csv": rows_to_csv(package["netlist"]),
        "report_json": json.dumps(package, indent=2),
        "report_markdown": generate_design_report_markdown(package),
    }
