"""Optional, explicitly enabled unittest execution in a separate process.

This is NOT an operating-system sandbox. Generated code has the user's rights.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from .client import Cancelled


def run_python_tests(root: Path, cancel: threading.Event, enabled: bool) -> dict:
    if not enabled:
        return {"status": "disabled", "message": "The user has not enabled generated-code execution. Report tests as not run."}
    if not (root / "tests").is_dir():
        return {"status": "failed", "message": "Create a tests/ directory with Python unittest test_*.py files first."}
    output = root / ".agent" / "python-tests.log"
    child_output = root / ".agent" / "child-tests.log"
    child_output.unlink(missing_ok=True)
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--run-python-tests", str(root)]
    else:
        command = [sys.executable, "-I", str(Path(__file__).resolve().parents[1] / "main.py"), "--run-python-tests", str(root)]
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT", "LANG"}
    environment = {k: v for k, v in os.environ.items() if k.upper() in keep}
    environment["PYTHONUTF8"] = "1"
    with output.open("wb") as handle:
        process = subprocess.Popen(command, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        deadline, status = time.monotonic() + 60, "finished"
        while process.poll() is None:
            log_bytes = output.stat().st_size + (child_output.stat().st_size if child_output.exists() else 0)
            if cancel.wait(0.15) or time.monotonic() > deadline or log_bytes > 2_000_000:
                status = "cancelled" if cancel.is_set() else "limit_reached"
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                else:
                    process.kill()
                process.wait(timeout=10)
                break
    if cancel.is_set():
        raise Cancelled()
    actual_output = child_output if child_output.exists() else output
    with actual_output.open("rb") as handle:
        handle.seek(max(0, actual_output.stat().st_size - 16000))
        tail = handle.read().decode("utf-8", errors="replace")
    return {"status": status, "exit_code": process.returncode,
            "passed": status == "finished" and process.returncode == 0,
            "output": tail, "scope": "Python stdlib unittest only; no dependencies installed; not sandboxed."}


def child_main(root: str) -> int:
    import unittest
    import importlib
    project = Path(root).resolve()
    os.chdir(project)
    sys.path.insert(0, str(project))
    importlib.invalidate_caches()
    try:
        suite = unittest.defaultTestLoader.discover(str(project / "tests"), pattern="test_*.py")
        if not suite.countTestCases():
            print("No Python unittest cases found; zero tests is not a pass.")
            return 2
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    except Exception as exc:
        print(f"Test discovery failed: {exc}")
        return 2
