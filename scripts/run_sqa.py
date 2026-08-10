"""Run the repository's complete, cross-platform software quality gate."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    python = sys.executable
    try:
        run("Dependency consistency", [python, "-m", "pip", "check"])
        run("Python compilation", [python, "-m", "compileall", "-q", "app.py", "src", "tests", "scripts"])
        with tempfile.TemporaryDirectory(prefix="ai-pcb-coverage-") as temp_dir:
            coverage_env = os.environ.copy()
            coverage_env["COVERAGE_FILE"] = str(Path(temp_dir) / ".coverage")
            run("Coverage reset", [python, "-m", "coverage", "erase"], coverage_env)
            run("Tests with coverage", [python, "-m", "coverage", "run", "-m", "pytest", "-q"], coverage_env)
            run("Coverage threshold", [python, "-m", "coverage", "report"], coverage_env)
        run("Ruff static analysis", [python, "-m", "ruff", "check", "app.py", "src", "tests", "scripts"])
        run("Production dependency audit", [python, "-m", "pip_audit", "-r", "requirements.txt"])
        run("Secret hygiene", [python, "scripts/check_secrets.py"])
        run("Streamlit runtime health", [python, "scripts/check_streamlit_health.py"])
    except subprocess.CalledProcessError as exc:
        print(f"\nSQA failed with exit code {exc.returncode}.", file=sys.stderr)
        return exc.returncode or 1
    print("\nAll SQA gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
