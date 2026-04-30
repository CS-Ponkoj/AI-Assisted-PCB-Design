"""Grounded review copilot for generated PCB handoff packages."""

import hashlib
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional

from .gemini_assistant import GEMINI_MODEL_DEFAULT, get_gemini_api_key, get_gemini_model_candidates


REVIEW_COPILOT_MODEL_DEFAULT = (
    os.getenv("REVIEW_COPILOT_MODEL", GEMINI_MODEL_DEFAULT).strip() or GEMINI_MODEL_DEFAULT
)


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


def extract_json_object(text: str) -> Dict[str, Any]:
    """Parse a JSON object from a model response."""
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


REVIEW_COPILOT_MAX_CONTEXT_CHARS = read_int_env("REVIEW_COPILOT_MAX_CONTEXT_CHARS", 9000)
REVIEW_COPILOT_MAX_OUTPUT_TOKENS = read_int_env("REVIEW_COPILOT_MAX_OUTPUT_TOKENS", 550)

SOURCE_SCOPE = "Scope Guardrail"
SOURCE_PARSED = "Parsed Requirement"
SOURCE_SUMMARY = "Project Summary"
SOURCE_ASSUMPTIONS = "Design Assumptions"
SOURCE_BOM = "BOM"
SOURCE_PIN_MAP = "Pin Map"
SOURCE_NETLIST = "Netlist"
SOURCE_POWER = "Power Budget"
SOURCE_READINESS = "Readiness Review"
SOURCE_LAYOUT = "Layout Guidance"
SOURCE_FAB = "Fabrication Checklist"
SOURCE_BRINGUP = "Bring-Up Checklist"
SOURCE_SCHEMATIC = "Schematic Summary"

KNOWN_SOURCES = {
    SOURCE_SCOPE,
    SOURCE_PARSED,
    SOURCE_SUMMARY,
    SOURCE_ASSUMPTIONS,
    SOURCE_BOM,
    SOURCE_PIN_MAP,
    SOURCE_NETLIST,
    SOURCE_POWER,
    SOURCE_READINESS,
    SOURCE_LAYOUT,
    SOURCE_FAB,
    SOURCE_BRINGUP,
    SOURCE_SCHEMATIC,
}

REVIEW_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "guardrail_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "sources", "confidence", "guardrail_notes"],
}


