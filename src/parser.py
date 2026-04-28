"""Controlled natural-language requirement parsing."""

from typing import Any, Dict, List


def ordered_requirements(requirements: List[str], sensor_library: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return requested sensing categories in sensor-folder order."""
    ordered: List[str] = []
    for sensor in sensor_library.values():
        for category in sensor.get("categories", []):
            name = category["name"]
            if name in requirements and name not in ordered:
                ordered.append(name)
    for requirement in requirements:
        if requirement not in ordered:
            ordered.append(requirement)
    return ordered


def parse_requirements(
    user_input: str,
    sensor_library: Dict[str, Dict[str, Any]],
    supported_sensors: Dict[str, Dict[str, str]],
    sensor_keywords: Dict[str, str],
    requirement_groups: List[List[str]],
    requirement_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Parse free-form requirements into the controlled board architecture."""
    text = user_input.lower()

    connectivity: List[str] = []
    for label, keywords in requirement_config["connectivity_keywords"].items():
        if any(keyword in text for keyword in keywords):
            connectivity.append(label)
    if not connectivity:
        connectivity = requirement_config["default_connectivity"]

    requested_sensing: List[str] = []
    for phrase, key in sensor_keywords.items():
        if phrase in text and key not in requested_sensing:
            requested_sensing.append(key)

    for group in requirement_groups:
        if any(requirement in requested_sensing for requirement in group):
            for requirement in group:
                if requirement not in requested_sensing:
                    requested_sensing.append(requirement)
    requested_sensing = ordered_requirements(requested_sensing, sensor_library)

    selected_components: List[str] = []
    for requirement in requested_sensing:
        component = supported_sensors.get(requirement, {}).get("component")
        if component and component not in selected_components:
            selected_components.append(component)

    unsupported = [kw for kw in requirement_config["unsupported_keywords"] if kw in text]

    return {
        "power_input": "USB-C 5 V power only",
        "wireless": connectivity,
        "mcu": "ESP32-WROOM-32",
        "logic_voltage": "3.3 V",
        "communication_bus": "I2C",
        "requested_sensing": requested_sensing,
        "selected_components": selected_components,
        "unsupported_requirements": unsupported,
    }
