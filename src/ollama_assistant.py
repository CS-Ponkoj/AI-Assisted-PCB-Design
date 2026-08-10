"""Optional local LLM assistant through Ollama."""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Tuple

from .base_assistant import run_ai_requirement_assistant, validate_ai_extraction
from .parser import ordered_requirements
from .provider_security import safe_endpoint_for_display, safe_provider_failure


LOGGER = logging.getLogger(__name__)


OLLAMA_MODEL_DEFAULT = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip() or "qwen2.5:3b"
OLLAMA_URL_DEFAULT = os.getenv("OLLAMA_URL", "http://localhost:11434").strip() or "http://localhost:11434"
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_AUTH_HEADER = os.getenv("OLLAMA_AUTH_HEADER", "").strip()


def read_int_env(name: str, default: int) -> int:
    """Read a positive integer environment variable without failing at import time."""
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


OLLAMA_TIMEOUT_SECONDS = read_int_env("OLLAMA_TIMEOUT_SECONDS", 120)


def get_ollama_provider_label(base_url: str = OLLAMA_URL_DEFAULT) -> str:
    """Return a readable label for the configured Ollama provider."""
    parsed_url = urllib.parse.urlparse(base_url)
    host = parsed_url.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "Local Ollama"
    return "Remote Ollama"


def build_ollama_headers(include_json: bool = False) -> Dict[str, str]:
    """Build request headers for local or hosted Ollama-compatible servers."""
    headers: Dict[str, str] = {}
    if include_json:
        headers["Content-Type"] = "application/json"

    if OLLAMA_AUTH_HEADER:
        if ":" in OLLAMA_AUTH_HEADER:
            name, value = OLLAMA_AUTH_HEADER.split(":", 1)
            headers[name.strip()] = value.strip()
        else:
            headers["Authorization"] = OLLAMA_AUTH_HEADER
    elif OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    return headers


