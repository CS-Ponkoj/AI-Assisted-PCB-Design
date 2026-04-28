"""Sensor plugin validation helpers."""

from pathlib import Path
from typing import Any, Dict, List, Tuple


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
