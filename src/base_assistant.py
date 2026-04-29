"""Local no-cost requirement assistant with controlled validation."""

from typing import Any, Dict, List, Tuple

from .parser import ordered_requirements
from .parser import parse_requirements as rule_based_parse_requirements


LOCAL_ASSISTANT_NAME = "Local controlled assistant"

LOCAL_INTENT_ALIASES: Dict[str, List[str]] = {
    "temperature": [
        "comfort",
        "room comfort",
        "thermal comfort",
        "indoor comfort",
        "heat",
        "cold",
        "warm",
        "ambient condition",
    ],
    "humidity": [
        "comfort",
        "room comfort",
        "moisture",
        "damp",
        "dryness",
        "indoor comfort",
        "ambient condition",
    ],
    "light": [
        "brightness",
        "bright",
        "dark",
        "illumination",
        "daylight",
        "ambient light",
        "lux level",
    ],
    "air_quality": [
        "air freshness",
        "freshness",
        "stale air",
        "air quality",
        "voc",
        "gas",
        "odor",
        "smell",
        "indoor air",
    ],
    "pressure": [
        "barometer",
        "barometric",
        "weather pressure",
        "altitude",
        "elevation",
        "atmospheric pressure",
    ],
}

LOCAL_UNSUPPORTED_ALIASES: Dict[str, List[str]] = {
    "camera": ["camera", "photo", "image", "video", "vision"],
    "gps": ["gps", "location", "position tracking", "geolocation"],
    "microphone": ["microphone", "audio", "sound recording", "voice"],
    "battery": ["battery", "rechargeable", "charging", "portable power"],
    "cellular": ["cellular", "lte", "4g", "5g", "sim card"],
    "lora": ["lora", "long range radio", "lorawan"],
    "display": ["display", "screen", "oled", "lcd"],
}


def is_ai_configured() -> bool:
    """The local assistant is always available because it uses no external API."""
    return True


def find_alias_matches(text: str, aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Return alias matches found in user text."""
    matches: Dict[str, List[str]] = {}
    for target, phrases in aliases.items():
        found = [phrase for phrase in phrases if phrase in text]
        if found:
            matches[target] = found
    return matches


def validate_ai_extraction(
    ai_result: Dict[str, Any],
    rule_based_result: Dict[str, Any],
    sensor_library: Dict[str, Dict[str, Any]],
    supported_sensors: Dict[str, Dict[str, str]],
    requirement_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate and reconcile assistant output with the controlled architecture."""
    notes = list(ai_result.get("notes", []))
    supported_requirements = set(supported_sensors)
    supported_components = set(sensor_library)
    unsupported_keywords = set(requirement_config["unsupported_keywords"])

    requested_sensing: List[str] = []
    for requirement in ai_result.get("requested_sensing", []):
        if requirement in supported_requirements and requirement not in requested_sensing:
            requested_sensing.append(requirement)
        else:
            notes.append(f"Ignored unsupported sensing category from assistant output: {requirement}")

    selected_components: List[str] = []
    for requirement in requested_sensing:
        component = supported_sensors.get(requirement, {}).get("component")
        if component and component not in selected_components:
            selected_components.append(component)

    for component in ai_result.get("selected_components", []):
        if component not in supported_components:
            notes.append(f"Ignored unsupported component from assistant output: {component}")
        elif component not in selected_components:
            notes.append(f"Assistant selected {component}, but no validated sensing category required it; ignored.")

    unsupported_requirements: List[str] = []
    combined_unsupported = list(rule_based_result.get("unsupported_requirements", [])) + list(
        ai_result.get("unsupported_requirements", [])
    )
    for item in combined_unsupported:
        if item in unsupported_keywords and item not in unsupported_requirements:
            unsupported_requirements.append(item)

    confidence = ai_result.get("confidence", "low")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
        notes.append("Assistant confidence value was invalid and was reset to low.")

    parsed = dict(rule_based_result)
    parsed["requested_sensing"] = requested_sensing
    parsed["selected_components"] = selected_components
    parsed["unsupported_requirements"] = unsupported_requirements
    parsed["ai_assistant"] = {
        "enabled": True,
        "mode": "local",
        "confidence": confidence,
        "notes": notes,
    }
    return parsed, notes


def run_ai_requirement_assistant(
    user_input: str,
    sensor_library: Dict[str, Dict[str, Any]],
    supported_sensors: Dict[str, Dict[str, str]],
    sensor_keywords: Dict[str, str],
    requirement_groups: List[List[str]],
    requirement_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run the local assistant and return a validated parsed requirement."""
    rule_based_result = rule_based_parse_requirements(
        user_input,
        sensor_library,
        supported_sensors,
        sensor_keywords,
        requirement_groups,
        requirement_config,
    )
    text = user_input.lower()
    intent_matches = find_alias_matches(text, LOCAL_INTENT_ALIASES)
    unsupported_matches = find_alias_matches(text, LOCAL_UNSUPPORTED_ALIASES)

    requested_sensing = list(rule_based_result["requested_sensing"])
    notes: List[str] = []
    for requirement, phrases in intent_matches.items():
        if requirement in supported_sensors and requirement not in requested_sensing:
            requested_sensing.append(requirement)
            notes.append(f"Mapped phrase '{phrases[0]}' to {requirement}.")

    for group in requirement_groups:
        if any(requirement in requested_sensing for requirement in group):
            for requirement in group:
                if requirement not in requested_sensing:
                    requested_sensing.append(requirement)
                    notes.append(f"Added linked sensing requirement {requirement}.")

    requested_sensing = ordered_requirements(requested_sensing, sensor_library)
    selected_components: List[str] = []
    for requirement in requested_sensing:
        component = supported_sensors.get(requirement, {}).get("component")
        if component and component not in selected_components:
            selected_components.append(component)

    unsupported_requirements = list(rule_based_result["unsupported_requirements"])
    for unsupported, phrases in unsupported_matches.items():
        if unsupported in requirement_config["unsupported_keywords"] and unsupported not in unsupported_requirements:
            unsupported_requirements.append(unsupported)
            notes.append(f"Detected unsupported request from phrase '{phrases[0]}'.")

    if notes:
        confidence = "medium"
    elif requested_sensing:
        confidence = "high"
        notes.append("Used direct supported sensor keywords from the rule-based parser.")
    else:
        confidence = "low"
        notes.append("No supported sensing request was detected.")

    local_result = {
        "requested_sensing": requested_sensing,
        "selected_components": selected_components,
        "unsupported_requirements": unsupported_requirements,
        "confidence": confidence,
        "notes": notes,
    }
    parsed, validated_notes = validate_ai_extraction(
        local_result,
        rule_based_result,
        sensor_library,
        supported_sensors,
        requirement_config,
    )
    return parsed, {
        "used_ai": True,
        "mode": "local",
        "model": LOCAL_ASSISTANT_NAME,
        "notes": validated_notes,
    }
