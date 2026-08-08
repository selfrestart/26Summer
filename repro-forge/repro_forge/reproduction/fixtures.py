"""Maintainer-owned CPU fixtures for P3 runner verification.

Only exact IDs from this immutable registry may reach the host subprocess
backend. Generated or caller-supplied code is never accepted there.
"""

from __future__ import annotations

from types import MappingProxyType

from repro_forge.reproduction.schemas import FixtureSpec

P3_CPU_SMOKE_SUCCESS = FixtureSpec(
    fixture_id="p3-cpu-smoke",
    description="Deterministic CPU smoke test that exits successfully",
    code='''"""P3 CPU smoke fixture — exits 0 with deterministic output."""
import json
import os
import sys
from pathlib import Path

result = {"status": "ok", "sum": sum(range(100))}
output_dir = Path(os.environ["REPROFORGE_OUTPUT_DIR"])
metrics_path = output_dir / "reproforge-metrics.jsonl"
metrics_path.write_text(
    json.dumps({"name": "cpu_smoke", "value": 1.0, "step": 0}) + "\\n",
    encoding="utf-8",
)
print(json.dumps(result))
sys.exit(0)
''',
    expected_exit=0,
    timeout_seconds=10,
)

P3_CPU_SMOKE_FAIL = FixtureSpec(
    fixture_id="p3-cpu-smoke-fail",
    description="Deterministic CPU fixture that exits non-zero",
    code='''"""P3 CPU smoke fixture — exits 1."""
import sys

print("failure message")
sys.exit(1)
''',
    expected_exit=1,
    timeout_seconds=10,
)

P3_CPU_SMOKE_TIMEOUT = FixtureSpec(
    fixture_id="p3-cpu-smoke-timeout",
    description="Deterministic CPU fixture that sleeps long enough to timeout",
    code='''"""P3 CPU smoke fixture — runs long."""
import time

time.sleep(9999)
''',
    expected_exit=-1,
    timeout_seconds=2,
)

P3_CPU_SMOKE_LARGE_OUTPUT = FixtureSpec(
    fixture_id="p3-cpu-smoke-large-output",
    description="Deterministic CPU fixture that produces large stdout/stderr",
    code='''"""P3 CPU smoke fixture — large output."""
import sys

print("x" * 10000)
print("y" * 10000, file=sys.stderr)
''',
    expected_exit=0,
    timeout_seconds=10,
)

P3_CPU_SMOKE_CLEANUP = FixtureSpec(
    fixture_id="p3-cpu-smoke-cleanup",
    description="Deterministic CPU fixture that creates an output artifact",
    code='''"""P3 CPU smoke fixture — creates an output artifact."""
import os
from pathlib import Path

output = Path(os.environ["REPROFORGE_OUTPUT_DIR"])
artifact = output / "cleanup-smoke.txt"
artifact.write_text("test data", encoding="utf-8")
print(artifact.name)
''',
    expected_exit=0,
    timeout_seconds=10,
)


_FIXTURES = MappingProxyType(
    {
        fixture.fixture_id: fixture
        for fixture in (
            P3_CPU_SMOKE_SUCCESS,
            P3_CPU_SMOKE_FAIL,
            P3_CPU_SMOKE_TIMEOUT,
            P3_CPU_SMOKE_LARGE_OUTPUT,
            P3_CPU_SMOKE_CLEANUP,
        )
    }
)


def get_fixture(fixture_id: str) -> FixtureSpec | None:
    """Resolve a maintainer-owned fixture by exact ID."""
    return _FIXTURES.get(fixture_id)


def list_fixtures() -> list[str]:
    """Return all registered fixture IDs."""
    return sorted(_FIXTURES)