def copy_rows(rows: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Return a string-normalized copy of table rows so callers cannot mutate the package."""
    copied: List[Dict[str, str]] = []
    for row in rows or []:
        copied.append({str(key): str(value) for key, value in row.items()})
    return copied


def build_review_context(package: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact review context from an already-generated PCB handoff package."""
    parsed = dict(package.get("parsed", {}))
    readiness = package.get("readiness_review") or {}
    summary_rows = copy_rows(package.get("summary", []))
    original_requirement = ""
    for row in summary_rows:
        if row.get("Item") == "Original requirement":
            original_requirement = row.get("Decision", "")
            break

    return {
        "scope": {
            "fixed_architecture": "USB-C 5 V input -> 3.3 V regulator -> ESP32-WROOM-32 -> shared I2C sensor bus",
            "allowed_behavior": "Review, explain, summarize, and highlight risks in the generated handoff only.",
            "blocked_behavior": "Do not invent hardware, silently change the design, or claim fabrication signoff.",
        },
        "requirement": {
            "original": original_requirement,
            "requested_sensing": list(parsed.get("requested_sensing", [])),
            "selected_components": list(parsed.get("selected_components", [])),
            "unsupported_requirements": list(parsed.get("unsupported_requirements", [])),
            "wireless": list(parsed.get("wireless", [])),
            "power_input": str(parsed.get("power_input", "")),
            "mcu": str(parsed.get("mcu", "")),
            "logic_voltage": str(parsed.get("logic_voltage", "")),
            "communication_bus": str(parsed.get("communication_bus", "")),
        },
        "sensor_refs": dict(package.get("sensor_refs", {})),
        "summary": summary_rows,
        "assumptions": copy_rows(package.get("assumptions", [])),
        "io_table": copy_rows(package.get("io_table", [])),
        "bom": copy_rows(package.get("bom", [])),
        "pin_map": copy_rows(package.get("pin_map", [])),
        "netlist": copy_rows(package.get("netlist", [])),
        "power_budget": copy_rows(package.get("power_budget", [])),
        "layout_guidance": copy_rows(package.get("layout_guidance", [])),
        "fabrication_checklist": copy_rows(package.get("fabrication_checklist", [])),
        "bringup_checklist": copy_rows(package.get("bringup_checklist", [])),
        "schematic_summary": [str(line) for line in package.get("schematic_summary", [])],
        "readiness": {
            "status": str(readiness.get("status", "Unknown")),
            "blockers": [str(item) for item in readiness.get("blockers", [])],
            "review_items": [str(item) for item in readiness.get("review_items", [])],
            "passed": [str(item) for item in readiness.get("passed", [])],
            "rows": copy_rows(readiness.get("rows", [])),
        },
    }


def review_context_signature(context: Dict[str, Any]) -> str:
    """Return a stable short signature for resetting chat when the design changes."""
    payload = {
        "requirement": context.get("requirement", {}),
        "sensor_refs": context.get("sensor_refs", {}),
        "readiness": context.get("readiness", {}).get("status", ""),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def response(
    answer: str,
    sources: List[str],
    confidence: str = "medium",
    mode: str = "local",
    model: str = "",
    guardrail_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a normalized copilot response."""
    clean_sources = [source for source in sources if source in KNOWN_SOURCES]
    if not clean_sources:
        clean_sources = [SOURCE_SCOPE]
    clean_confidence = confidence if confidence in {"high", "medium", "low"} else "low"
    return {
        "answer": answer.strip(),
        "sources": clean_sources,
        "confidence": clean_confidence,
        "mode": mode,
        "model": model,
        "guardrail_notes": list(guardrail_notes or []),
    }


def format_sources(sources: List[str]) -> str:
    """Format source labels for display under an answer."""
    return "Based on: " + ", ".join(sources)


def row_contains(row: Dict[str, str], terms: Iterable[str]) -> bool:
    haystack = " ".join(row.values()).lower()
    return any(term.lower() in haystack for term in terms)


def find_rows(rows: List[Dict[str, str]], terms: Iterable[str], limit: int = 5) -> List[Dict[str, str]]:
    """Find rows that mention any term."""
    matches: List[Dict[str, str]] = []
    for row in rows:
        if row_contains(row, terms):
            matches.append(row)
        if len(matches) >= limit:
            break
    return matches


def bullet_lines(items: Iterable[str], limit: int = 6) -> List[str]:
    """Return a compact bullet list without letting long tables overwhelm the chat panel."""
    lines: List[str] = []
    for item in items:
        if item:
            lines.append(f"- {item}")
        if len(lines) >= limit:
            break
    return lines


def parse_ma(value: str) -> Optional[float]:
    """Extract the first mA number from a power-budget cell."""
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*mA", value)
    if not match:
        return None
    return float(match.group(1))


def selected_component_label(context: Dict[str, Any], component: str) -> str:
    """Format a selected component with its reference designator when available."""
    ref = context.get("sensor_refs", {}).get(component, "")
    return f"{ref} {component}".strip()


def answer_selected_components(context: Dict[str, Any]) -> Dict[str, Any]:
    requirement = context["requirement"]
    selected = requirement["selected_components"]
    requested = requirement["requested_sensing"]
    if not selected:
        return response(
            "No supported sensor is currently selected. The readiness review blocks this handoff until the requirement includes at least one supported sensing function.",
            [SOURCE_PARSED, SOURCE_READINESS],
            confidence="high",
        )

    selected_text = ", ".join(selected_component_label(context, component) for component in selected)
    requested_text = ", ".join(requested) if requested else "the supported sensing categories detected in the request"
    answer = (
        f"The generated handoff populates {selected_text}. These parts are tied to the requested sensing scope: "
        f"{requested_text}. The copilot is reviewing that existing selection; it is not changing the board."
    )
    return response(answer, [SOURCE_PARSED, SOURCE_BOM], confidence="high")


def answer_power_budget(context: Dict[str, Any]) -> Dict[str, Any]:
    rows = context["power_budget"]
    if not rows:
        return response("No power-budget rows are available in this handoff.", [SOURCE_POWER], confidence="low")

    largest_row: Optional[Dict[str, str]] = None
    largest_ma = -1.0
    regulator_row = ""
    total_load_text = ""
    sensor_lines: List[str] = []
    for row in rows:
        current_text = row.get("Estimated current", "")
        current_ma = parse_ma(current_text)
        block = row.get("Block", "")
        is_summary_row = block in {"3.3 V regulator requirement", "Thermal check"}
        if current_ma is not None and not is_summary_row and current_ma > largest_ma:
            largest_ma = current_ma
            largest_row = row
        if block == "3.3 V regulator requirement":
            total_load_text = current_text
            regulator_row = f"{current_text}; {row.get('Notes', '')}"
        elif block in context["requirement"]["selected_components"]:
            sensor_lines.append(f"{row.get('Block')}: {current_text}")

    lines = []
    if largest_row:
        lines.append(
            f"The largest individual load is {largest_row.get('Block')} at {largest_row.get('Estimated current')}."
        )
    if total_load_text:
        lines.append(f"The total estimated 3.3 V load is {total_load_text}.")
    if regulator_row:
        lines.append(f"The regulator summary says: {regulator_row}")
    if sensor_lines:
        lines.append("Selected sensor current rows: " + "; ".join(sensor_lines) + ".")
    lines.append("This remains an estimate; layout thermal review and the selected regulator datasheet still matter before fabrication.")
    return response(" ".join(lines), [SOURCE_POWER, SOURCE_READINESS], confidence="high")


def answer_risks(context: Dict[str, Any]) -> Dict[str, Any]:
    readiness = context["readiness"]
    lines = [f"Readiness status: {readiness['status']}."]
    blockers = bullet_lines(readiness.get("blockers", []), limit=4)
    review_items = bullet_lines(readiness.get("review_items", []), limit=4)
    if blockers:
        lines.append("Blockers:\n" + "\n".join(blockers))
    if review_items:
        lines.append("Needs review:\n" + "\n".join(review_items))
    if not blockers and not review_items:
        lines.append("No blockers or review items are listed, but fabrication still depends on DRC, footprint checks, antenna keepout, and regulator datasheet review.")

    fab_checks = [
        f"{row.get('Check')}: {row.get('Acceptance')}"
        for row in context["fabrication_checklist"][:3]
    ]
    if fab_checks:
        lines.append("Top fabrication checks:\n" + "\n".join(bullet_lines(fab_checks, limit=3)))
    return response("\n\n".join(lines), [SOURCE_READINESS, SOURCE_FAB, SOURCE_LAYOUT], confidence="high")


def answer_bringup(context: Dict[str, Any]) -> Dict[str, Any]:
    steps = [
        f"{row.get('Step')}: {row.get('Expected result')}"
        for row in context["bringup_checklist"]
        if row.get("Step")
    ]
    if not steps:
        return response("No bring-up checklist rows are available in this handoff.", [SOURCE_BRINGUP], confidence="low")
    answer = "Use this bring-up order:\n" + "\n".join(bullet_lines(steps, limit=8))
    return response(answer, [SOURCE_BRINGUP, SOURCE_POWER], confidence="high")


def answer_nets(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    normalized = question.lower()
    net_terms = ["i2c_sda", "i2c_scl", "i2c", "sda", "scl", "3v3", "vbus", "vbus_5v", "gnd", "ground", "reset", "status"]
    query_terms = [term for term in net_terms if term in normalized]
    if "i2c" in normalized:
        query_terms.extend(["I2C_SDA", "I2C_SCL"])
    if not query_terms:
        query_terms = ["I2C_SDA", "I2C_SCL", "3V3", "GND"]
    rows = find_rows(context["netlist"], query_terms, limit=5)
    if not rows:
        return response("I could not find a matching net row in the generated netlist.", [SOURCE_NETLIST], confidence="low")
    lines = []
    for row in rows:
        lines.append(
            f"{row.get('Net')}: {row.get('Connected pins')} ({row.get('Voltage')}). {row.get('Routing / PCB note')}"
        )
    return response("\n".join(bullet_lines(lines, limit=5)), [SOURCE_NETLIST, SOURCE_PIN_MAP], confidence="high")


def answer_dnp(context: Dict[str, Any]) -> Dict[str, Any]:
    selected = context["requirement"]["selected_components"]
    selected_text = ", ".join(selected) if selected else "none"
    answer = (
        "DNP means 'do not populate.' In this app, selected sensors are assembled for the current request, "
        f"while optional footprint choices are visual review aids for the shared prototype board. Current selected sensors: {selected_text}."
    )
    return response(answer, [SOURCE_SCOPE, SOURCE_PARSED, SOURCE_BOM], confidence="high")


def answer_fabrication(context: Dict[str, Any]) -> Dict[str, Any]:
    readiness = context["readiness"]
    checks = [
        f"{row.get('Check')}: {row.get('Acceptance')}"
        for row in context["fabrication_checklist"]
        if row.get("Check")
    ]
    lines = [f"The generated readiness gate is {readiness['status']}."]
    if readiness.get("blockers"):
        lines.append("Do not treat this as fabrication-ready while blockers remain:\n" + "\n".join(bullet_lines(readiness["blockers"], limit=4)))
    elif readiness.get("review_items"):
        lines.append("Review these before fabrication:\n" + "\n".join(bullet_lines(readiness["review_items"], limit=4)))
    else:
        lines.append("No readiness blockers are listed, but this prototype still needs CAD DRC, footprint verification, and datasheet checks.")
    if checks:
        lines.append("Required fabrication checks:\n" + "\n".join(bullet_lines(checks, limit=5)))
    return response("\n\n".join(lines), [SOURCE_READINESS, SOURCE_FAB], confidence="high")


def answer_beginner_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    req = context["requirement"]
    selected = req["selected_components"]
    sensors = ", ".join(selected) if selected else "no supported sensors yet"
    unsupported = ", ".join(req["unsupported_requirements"]) or "none"
    answer = (
        "This handoff is for a small ESP32 sensor board powered from USB-C. "
        "USB-C provides 5 V, the regulator makes 3.3 V, and the ESP32 talks to the sensors over I2C. "
        f"The selected sensor parts are {sensors}. Unsupported requests excluded from this design: {unsupported}. "
        f"The current readiness result is {context['readiness']['status']}."
    )
    return response(answer, [SOURCE_SUMMARY, SOURCE_PARSED, SOURCE_READINESS], confidence="high")


def answer_reviewer_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    selected = context["requirement"]["selected_components"]
    selected_text = ", ".join(selected_component_label(context, component) for component in selected) or "none"
    net_rows = find_rows(context["netlist"], ["VBUS_5V", "3V3", "I2C_SDA", "I2C_SCL"], limit=4)
    net_text = "; ".join(row.get("Net", "") for row in net_rows)
    readiness = context["readiness"]
    risk_count = len(readiness.get("blockers", [])) + len(readiness.get("review_items", []))
    answer = (
        f"Reviewer snapshot: selected sensors are {selected_text}; readiness is {readiness['status']} with {risk_count} open blocker/review item(s). "
        f"Key nets to inspect are {net_text or 'listed in the netlist'}. Prioritize antenna keepout, USB-C sink wiring, regulator footprint/thermal margin, I2C routing, and any readiness items."
    )
    return response(answer, [SOURCE_BOM, SOURCE_NETLIST, SOURCE_READINESS, SOURCE_LAYOUT], confidence="high")


def answer_change_impact(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    selected = context["requirement"]["selected_components"]
    mentioned = [component for component in selected if component.lower() in question.lower()]
    if not mentioned and "light" in question.lower():
        mentioned = [component for component in selected if component == "BH1750"]
    if not mentioned and ("temperature" in question.lower() or "humidity" in question.lower()):
        mentioned = [component for component in selected if component == "AHT20"]
    if not mentioned and "air" in question.lower():
        mentioned = [component for component in selected if component == "SGP30"]
    if not mentioned and "pressure" in question.lower():
        mentioned = [component for component in selected if component == "BMP280"]

    if mentioned:
        component = mentioned[0]
        rows = find_rows(context["bom"], [component], limit=3) + find_rows(context["pin_map"], [component], limit=3)
        row_count = len(rows)
        answer = (
            f"I can explain the impact, but I will not mutate the current handoff. Removing {component} would affect its BOM, pin-map, layout, power-budget, and bring-up rows "
            f"({row_count} directly matched row(s) in BOM/pin map). Generate a new requirement without that sensing function to create a controlled replacement handoff."
        )
        return response(answer, [SOURCE_SCOPE, SOURCE_BOM, SOURCE_PIN_MAP, SOURCE_POWER], confidence="medium")

    answer = (
        "I can review possible impact, but I cannot change this generated handoff from the copilot panel. "
        "To add, remove, or replace hardware, regenerate the design from a revised requirement so the parser, validation, readiness review, visual, and exports stay consistent."
    )
    return response(answer, [SOURCE_SCOPE, SOURCE_PARSED, SOURCE_READINESS], confidence="high")


def answer_general(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    unsupported = context["requirement"]["unsupported_requirements"]
    if unsupported and any(item in question.lower() for item in unsupported):
        return response(
            "That request is listed as unsupported in the generated requirement. It was intentionally excluded rather than turned into imaginary hardware.",
            [SOURCE_PARSED, SOURCE_READINESS, SOURCE_SCOPE],
            confidence="high",
        )
    return answer_beginner_summary(context)


def deterministic_review_answer(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Answer common review questions using only deterministic package data."""
    normalized = question.strip().lower()
    if not normalized:
        return response(
            "Ask a question about the generated handoff, such as risks, power budget, bring-up, selected sensors, or a specific net.",
            [SOURCE_SCOPE],
            confidence="high",
        )

    change_terms = [" add ", " remove ", " replace ", " switch ", " change ", " modify ", " redesign ", " upgrade "]
    padded = f" {normalized} "
    if any(term in padded for term in change_terms):
        return answer_change_impact(question, context)
    if any(term in normalized for term in ["risk", "blocked", "blocker", "review item", "problem", "issue"]):
        return answer_risks(context)
    if any(term in normalized for term in ["bring-up", "bringup", "test plan", "first check", "verify first"]):
        return answer_bringup(context)
    if any(term in normalized for term in ["power", "current", "load", "regulator", "thermal", "margin"]):
        return answer_power_budget(context)
    if any(term in normalized for term in ["net", "i2c", "sda", "scl", "3v3", "vbus", "ground", "gnd"]):
        return answer_nets(question, context)
    if any(term in normalized for term in ["dnp", "footprint option", "populate", "populated"]):
        return answer_dnp(context)
    if any(term in normalized for term in ["fabrication", "fabricate", "build", "safe", "release"]):
        return answer_fabrication(context)
    if any(term in normalized for term in ["reviewer", "pcb designer", "designer review"]):
        return answer_reviewer_summary(context)
    if any(term in normalized for term in ["beginner", "new to", "simple", "explain this design"]):
        return answer_beginner_summary(context)
    if any(term in normalized for term in ["why", "selected", "choose", "component", "sensor", "bom", "part"]):
        return answer_selected_components(context)
    return answer_general(question, context)


def build_gemini_review_prompt(question: str, context: Dict[str, Any]) -> str:
    """Build a constrained prompt for source-grounded review answers."""
    context_json = json.dumps(context, indent=2)[:REVIEW_COPILOT_MAX_CONTEXT_CHARS]
    return (
        "You are PCB Review Copilot for a controlled ESP32 sensor-board prototype.\n"
        "Answer only from the provided generated handoff context. Do not invent parts, nets, sensor capabilities, or fabrication signoff.\n"
        "You may explain, summarize, identify risks, and state what data is missing. You must not modify the design.\n"
        "If the user asks to change hardware, explain the impact and say they must regenerate from a revised requirement.\n"
        "Return JSON only with this shape: answer, sources, confidence, guardrail_notes.\n"
        "The sources list may only use these labels: "
        + ", ".join(sorted(KNOWN_SOURCES))
        + ".\n\nGenerated handoff context:\n"
        + context_json
        + "\n\nUser question:\n"
        + question[:1200]
    )


def call_gemini_review_generate(prompt: str, api_key: str, model: str = REVIEW_COPILOT_MODEL_DEFAULT) -> Dict[str, Any]:
    """Call Gemini for a review answer and parse the JSON object response."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response_obj = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=REVIEW_COPILOT_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
            response_schema=REVIEW_RESPONSE_SCHEMA,
        ),
    )
    return extract_json_object(response_obj.text or "{}")


def gemini_unavailable_response(reason: str, model: str = REVIEW_COPILOT_MODEL_DEFAULT) -> Dict[str, Any]:
    """Return a Gemini unavailable message for callers that do not apply local review fallback."""
    return response(
        "Gemini Review Copilot is unavailable right now. The generated PCB handoff is still available, "
        "but copilot answers require Gemini to be configured and reachable.",
        [SOURCE_SCOPE],
        confidence="low",
        mode="gemini_unavailable",
        model=model,
        guardrail_notes=[reason],
    )


def validate_gemini_review_response(
    gemini_result: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    """Keep Gemini review responses inside the same response contract as local answers."""
    answer = str(gemini_result.get("answer", "")).strip()
    if not answer:
        return gemini_unavailable_response(
            "Gemini returned an empty review answer.",
            model=model,
        )

    sources = [
        str(source)
        for source in gemini_result.get("sources", [])
        if str(source) in KNOWN_SOURCES
    ]
    if not sources:
        sources = [SOURCE_SCOPE]
    guardrail_notes = [str(note) for note in gemini_result.get("guardrail_notes", [])]
    guardrail_notes.append("Gemini response was constrained to the generated handoff context.")
    return response(
        answer,
        sources,
        confidence=str(gemini_result.get("confidence", "medium")),
        mode="gemini",
        model=model,
        guardrail_notes=guardrail_notes,
    )


def run_gemini_review_copilot(
    question: str,
    context: Dict[str, Any],
    api_key: str = "",
    model: str = REVIEW_COPILOT_MODEL_DEFAULT,
) -> Dict[str, Any]:
    """Run the Gemini review copilot."""
    resolved_api_key = api_key or get_gemini_api_key()
    if not resolved_api_key:
        return gemini_unavailable_response(
            "Gemini API key was not configured.",
            model=model,
        )

    prompt = build_gemini_review_prompt(question, context)
    provider_errors: List[str] = []
    for candidate_model in get_gemini_model_candidates(model):
        try:
            gemini_result = call_gemini_review_generate(prompt, api_key=resolved_api_key, model=candidate_model)
            return validate_gemini_review_response(gemini_result, candidate_model)
        except Exception as exc:
            provider_errors.append(f"{candidate_model}: {exc}")

    return gemini_unavailable_response(
        "Gemini review was busy, unavailable, or returned invalid JSON. " + "; ".join(provider_errors),
        model=model,
    )


def run_review_copilot(
    question: str,
    package: Dict[str, Any],
    use_gemini: bool = False,
    api_key: str = "",
    model: str = REVIEW_COPILOT_MODEL_DEFAULT,
) -> Dict[str, Any]:
    """Answer a review question about an already-generated PCB handoff package."""
    context = build_review_context(package)
    if use_gemini:
        return run_gemini_review_copilot(question, context, api_key=api_key, model=model)
    return deterministic_review_answer(question, context)
