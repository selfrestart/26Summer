"""Experimentor — the central orchestrator for experiment execution.

Routes each execution request to the appropriate backend and collects
the resulting ``ExperimentRun``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from repro_forge.reproduction.schemas import ExperimentRun
from repro_forge.reproduction.schemas import FailureCode
from repro_forge.reproduction.schemas import RunStatus

if TYPE_CHECKING:
    from repro_forge.reproduction.schemas import ReproductionBundle


class Experimentor:
    """Select and invoke the appropriate execution backend."""

    async def execute(
        self,
        bundle: ReproductionBundle,
        backend: str = "dryrun",
        experiment_index: int = 0,
    ) -> ExperimentRun:
        if backend not in ("dryrun", "docker"):
            return ExperimentRun(
                backend=backend,
                status=RunStatus.BLOCKED,
                failure_code=FailureCode.SECURITY_VIOLATION,
            )

        if not bundle.experiments:
            return ExperimentRun(
                bundle_id=bundle.bundle_id,
                backend=backend,
                status=RunStatus.BLOCKED,
                failure_code=FailureCode.PATH_VALIDATION,
            )

        if experiment_index < 0 or experiment_index >= len(bundle.experiments):
            return ExperimentRun(
                bundle_id=bundle.bundle_id,
                backend=backend,
                status=RunStatus.BLOCKED,
                failure_code=FailureCode.PATH_VALIDATION,
            )

        from repro_forge.reproduction.verification.static_check import validate_bundle

        if not validate_bundle(bundle).valid:
            return ExperimentRun(
                bundle_id=bundle.bundle_id,
                backend=backend,
                status=RunStatus.BLOCKED,
                failure_code=FailureCode.PATH_VALIDATION,
            )

        experiment = bundle.experiments[experiment_index]

        if backend == "dryrun":
            from repro_forge.reproduction.experiment.dryrun import dryrun_execute

            run = await dryrun_execute(bundle, experiment)
        elif backend == "docker":
            from repro_forge.reproduction.experiment.docker import docker_execute

            run = await docker_execute(bundle, experiment)
        else:
            return ExperimentRun(
                bundle_id=bundle.bundle_id,
                backend=backend,
                status=RunStatus.BLOCKED,
                failure_code="path_validation",
            )

        run.experiment_index = experiment_index
        return run

    async def run_registered_fixture(
        self,
        fixture_id: str,
        backend: str = "local-subprocess",
    ) -> ExperimentRun:
        if backend == "local-subprocess":
            from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

            return await subprocess_execute_fixture(fixture_id)
        elif backend == "docker":
            from repro_forge.reproduction.experiment.docker import docker_execute
            from repro_forge.reproduction.fixtures import get_fixture

            fixture = get_fixture(fixture_id)
            if fixture is None:
                return ExperimentRun(
                    backend="docker",
                    status=RunStatus.BLOCKED,
                    failure_code=FailureCode.SECURITY_VIOLATION,
                )
            return await docker_execute(fixture, fixture=fixture)
        else:
            return ExperimentRun(
                backend=str(backend),
                status=RunStatus.BLOCKED,
                failure_code=FailureCode.SECURITY_VIOLATION,
            )
