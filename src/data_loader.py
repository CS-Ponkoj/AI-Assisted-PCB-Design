"""Data loading and indexing for sensor-driven PCB generation."""

import json
from pathlib import Path
from typing import Any, Dict, List

from .validation import analyze_sensor_definition, validate_sensor_definition


def load_json(path: str) -> Any:
    """Load a JSON data file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_sensor_validation(root: str = "data/sensors") -> List[Dict[str, str]]:
    """Collect validation status for every sensor folder."""
    rows: List[Dict[str, str]] = []
    for sensor_file in sorted(Path(root).glob("*/sensor.json")):
        try:
            sensor = load_json(str(sensor_file))
            errors, warnings = analyze_sensor_definition(sensor, sensor_file)
            component = sensor.get("component", sensor_file.parent.name)
        except Exception as exc:
            sensor = {}
            component = sensor_file.parent.name
            errors = [str(exc)]
            warnings = []

        if errors:
            status = "Error"
            details = " | ".join(errors)
        elif sensor.get("enabled") is False:
            status = "Disabled"
            details = "Valid template or disabled sensor; not loaded as a supported option"
        elif warnings:
            status = "Warning"
            details = " | ".join(warnings)
        else:
            status = "OK"
            details = "Valid enabled sensor definition"

        rows.append(
            {
                "Sensor": component,
                "File": str(sensor_file),
                "Status": status,
                "Details": details,
            }
        )
    return rows


def load_sensor_definitions(root: str = "data/sensors") -> Dict[str, Dict[str, Any]]:
    """Load one sensor definition from each sensor subfolder."""
    sensors: List[Dict[str, Any]] = []
    for sensor_file in sorted(Path(root).glob("*/sensor.json")):
        sensor = load_json(str(sensor_file))
        validate_sensor_definition(sensor, sensor_file)
        if sensor.get("enabled") is False:
            continue
        sensors.append(sensor)

    sensors.sort(key=lambda item: (int(item.get("order", 999)), item["component"]))
    return {sensor["component"]: sensor for sensor in sensors}


def build_supported_sensors(sensor_library: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Build requirement-to-component mapping from sensor folders."""
    supported: Dict[str, Dict[str, str]] = {}
    for component, sensor in sensor_library.items():
        for category in sensor.get("categories", []):
            supported[category["name"]] = {
                "component": component,
                "function": category.get("function", sensor["functions"]),
                "interface": sensor.get("interface", "I2C"),
            }
    return supported


def build_sensor_keywords(sensor_library: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Build user-input keyword aliases from sensor folders."""
    keywords: Dict[str, str] = {}
    for sensor in sensor_library.values():
        for category in sensor.get("categories", []):
            requirement = category["name"]
            keywords[requirement] = requirement
            for keyword in category.get("keywords", []):
                keywords[keyword.lower()] = requirement
    return keywords


def build_requirement_groups(sensor_library: Dict[str, Dict[str, Any]]) -> List[List[str]]:
    """Build linked sensing requirement groups from sensor folders."""
    groups: List[List[str]] = []
    for sensor in sensor_library.values():
        group = sensor.get("linked_categories", [])
        if group and group not in groups:
            groups.append(group)
    return groups


def build_sensor_reference_map(
    sensor_library: Dict[str, Dict[str, Any]],
    board_template: Dict[str, Any],
) -> Dict[str, str]:
    """Build stable reference designators for all known sensor footprints."""
    refs: Dict[str, str] = {}
    template_refs = board_template.get("pcb_visual", {}).get("sensor_refs", {})
    for component, sensor in sensor_library.items():
        visual_ref = sensor.get("visual", {}).get("ref") or template_refs.get(component)
        if visual_ref:
            refs[component] = visual_ref

    used = set(refs.values())
    next_index = 3
    for component in sensor_library:
        if component in refs:
            continue
        while f"U{next_index}" in used:
            next_index += 1
        refs[component] = f"U{next_index}"
        used.add(refs[component])
    return refs
