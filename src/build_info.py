"""Non-sensitive build metadata for deployment traceability."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict

from .gemini_assistant import GEMINI_MODEL_DEFAULT


ROOT = Path(__file__).resolve().parents[1]
COMMIT_ENV_NAMES = ("APP_COMMIT_SHA", "STREAMLIT_GIT_COMMIT", "SOURCE_COMMIT", "GITHUB_SHA")


def app_version() -> str:
    try:
        value = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    return value or "unknown"


def normalize_commit(value: str) -> str:
    candidate = value.strip()
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", candidate):
        return candidate[:7].lower()
    return "unknown"


def commit_id() -> str:
    for name in COMMIT_ENV_NAMES:
        candidate = normalize_commit(os.getenv(name, ""))
        if candidate != "unknown":
            return candidate
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return normalize_commit(result.stdout)


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def get_build_info() -> Dict[str, str]:
    return {
        "App version": app_version(),
        "Commit": commit_id(),
        "Python": platform.python_version(),
        "Streamlit": package_version("streamlit"),
        "Gemini model": os.getenv("GEMINI_MODEL", GEMINI_MODEL_DEFAULT).strip() or GEMINI_MODEL_DEFAULT,
    }
