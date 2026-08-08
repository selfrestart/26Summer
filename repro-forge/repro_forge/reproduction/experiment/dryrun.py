"""Dry-run backend — materialise, validate, emit events, but never execute."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from repro_forge.reproduction.schemas import EventType
from repro_forge.reproduction.schemas import ExperimentEvent
from repro_forge.reproduction.schemas import ExperimentRun
from repro_forge.reproduction.schemas import FailureCode
from repro_forge.reproduction.schemas import RunStatus
from repro_forge.reproduction.verification.static_check import validate_bundle

if TYPE_CHECKING:
    from repro_forge.reproduction.schemas import ExperimentSpec
    from repro_forge.reproduction.schemas import ReproductionBundle


async def dryrun_execute(
    bundle: ReproductionBundle,
    experiment: ExperimentSpec,
) -> ExperimentRun:
    """Materialise the bundle to a temp directory, validate, emit events, and clean up.

    This backend NEVER runs any generated code.  It only verifies that the
    bundle is structurally sound.
    """
    run = ExperimentRun(
        bundle_id=bundle.bundle_id,
        backend="dryrun",
        status=RunStatus.RUNNING,
        started_at=datetime.now(UTC).isoformat(),
    )

    events: list[ExperimentEvent] = []
    seq = 0

    def _event(etype: EventType, payload: dict[str, object] | None = None) -> ExperimentEvent:
        nonlocal seq
        seq += 1
        return ExperimentEvent(
            sequence=seq,
            run_id=run.run_id,
            timestamp=datetime.now(UTC).isoformat(),
            event_type=etype,
            payload=payload or {},
        )

    events.append(_event(EventType.STATUS, {"status": "materializing"}))
    materialize_dir: Path | None = None
    try:
        materialize_dir = Path(tempfile.mkdtemp(prefix="reproforge_dryrun_"))
        run_dir = materialize_dir / "bundle"
        run_dir.mkdir(parents=True, exist_ok=True)

        for f in bundle.files:
            dest = run_dir / f.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8", newline="\n")

        events.append(_event(EventType.STATUS, {"status": "validating"}))
        report = validate_bundle(bundle)
        if not report.valid:
            errors = (
                report.ast_errors
                + report.compile_errors
                + report.import_errors
                + report.entrypoint_errors
                + report.config_errors
                + report.test_errors
                + report.manifest_errors
                + report.evidence_errors
            )
            events.append(_event(EventType.ERROR, {"errors": errors}))
            run.status = RunStatus.FAILED
            run.failure_code = FailureCode.PATH_VALIDATION
        else:
            events.append(_event(EventType.STATUS, {"status": "verified"}))
            run.status = RunStatus.SUCCESS

    except Exception as exc:
        events.append(_event(EventType.ERROR, {"error": str(exc)}))
        run.status = RunStatus.FAILED
        run.failure_code = FailureCode.PATH_VALIDATION
    finally:
        if materialize_dir is not None and materialize_dir.exists():
            with suppress(OSError):
                shutil.rmtree(materialize_dir)
        events.append(_event(EventType.STATUS, {"status": "cleaned_up"}))

    run.events = events
    run.finished_at = datetime.now(UTC).isoformat()
    return run
