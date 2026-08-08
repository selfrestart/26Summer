"""Tests for P3 pipeline integration and CLI."""

from __future__ import annotations

import asyncio
import json

import pytest

from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import RunStatus


class TestReproductionPipeline:
    def test_pipeline_requires_provider_for_generate(self) -> None:
        from repro_forge.paper.extractor.schemas import MethodAnalysis
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        pipeline = ReproductionPipeline()
        with pytest.raises(ValueError, match="Code generation requires"):
            asyncio.run(pipeline.generate(MethodAnalysis()))

    async def test_pipeline_execute_dryrun(self) -> None:
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(path="t.py", content="print('hi')\n", purpose="source"),
                GeneratedFile(path="tests/t.py", content="def test(): pass\n", purpose="test"),
            ],
            experiments=[ExperimentSpec(entrypoint=["python", "t.py"])],
        )
        pipeline = ReproductionPipeline()
        run = await pipeline.execute(bundle, backend="dryrun")
        assert run.status == RunStatus.SUCCESS
        assert run.backend == "dryrun"

    async def test_pipeline_run_fixture(self) -> None:
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        pipeline = ReproductionPipeline()
        run = await pipeline.run_registered_fixture("p3-cpu-smoke")
        assert run.status == RunStatus.SUCCESS

    async def test_pipeline_rejects_unknown_fixture(self) -> None:
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        pipeline = ReproductionPipeline()
        run = await pipeline.run_registered_fixture("not-registered")
        assert run.status == RunStatus.BLOCKED

    async def test_pipeline_rejects_out_of_range_experiment(self) -> None:
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        pipeline = ReproductionPipeline()
        run = await pipeline.execute(
            ReproductionBundle(
                files=[GeneratedFile(path="t.py", content="print(1)", purpose="source")],
                experiments=[ExperimentSpec(entrypoint=["python", "t.py"])],
            ),
            experiment_index=99,
        )
        assert run.status == RunStatus.BLOCKED


class TestCLIP3Commands:
    def test_parser_has_p3_commands(self) -> None:
        from repro_forge.cli import _build_parser

        parser = _build_parser()
        assert parser is not None

    def test_capabilities_shows_p3(self, capsys) -> None:
        import argparse

        from repro_forge.cli import _capabilities

        ns = argparse.Namespace()
        rc = _capabilities(ns)
        assert rc == 0
        captured = capsys.readouterr()
        assert "P3" in captured.out

    def test_run_fixture_invalid_id(self) -> None:
        import argparse

        from repro_forge.cli import _run_fixture

        ns = argparse.Namespace(
            fixture_id="nonexistent",
            backend="local-subprocess",
            output=None,
            force=False,
        )
        with pytest.raises(SystemExit):
            _run_fixture(ns)

    def test_run_fixture_smoke(self, tmp_path) -> None:
        import argparse

        from repro_forge.cli import _run_fixture

        output = tmp_path / "nested" / "run.json"
        ns = argparse.Namespace(
            fixture_id="p3-cpu-smoke",
            backend="local-subprocess",
            output=output,
            force=True,
        )
        rc = _run_fixture(ns)
        assert rc == 0
        assert output.exists()
        run_data = json.loads(output.read_text(encoding="utf-8"))
        assert run_data["status"] == "success"

    def test_run_fixture_failure_returns_nonzero(self, tmp_path) -> None:
        import argparse

        from repro_forge.cli import _run_fixture

        output = tmp_path / "failed-run.json"
        ns = argparse.Namespace(
            fixture_id="p3-cpu-smoke-fail",
            backend="local-subprocess",
            output=output,
            force=True,
        )

        rc = _run_fixture(ns)

        assert rc == 3
        run_data = json.loads(output.read_text(encoding="utf-8"))
        assert run_data["status"] == "failed"
        assert run_data["failure_code"] == "non_zero_exit"

    def test_run_experiment_dryrun(self, tmp_path) -> None:
        import argparse

        from repro_forge.cli import _run_experiment

        bundle_path = tmp_path / "bundle.json"
        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(path="t.py", content="print(1)\n", purpose="source"),
                GeneratedFile(path="tests/t.py", content="def test(): pass\n", purpose="test"),
            ],
            experiments=[ExperimentSpec(entrypoint=["python", "t.py"])],
        )
        bundle_path.write_text(json.dumps(bundle.model_dump(mode="json")), encoding="utf-8")

        ns = argparse.Namespace(
            bundle=bundle_path,
            backend="dryrun",
            output=None,
            force=False,
        )
        rc = _run_experiment(ns)
        assert rc == 0

    def test_generate_code_requires_llm(self, tmp_path) -> None:
        """ReproductionPipeline.generate() raises ValueError when no provider is given."""
        from repro_forge.paper.extractor.schemas import MethodAnalysis
        from repro_forge.reproduction.pipeline import ReproductionPipeline

        analysis = MethodAnalysis(paper_id="test")
        pipeline = ReproductionPipeline()
        with pytest.raises(ValueError, match="Code generation requires"):
            asyncio.run(pipeline.generate(analysis))


class TestSchemaEdgeCases:
    def test_unknown_schema_version_rejected(self) -> None:
        with pytest.raises(ValueError, match="schema_version"):
            ReproductionBundle(schema_version="unknown")

    def test_empty_bundle_serializes(self) -> None:
        bundle = ReproductionBundle()
        dumped = bundle.model_dump(mode="json")
        assert dumped["schema_version"] == "p3.bundle.v1"

    def test_experiment_run_serializes(self) -> None:
        from repro_forge.reproduction.schemas import ExperimentRun

        run = ExperimentRun(status=RunStatus.SUCCESS)
        dumped = run.model_dump(mode="json")
        assert "run_id" in dumped
        assert "status" in dumped
