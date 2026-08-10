"""Optional cloud LLM assistant through the Gemini API."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .base_assistant import run_ai_requirement_assistant, validate_ai_extraction
from .ollama_assistant import extract_json_object, read_int_env
from .parser import ordered_requirements
from .provider_security import safe_provider_failure, safe_provider_failure_message


LOGGER = logging.getLogger(__name__)


GEMINI_MODEL_DEFAULT = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip() or "gemini-2.5-flash-lite"
GEMINI_TIMEOUT_SECONDS = read_int_env("GEMINI_TIMEOUT_SECONDS", 60)
GEMINI_MAX_INPUT_CHARS = read_int_env("GEMINI_MAX_INPUT_CHARS", 1200)
GEMINI_MAX_OUTPUT_TOKENS = read_int_env("GEMINI_MAX_OUTPUT_TOKENS", 350)
GEMINI_MODEL_FALLBACKS = [
    model.strip()
    for model in os.getenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash,gemini-2.0-flash-lite").split(",")
    if model.strip()
]

GEMINI_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "requested_sensing": {"type": "array", "items": {"type": "string"}},
        "selected_components": {"type": "array", "items": {"type": "string"}},
        "unsupported_requirements": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "requested_sensing",
        "selected_components",
        "unsupported_requirements",
        "confidence",
        "notes",
    ],
}


def get_gemini_api_key(secrets: Optional[Any] = None) -> str:
    """Read Gemini API key from Streamlit secrets first, then environment."""
    if secrets is not None:
        try:
            secret_value = secrets.get("GEMINI_API_KEY", "")
        except Exception:
            secret_value = ""
        if secret_value:
            return str(secret_value).strip()
        return os.getenv("GEMINI_API_KEY", "").strip()

    try:
        import streamlit as st

        secret_value = st.secrets.get("GEMINI_API_KEY", "")
        if secret_value:
            return str(secret_value).strip()
    except Exception:
        pass

    return os.getenv("GEMINI_API_KEY", "").strip()


def check_gemini_status(secrets: Optional[Any] = None, model: str = GEMINI_MODEL_DEFAULT) -> Dict[str, Any]:
    """Return non-sensitive Gemini provider status for the UI."""
    return {
        "provider": "Gemini API",
        "model": model,
        "api_key_configured": bool(get_gemini_api_key(secrets)),
        "max_input_chars": GEMINI_MAX_INPUT_CHARS,
        "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
        "fallback_models": [candidate for candidate in get_gemini_model_candidates(model) if candidate != model],
        "fallback": "Base",
    }


def get_gemini_model_candidates(model: str = GEMINI_MODEL_DEFAULT) -> List[str]:
    """Return unique Gemini model candidates from primary plus fallback models."""
    candidates: List[str] = []
    for candidate in [model] + GEMINI_MODEL_FALLBACKS:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def build_gemini_prompt(
    user_input: str,
    local_result: Dict[str, Any],
    sensor_library: Dict[str, Dict[str, Any]],
    requirement_config: Dict[str, Any],
) -> str:
    """Build a constrained prompt for Gemini requirement extraction."""
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
        "You are a requirement extraction assistant for a controlled PCB prototype.\n"
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
        "Base assistant baseline:\n"
        + json.dumps(local_result, indent=2)
        + "\n\nUser input:\n"
        + user_input[:GEMINI_MAX_INPUT_CHARS]
    )


def call_gemini_generate(
    prompt: str,
    api_key: str,
    model: str = GEMINI_MODEL_DEFAULT,
) -> Dict[str, Any]:
    """Call Gemini API and parse a JSON object response."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
            response_schema=GEMINI_RESPONSE_SCHEMA,
        ),
    )
    return extract_json_object(response.text or "{}")


