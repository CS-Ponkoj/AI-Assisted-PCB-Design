"""Safe provider diagnostics that never expose exception text or credentials."""

import json
from typing import Dict
from urllib.parse import urlsplit, urlunsplit


def classify_provider_failure(exc: Exception) -> str:
    """Return a stable, non-sensitive provider failure category."""
    exception_name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or "timeout" in exception_name:
        return "timeout"
    if isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
        return "invalid_response"
    if isinstance(exc, OSError) or "connection" in exception_name:
        return "unreachable"
    return "provider_unavailable"


def safe_provider_failure_message(provider: str, failure_code: str) -> str:
    """Build a user-safe provider message from a known failure category."""
    messages = {
        "timeout": f"{provider} timed out.",
        "invalid_response": f"{provider} returned an invalid response.",
        "unreachable": f"{provider} could not be reached.",
        "provider_unavailable": f"{provider} is unavailable.",
    }
    return messages.get(failure_code, messages["provider_unavailable"])


def safe_provider_failure(provider: str, exc: Exception) -> Dict[str, str]:
    """Return a safe code and message without using the exception text."""
    code = classify_provider_failure(exc)
    return {"code": code, "message": safe_provider_failure_message(provider, code)}


def safe_endpoint_for_display(endpoint: str) -> str:
    """Strip embedded credentials, query parameters, and fragments from a URL."""
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        return "Configured endpoint"
    if not parsed.scheme or not parsed.hostname:
        return "Configured endpoint"
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if port:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))
