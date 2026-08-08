"""Tests for P3 CodeForger with FakeProvider."""

from __future__ import annotations

import json as _json

import pytest

from repro_forge.paper.extractor.schemas import AlgorithmSpec
from repro_forge.paper.extractor.schemas import AlgorithmStep
from repro_forge.paper.extractor.schemas import EvidenceRef
from repro_forge.paper.extractor.schemas import EvidenceStatus
from repro_forge.paper.extractor.schemas import EvidenceValue
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.paper.extractor.schemas import TrainingRecipe
from repro_forge.reproduction.code_gen.forger import CodeForger
from repro_forge.reproduction.schemas import ReproductionBundle


def _build_analysis() -> MethodAnalysis:
    return MethodAnalysis(
        paper_id="test.001",
        title="Test Paper",
        problem_statement="Solve a test problem",
        algorithms=[
            AlgorithmSpec(
                name="TestAlgo",
                purpose="Testing",
                steps=[
                    AlgorithmStep(
                        order=1,
                        description="Initialize parameters",
                        evidence=EvidenceRef(
                            evidence_id="ev_001",
                            quote="Initialize with random values",
                            status=EvidenceStatus.VERIFIED,
                        ),
                    )
                ],
                evidence=EvidenceRef(evidence_id="ev_002", quote="TestAlgo description"),
            )
        ],
        training_recipe=TrainingRecipe(
            optimizer=EvidenceValue.reported(
                "Adam",
                EvidenceRef(evidence_id="ev_003", quote="Adam optimizer"),
            ),
        ),
    )


def _plan_response() -> str:
    plan = {
        "files": [
            {
                "path": "src/model.py",
                "purpose": "source",
                "language": "python",
                "evidence_ids": ["ev_001"],
                "is_entrypoint": False,
            },
            {
                "path": "train.py",
                "purpose": "source",
                "language": "python",
                "evidence_ids": ["ev_002", "ev_003"],
                "is_entrypoint": True,
            },
            {
                "path": "tests/test_model.py",
                "purpose": "test",
                "language": "python",
                "evidence_ids": [],
                "is_entrypoint": False,
            },
            {
                "path": "config.yaml",
                "purpose": "config",
                "language": "yaml",
                "evidence_ids": ["ev_003"],
                "is_entrypoint": False,
            },
            {
                "path": "README.md",
                "purpose": "doc",
                "language": "markdown",
                "evidence_ids": [],
                "is_entrypoint": False,
            },
        ],
        "experiments": [{"experiment_name": "main", "entrypoint": ["python", "train.py"]}],
        "dependencies": [{"name": "torch", "version": None, "source": "pypi", "locked": False}],
        "assumptions": [],
        "unresolved": [],
    }
    return _json.dumps(plan)


def _file_response(content: str) -> str:
    return _json.dumps({"content": content})


_VALID_MODEL = """import torch

class TestModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(10, 2)

    def forward(self, x):
        return self.linear(x)
"""

_VALID_TRAIN = """import torch
import sys

def main():
    print("Training...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

_VALID_TEST = """def test_model():
    assert True
"""

_VALID_CONFIG = """lr: 0.001
"""

_VALID_README = """# Test Paper Reproduction
"""


@pytest.fixture
def fake_provider_for_forger():
    from tests.conftest import FakeLLMProvider

    provider = FakeLLMProvider(
        responses=[
            _plan_response(),  # plan
            _file_response(_VALID_MODEL),  # src/model.py
            _file_response(_VALID_TRAIN),  # train.py
            _file_response(_VALID_TEST),  # tests/test_model.py
            _file_response(_VALID_CONFIG),  # config.yaml
            _file_response(_VALID_README),  # README.md
        ]
    )
    return provider


class TestCodeForgerWithFakeProvider:
    async def test_generates_bundle(self, fake_provider_for_forger) -> None:
        forger = CodeForger(fake_provider_for_forger)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        assert isinstance(bundle, ReproductionBundle)
        assert bundle.paper_id == "test.001"
        assert len(bundle.files) >= 3  # model, train, test at minimum

    async def test_generated_files_have_hash(self, fake_provider_for_forger) -> None:
        forger = CodeForger(fake_provider_for_forger)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        for f in bundle.files:
            assert f.content_hash != ""
            assert len(f.content_hash) == 64

    async def test_bundle_has_entrypoint(self, fake_provider_for_forger) -> None:
        forger = CodeForger(fake_provider_for_forger)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        assert len(bundle.experiments) > 0
        assert len(bundle.experiments[0].entrypoint) > 0

    async def test_manifest_hash_computed(self, fake_provider_for_forger) -> None:
        forger = CodeForger(fake_provider_for_forger)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        assert bundle.manifest_hash != ""

    async def test_bundle_serializable(self, fake_provider_for_forger) -> None:
        forger = CodeForger(fake_provider_for_forger)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        dumped = bundle.model_dump(mode="json")
        bundle2 = ReproductionBundle(**dumped)
        assert bundle2.manifest_hash == bundle.manifest_hash


class TestCodeForgerRepair:
    async def test_repair_with_syntax_error(self) -> None:
        from tests.conftest import FakeLLMProvider

        provider = FakeLLMProvider(
            responses=[
                _json.dumps(
                    {
                        "files": [
                            {
                                "path": "main.py",
                                "purpose": "source",
                                "language": "python",
                                "evidence_ids": [],
                                "is_entrypoint": True,
                            },
                            {
                                "path": "tests/test_main.py",
                                "purpose": "test",
                                "language": "python",
                                "evidence_ids": [],
                                "is_entrypoint": False,
                            },
                        ],
                        "experiments": [
                            {"experiment_name": "main", "entrypoint": ["python", "main.py"]}
                        ],
                        "dependencies": [],
                        "assumptions": [],
                        "unresolved": [],
                    }
                ),
                _json.dumps({"content": "if True print('broken')\n"}),  # invalid Python
                _json.dumps({"content": "def test_main():\n    assert True\n"}),
                _json.dumps(
                    {"content": "print('hello world')\n", "changes": "Fixed syntax error"}
                ),  # repaired
            ]
        )
        forger = CodeForger(provider)
        analysis = _build_analysis()
        bundle = await forger.forge(analysis)

        assert len(bundle.files) > 0
        assert "hello" in bundle.files[0].content.lower()

    async def test_invalid_bundle_after_repair_fails_closed(self) -> None:
        from repro_forge.reproduction.code_gen.forger import GenerationError
        from tests.conftest import FakeLLMProvider

        provider = FakeLLMProvider(
            responses=[
                _json.dumps(
                    {
                        "files": [
                            {
                                "path": "main.py",
                                "purpose": "source",
                                "language": "python",
                                "evidence_ids": [],
                                "is_entrypoint": True,
                            }
                        ],
                        "experiments": [
                            {"experiment_name": "main", "entrypoint": ["python", "main.py"]}
                        ],
                        "dependencies": [],
                        "assumptions": [],
                        "unresolved": [],
                    }
                ),
                _json.dumps({"content": "print('valid syntax but no tests')\n"}),
            ]
        )

        with pytest.raises(GenerationError, match="validation"):
            await CodeForger(provider).forge(_build_analysis())
