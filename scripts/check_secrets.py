"""Fail when tracked repository files appear to contain production credentials."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRACKED_PATHS = {".streamlit/secrets.toml", ".env"}
SECRET_PATTERNS = {
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    "OpenAI-style key": re.compile(rb"sk-[0-9A-Za-z_-]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def repository_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8", errors="surrogateescape") for item in result.stdout.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    inspected_files = repository_files()
    for relative_path in inspected_files:
        normalized = relative_path.replace("\\", "/")
        if normalized in FORBIDDEN_TRACKED_PATHS:
            findings.append(f"forbidden credential file is tracked: {normalized}")
        path = ROOT / relative_path
        try:
            content = path.read_bytes()
        except OSError as exc:
            findings.append(f"could not inspect tracked file {normalized}: {exc.__class__.__name__}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"possible {label} in tracked file: {normalized}")

    if findings:
        print("Secret hygiene check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Secret hygiene check passed ({len(inspected_files)} repository files inspected).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
