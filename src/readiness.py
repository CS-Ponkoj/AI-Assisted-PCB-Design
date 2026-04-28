"""Design readiness review for generated PCB handoffs."""

import re
from typing import Any, Dict, List, Tuple


COMMON_SENSOR_NETS = {"3V3", "GND", "I2C_SDA", "I2C_SCL"}
STANDARD_I2C_PIN_NAMES = {"VCC", "VDD", "VDDIO", "GND", "SDA", "SCL"}


def estimate_power_margin_ma(
    selected_components: List[str],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> Tuple[float, float]:
    """Return estimated peak current and regulator margin in mA."""
    power_template = board_template["power_budget_base"]
    total_ma = float(power_template["base_load_ma"])
    for component in selected_components:
        total_ma += float(sensor_library[component]["current_ma"])
    margin = float(power_template["regulator_min_ma"]) - total_ma
    return total_ma, margin


def optional_sensor_pins(
    selected_components: List[str],
    sensor_library: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Return non-standard sensor pins that need designer review."""
    pins: List[str] = []
    for component in selected_components:
        for pin, net in sensor_library[component].get("pins", {}).items():
            if pin.upper() not in STANDARD_I2C_PIN_NAMES or net not in COMMON_SENSOR_NETS:
                pins.append(f"{component}.{pin} -> {net}")
    return pins


def validation_summary(validation_rows: List[Dict[str, str]]) -> Tuple[bool, bool]:
    """Return whether active plugin validation has errors or warnings."""
    active_rows = [row for row in validation_rows if row["Status"] != "Disabled"]
    has_errors = any(row["Status"] == "Error" for row in active_rows)
    has_warnings = any(row["Status"] == "Warning" for row in active_rows)
    return has_errors, has_warnings


def generate_design_readiness_review(
    package: Dict[str, Any],
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
    validation_rows: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Generate a Ready / Needs Review / Blocked status for the current handoff."""
    parsed = package["parsed"]
    selected = parsed["selected_components"]
    unsupported = parsed["unsupported_requirements"]
    total_ma, margin_ma = estimate_power_margin_ma(selected, sensor_library, board_template)
    optional_pins = optional_sensor_pins(selected, sensor_library)
    has_validation_errors, has_validation_warnings = validation_summary(validation_rows)

    blockers: List[str] = []
    review_items: List[str] = []
    passed: List[str] = []

    if not selected:
        blockers.append("No supported sensor was selected from the user input.")
    else:
        passed.append(f"{len(selected)} supported sensor footprint(s) selected: {', '.join(selected)}.")

    if unsupported:
        blockers.append("Unsupported request(s) excluded: " + ", ".join(unsupported) + ".")
    else:
        passed.append("No unsupported hardware request was detected.")

    if has_validation_errors:
        blockers.append("One or more enabled sensor plugin files have validation errors.")
    elif has_validation_warnings:
        review_items.append("Sensor plugin validation has warning(s); review the validation panel.")
    else:
        passed.append("Enabled sensor plugin files passed validation.")

    if margin_ma <= 0:
        blockers.append(f"Estimated 3.3 V load is {total_ma:.1f} mA, exceeding the regulator target.")
    elif margin_ma < 150:
        review_items.append(f"3.3 V regulator margin is {margin_ma:.1f} mA; review thermal derating.")
    else:
        passed.append(f"Estimated 3.3 V regulator margin is {margin_ma:.1f} mA.")

    if optional_pins:
        review_items.append("Optional/configuration pins need review: " + ", ".join(optional_pins) + ".")
    else:
        passed.append("Selected sensors use only standard 3.3 V I2C pins.")

    if blockers:
        status = "Blocked"
    elif review_items:
        status = "Needs Review"
    else:
        status = "Ready"

    rows = [
        {"Category": "Status", "Result": status, "Detail": "Design handoff readiness gate."},
        {"Category": "Power", "Result": f"{total_ma:.1f} mA load", "Detail": f"{margin_ma:.1f} mA regulator margin."},
        {"Category": "Sensors", "Result": ", ".join(selected) if selected else "None", "Detail": "Selected supported footprints."},
    ]
    return {
        "status": status,
        "blockers": blockers,
        "review_items": review_items,
        "passed": passed,
        "rows": rows,
    }


def status_message_level(status: str) -> str:
    """Map readiness status to a Streamlit message level name."""
    normalized = re.sub(r"\s+", "_", status.lower())
    return {"ready": "success", "needs_review": "warning", "blocked": "error"}.get(normalized, "info")
