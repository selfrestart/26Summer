"""Installed-dependency smoke coverage for repository examples."""

import os
import subprocess
import sys
from pathlib import Path


def test_read_paper_example_uses_a_portable_ascii_heading() -> None:
    project_root = Path(__file__).parents[2]

    result = subprocess.run(
        [sys.executable, str(project_root / "examples" / "read_paper.py")],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    assert "ReproForge - PaperReader Demo" in result.stdout