def run_gemini_requirement_assistant(
    user_input: str,
    sensor_library: Dict[str, Dict[str, Any]],
    supported_sensors: Dict[str, Dict[str, str]],
    sensor_keywords: Dict[str, str],
    requirement_groups: List[List[str]],
    requirement_config: Dict[str, Any],
    api_key: str = "",
    model: str = GEMINI_MODEL_DEFAULT,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run Gemini extraction and fall back to the Base assistant on any provider issue."""
    local_parsed, local_metadata = run_ai_requirement_assistant(
        user_input,
        sensor_library,
        supported_sensors,
        sensor_keywords,
        requirement_groups,
        requirement_config,
    )
    resolved_api_key = api_key or get_gemini_api_key()
    if not resolved_api_key:
        local_parsed["ai_assistant"]["mode"] = "gemini_fallback"
        local_parsed["ai_assistant"]["notes"].insert(
            0,
            "Gemini API key was not configured; used Base assistant.",
        )
        local_metadata["mode"] = "gemini_fallback"
        local_metadata["provider"] = "Gemini API"
        local_metadata["model"] = model
        local_metadata["fallback_reason"] = "GEMINI_API_KEY missing"
        return local_parsed, local_metadata

    prompt = build_gemini_prompt(user_input, local_parsed, sensor_library, requirement_config)
    provider_failure_codes: List[str] = []
    try:
        gemini_result: Dict[str, Any] = {}
        used_model = model
        for candidate_model in get_gemini_model_candidates(model):
            try:
                gemini_result = call_gemini_generate(prompt, api_key=resolved_api_key, model=candidate_model)
                used_model = candidate_model
                break
            except Exception as exc:
                failure = safe_provider_failure("Gemini API", exc)
                provider_failure_codes.append(failure["code"])
                LOGGER.warning(
                    "Gemini requirement model %s failed (%s)",
                    candidate_model,
                    failure["code"],
                )
        else:
            raise RuntimeError(provider_failure_codes[-1] if provider_failure_codes else "provider_unavailable")

        merged_result = dict(gemini_result)
        merge_notes: List[str] = []
        if used_model != model:
            merge_notes.append(f"Gemini primary model failed; used fallback model {used_model}.")

        requested_sensing = list(gemini_result.get("requested_sensing", []))
        for requirement in local_parsed.get("requested_sensing", []):
            if requirement not in requested_sensing:
                requested_sensing.append(requirement)
                merge_notes.append(f"Preserved Base assistant sensing category missed by Gemini: {requirement}.")
        merged_result["requested_sensing"] = requested_sensing

        unsupported_requirements = list(gemini_result.get("unsupported_requirements", []))
        for unsupported in local_parsed.get("unsupported_requirements", []):
            if unsupported not in unsupported_requirements:
                unsupported_requirements.append(unsupported)
                merge_notes.append(f"Preserved unsupported request detected by Base assistant: {unsupported}.")
        merged_result["unsupported_requirements"] = unsupported_requirements

        parsed, notes = validate_ai_extraction(
            merged_result,
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

        parsed["ai_assistant"]["mode"] = "gemini"
        parsed["ai_assistant"]["model"] = used_model
        parsed["ai_assistant"]["notes"] = notes
        return parsed, {
            "used_ai": True,
            "mode": "gemini",
            "model": used_model,
            "provider": "Gemini API",
            "base_url": "Google Gemini API",
            "notes": notes,
        }
    except Exception as exc:
        if provider_failure_codes:
            failure_code = provider_failure_codes[-1]
            failure = {
                "code": failure_code,
                "message": safe_provider_failure_message("Gemini API", failure_code),
            }
        else:
            failure = safe_provider_failure("Gemini API", exc)
        local_parsed["ai_assistant"]["mode"] = "gemini_fallback"
        local_parsed["ai_assistant"]["notes"].insert(
            0,
            f"{failure['message']} Used Base assistant fallback.",
        )
        local_metadata["mode"] = "gemini_fallback"
        local_metadata["provider"] = "Gemini API"
        local_metadata["model"] = model
        local_metadata["base_url"] = "Google Gemini API"
        local_metadata["fallback_reason"] = failure["code"]
        return local_parsed, local_metadata
