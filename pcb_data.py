"""Data loading and validation for sensor-driven PCB generation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: str) -> Any:
    """Load a JSON data file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_sensor_definition(sensor: Dict[str, Any], source: Path) -> Tuple[List[str], List[str]]:
    """Return schema errors and warnings for a sensor definition."""
    errors: List[str] = []
    warnings: List[str] = []
    required_fields = [
        "component",
        "interface",
        "functions",
        "categories",
        "i2c_address",
        "supply",
        "current_ma",
        "footprint",
        "pins",
        "placement",
        "routing",
    ]
    missing = [field for field in required_fields if field not in sensor]
    if missing:
        errors.append(f"{source} is missing required field(s): {', '.join(missing)}")
        return errors, warnings

    if not isinstance(sensor["categories"], list) or not sensor["categories"]:
        errors.append(f"{source} must define at least one category")
    for index, category in enumerate(sensor["categories"], start=1):
        if not isinstance(category, dict):
            errors.append(f"{source} category {index} must be an object")
            continue
        for field in ("name", "function", "keywords"):
            if field not in category:
                errors.append(f"{source} category {index} is missing {field}")
        keywords = category.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            errors.append(f"{source} category {index} must include at least one keyword")

    if not isinstance(sensor["pins"], dict) or not sensor["pins"]:
        errors.append(f"{source} must define a non-empty pins object")
    else:
        for pin, net in sensor["pins"].items():
            if not isinstance(pin, str) or not isinstance(net, str):
                errors.append(f"{source} pins must map pin names to net names")

    try:
        float(sensor["current_ma"])
    except (TypeError, ValueError):
        errors.append(f"{source} current_ma must be numeric")

    interface = str(sensor.get("interface", "")).upper()
    if interface != "I2C":
        warnings.append(
            f"{source} declares interface {sensor.get('interface')}; this prototype is fully automated only for 3.3 V I2C sensors"
        )

    if isinstance(sensor.get("pins"), dict):
        nets = set(sensor["pins"].values())
        for required_net in ("3V3", "GND", "I2C_SDA", "I2C_SCL"):
            if required_net not in nets:
                warnings.append(f"{source} pins do not include required net {required_net}")

    return errors, warnings


def validate_sensor_definition(sensor: Dict[str, Any], source: Path) -> None:
    """Validate the minimum schema required for a sensor folder."""
    errors, _warnings = analyze_sensor_definition(sensor, source)
    if errors:
        raise ValueError("; ".join(errors))


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
    legacy_refs = board_template.get("pcb_visual", {}).get("sensor_refs", {})
    for component, sensor in sensor_library.items():
        visual_ref = sensor.get("visual", {}).get("ref") or legacy_refs.get(component)
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
