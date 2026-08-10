"""Start Streamlit temporarily and verify its HTTP health and root endpoints."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def fetch(url: str, timeout: float = 2.0) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def main() -> int:
    port = available_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        health_status = 0
        health_body = ""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                health_status, health_body = fetch(f"http://127.0.0.1:{port}/_stcore/health")
                if health_status == 200:
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.25)
        if health_status != 200 or health_body.strip().lower() != "ok":
            raise RuntimeError("Streamlit health endpoint did not become ready")
        root_status, root_body = fetch(f"http://127.0.0.1:{port}/", timeout=5)
        if root_status != 200 or "streamlit" not in root_body.lower():
            raise RuntimeError("Streamlit root page did not return the expected application shell")
        print(f"Streamlit health check passed on an ephemeral local port (health={health_status}, root={root_status}).")
        return 0
    except Exception as exc:
        print(f"Streamlit health check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