def check_ollama_status(
    model: str = OLLAMA_MODEL_DEFAULT,
    base_url: str = OLLAMA_URL_DEFAULT,
    timeout: int = 5,
) -> Dict[str, Any]:
    """Check whether the configured Ollama server is reachable and has the model."""
    status: Dict[str, Any] = {
        "provider": get_ollama_provider_label(base_url),
        "base_url": safe_endpoint_for_display(base_url),
        "model": model,
        "reachable": False,
        "model_available": False,
        "models": [],
        "auth_configured": bool(OLLAMA_API_KEY or OLLAMA_AUTH_HEADER),
        "error": "",
    }
    try:
        request = urllib.request.Request(
            url=base_url.rstrip("/") + "/api/tags",
            headers=build_ollama_headers(),
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        models = [item.get("name", "") for item in body.get("models", []) if item.get("name")]
        status["reachable"] = True
        status["models"] = models
        status["model_available"] = model in models
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        failure = safe_provider_failure("Ollama", exc)
        status["error"] = failure["message"]
        status["error_code"] = failure["code"]
        LOGGER.warning("Ollama status check failed (%s)", failure["code"])
    return status


def build_ollama_prompt(
    user_input: str,
    rule_based_result: Dict[str, Any],
    sensor_library: Dict[str, Dict[str, Any]],
    requirement_config: Dict[str, Any],
) -> str:
    """Build a constrained prompt for local LLM requirement extraction."""
    supported_lines: List[str] = []
    for component, sensor in sensor_library.items():
        categories = ", ".join(category["name"] for category in sensor.get("categories", []))
        keywords = ", ".join(
            keyword
            for category in sensor.get("categories", [])
            for keyword in category.get("keywords", [])
        )
        linked = ", ".join(sensor.get("linked_categories", [])) or "none"
        supported_lines.append(
            f"- {component}: categories={categories}; keywords={keywords}; linked_categories={linked}"
        )

    return (
        "You are a local requirement extraction assistant for a controlled PCB prototype.\n"
        "Return JSON only. Do not use Markdown. Do not invent hardware.\n"
        "Only use categories and components from the supported list.\n\n"
        "Fixed architecture: USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus.\n\n"
        "Supported sensors:\n"
        + "\n".join(supported_lines)
        + "\n\nUnsupported keywords:\n"
        + ", ".join(requirement_config["unsupported_keywords"])
        + "\n\nReturn exactly this JSON shape:\n"
        '{\n'
        '  "requested_sensing": ["temperature"],\n'
        '  "selected_components": ["AHT20"],\n'
        '  "unsupported_requirements": [],\n'
        '  "confidence": "high",\n'
        '  "notes": ["short explanation"]\n'
        '}\n\n'
        "Rule-based baseline:\n"
        + json.dumps(rule_based_result, indent=2)
        + "\n\nUser input:\n"
        + user_input
    )


def extract_json_object(text: str) -> Dict[str, Any]:
    """Parse a JSON object from an LLM response."""
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def call_ollama_generate(
    prompt: str,
    model: str = OLLAMA_MODEL_DEFAULT,
    base_url: str = OLLAMA_URL_DEFAULT,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Call Ollama's local generate API and parse its response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 350,
        },
    }
    request = urllib.request.Request(
        url=base_url.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers=build_ollama_headers(include_json=True),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_body = json.loads(response.read().decode("utf-8"))
    return extract_json_object(response_body.get("response", "{}"))


def run_ollama_requirement_assistant(
    user_input: str,
    sensor_library: Dict[str, Dict[str, Any]],
    supported_sensors: Dict[str, Dict[str, str]],
    sensor_keywords: Dict[str, str],
    requirement_groups: List[List[str]],
    requirement_config: Dict[str, Any],
    model: str = OLLAMA_MODEL_DEFAULT,
    base_url: str = OLLAMA_URL_DEFAULT,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run Ollama extraction and fall back to the base assistant if unavailable."""
    local_parsed, _ = run_ai_requirement_assistant(
        user_input,
        sensor_library,
        supported_sensors,
        sensor_keywords,
        requirement_groups,
        requirement_config,
    )
    prompt = build_ollama_prompt(user_input, local_parsed, sensor_library, requirement_config)

    try:
        llm_result = call_ollama_generate(prompt, model=model, base_url=base_url)
        merged_llm_result = dict(llm_result)
        merge_notes: List[str] = []

        requested_sensing = list(llm_result.get("requested_sensing", []))
        for requirement in local_parsed.get("requested_sensing", []):
            if requirement not in requested_sensing:
                requested_sensing.append(requirement)
                merge_notes.append(f"Preserved Base assistant sensing category missed by LLM: {requirement}.")
        merged_llm_result["requested_sensing"] = requested_sensing

        unsupported_requirements = list(llm_result.get("unsupported_requirements", []))
        for unsupported in local_parsed.get("unsupported_requirements", []):
            if unsupported not in unsupported_requirements:
                unsupported_requirements.append(unsupported)
                merge_notes.append(f"Preserved unsupported request detected by Base assistant: {unsupported}.")
        merged_llm_result["unsupported_requirements"] = unsupported_requirements

        parsed, notes = validate_ai_extraction(
            merged_llm_result,
            local_parsed,
            sensor_library,
            supported_sensors,
            requirement_config,
        )
        notes.extend(merge_notes)

        parsed["requested_sensing"] = ordered_requirements(parsed["requested_sensing"], sensor_library)
        selected_components: List[str] = []
        for requirement in parsed["requested_sensing"]:
            component = supported_sensors.get(requirement, {}).get("component")
            if component and component not in selected_components:
                selected_components.append(component)
        parsed["selected_components"] = selected_components

        parsed["ai_assistant"]["mode"] = "ollama"
        parsed["ai_assistant"]["model"] = model
        parsed["ai_assistant"]["notes"] = notes
        return parsed, {
            "used_ai": True,
            "mode": "ollama",
            "model": model,
            "provider": get_ollama_provider_label(base_url),
            "base_url": base_url,
            "notes": notes,
        }
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        failure = safe_provider_failure("Ollama", exc)
        parsed, metadata = run_ai_requirement_assistant(
            user_input,
            sensor_library,
            supported_sensors,
            sensor_keywords,
            requirement_groups,
            requirement_config,
        )
        parsed["ai_assistant"]["mode"] = "local_fallback"
        parsed["ai_assistant"]["notes"].insert(
            0,
            f"{failure['message']} Used Base assistant fallback.",
        )
        metadata["mode"] = "local_fallback"
        metadata["provider"] = get_ollama_provider_label(base_url)
        metadata["base_url"] = safe_endpoint_for_display(base_url)
        metadata["fallback_reason"] = failure["code"]
        LOGGER.warning("Ollama generation failed (%s)", failure["code"])
        return parsed, metadata
