#!/usr/bin/env python3
"""Run the complete credential-free Photography H0 validation suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    run([sys.executable, "scripts/validate_site.py"])
    run([sys.executable, "scripts/validate_photography.py"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    scripts = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "scripts").glob("*.py"))
    run([sys.executable, "-m", "py_compile", *scripts])
    run(["git", "diff", "--check"])
    print("PASS: offline H0 validation suite")


if __name__ == "__main__":
    main()
