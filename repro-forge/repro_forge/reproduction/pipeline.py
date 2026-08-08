"""ReproductionPipeline — compose code generation and experiment execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from repro_forge.reproduction.experiment.experimentor import Experimentor

if TYPE_CHECKING:
    from repro_forge.paper.extractor.schemas import MethodAnalysis
    from repro_forge.providers.base import BaseProvider
    from repro_forge.reproduction.schemas import ExperimentRun
    from repro_forge.reproduction.schemas import ReproductionBundle


class ReproductionPipeline:
    """P3 orchestration: generate a bundle, then execute it."""

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self._provider = provider
        self._experimentor = Experimentor()

    async def generate(self, analysis: MethodAnalysis) -> ReproductionBundle:
        """Generate a ``ReproductionBundle`` from a ``MethodAnalysis``.

        Requires an LLM provider.  Raises ``ValueError`` if no provider was
        injected.
        """
        if self._provider is None:
            raise ValueError("Code generation requires an LLM provider; inject a BaseProvider")
        from repro_forge.reproduction.code_gen.forger import CodeForger

        forger = CodeForger(self._provider)
        return await forger.forge(analysis)

    async def execute(
        self,
        bundle: ReproductionBundle,
        backend: str = "dryrun",
        experiment_index: int = 0,
    ) -> ExperimentRun:
        """Execute a bundle with the selected backend."""
        return await self._experimentor.execute(bundle, backend, experiment_index)

    async def run_registered_fixture(
        self,
        fixture_id: str,
        backend: str = "local-subprocess",
    ) -> ExperimentRun:
        """Execute a registered fixture with the selected backend."""
        return await self._experimentor.run_registered_fixture(fixture_id, backend)
