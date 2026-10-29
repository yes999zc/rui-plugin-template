"""The template's one contract check.

Runs the official contract checker against this repository. The checker is a
house-ear CLI (`rui-adapter-check`); until that CLI ships in a core release this
test skips with the exact commands to run today, so a fresh clone is never red
just because the template predates the tool.

Keep the failure message actionable: a third-party developer reads it first.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = "rui-adapter-check"


def test_contract_checker_passes() -> None:
    """The checker must exit 0 for this template."""
    executable = shutil.which(CLI)
    if executable is None:
        pytest.skip(
            f"{CLI!r} is not on PATH yet: the CLI is still being merged into the "
            "core repo. Run the same check today with either of:\n"
            f"  rui plug-test {REPO_ROOT} --adapter {REPO_ROOT / 'adapter.py'}:build\n"
            f"  python -m rui plug-test {REPO_ROOT} "
            f"--adapter {REPO_ROOT / 'adapter.py'}:build\n"
            "After the CLI ships, re-run this test (no edits needed)."
        )

    completed = subprocess.run(
        [executable, "--adapter", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, (
        f"{CLI} exited {completed.returncode} for {REPO_ROOT}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
