"""Tests for P3 static validation."""

from __future__ import annotations

from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.verification.static_check import ast_check
from repro_forge.reproduction.verification.static_check import check_entrypoint
from repro_forge.reproduction.verification.static_check import check_manifest_integrity
from repro_forge.reproduction.verification.static_check import check_tests_exist
from repro_forge.reproduction.verification.static_check import compile_check
from repro_forge.reproduction.verification.static_check import validate_bundle
from repro_forge.reproduction.verification.static_check import validate_config_files


class TestAstCheck:
    def test_valid_python(self) -> None:
        ok, err = ast_check("test.py", "x = 1\ny = 2\n")
        assert ok, err
        assert err == ""

    def test_syntax_error(self) -> None:
        ok, err = ast_check("bad.py", "if True print('oops')\n")
        assert not ok
        assert "SyntaxError" in err

    def test_empty_file(self) -> None:
        ok, err = ast_check("empty.py", "")
        assert ok, err


class TestCompileCheck:
    def test_valid_python(self) -> None:
        ok, err = compile_check("test.py", "def f(): return 1\n")
        assert ok, err

    def test_syntax_error(self) -> None:
        ok, _err = compile_check("bad.py", "def f(: pass\n")
        assert not ok


class TestCheckEntrypoint:
    def test_found(self) -> None:
        files = [GeneratedFile(path="train.py", content="", purpose="source")]
        ok, _msg = check_entrypoint(files, ["python", "train.py"])
        assert ok

    def test_not_found(self) -> None:
        files = [GeneratedFile(path="main.py", content="", purpose="source")]
        ok, msg = check_entrypoint(files, ["python", "train.py"])
        assert not ok
        assert "train.py" in msg

    def test_no_entrypoint(self) -> None:
        ok, _msg = check_entrypoint([], [])
        assert not ok


class TestCheckTestsExist:
    def test_found_tests(self) -> None:
        files = [
            GeneratedFile(path="src/model.py", content="", purpose="source"),
            GeneratedFile(path="tests/test_model.py", content="", purpose="test"),
        ]
        ok, _msg = check_tests_exist(files)
        assert ok

    def test_no_tests(self) -> None:
        files = [GeneratedFile(path="src/model.py", content="", purpose="source")]
        ok, _msg = check_tests_exist(files)
        assert not ok


class TestCheckManifestIntegrity:
    def test_valid(self) -> None:
        f = GeneratedFile(path="a.py", content="x = 1", purpose="source")
        bundle = ReproductionBundle(paper_id="p1", files=[f])
        ok, msg = check_manifest_integrity(bundle)
        assert ok, msg

    def test_tampered_content(self) -> None:
        f = GeneratedFile(path="a.py", content="x = 1", purpose="source")
        bundle = ReproductionBundle(paper_id="p1", files=[f])
        bundle.files[0].content = "x = 2"
        ok, _msg = check_manifest_integrity(bundle)
        assert not ok


class TestValidateConfig:
    def test_valid_json_config(self) -> None:
        files = [
            GeneratedFile(
                path="config.json",
                content='{"lr": 0.001}',
                language="json",
                purpose="config",
            )
        ]
        issues = validate_config_files(files)
        assert issues == []

    def test_invalid_json_config(self) -> None:
        files = [
            GeneratedFile(
                path="config.json",
                content="{bad",
                language="json",
                purpose="config",
            )
        ]
        issues = validate_config_files(files)
        assert len(issues) > 0


class TestFullValidation:
    def test_valid_bundle_passes(self) -> None:
        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(
                    path="train.py",
                    content="import os\nprint('hello')\n",
                    purpose="source",
                    is_entrypoint=True,
                ),
                GeneratedFile(
                    path="tests/test_train.py", content="def test(): pass\n", purpose="test"
                ),
            ],
            experiments=[
                ExperimentSpec(entrypoint=["python", "train.py"]),
            ],
        )
        report = validate_bundle(bundle)
        assert report.valid

    def test_syntax_error_bundle_fails(self) -> None:
        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(
                    path="train.py", content="def f(: pass\n", purpose="source", language="python"
                ),
                GeneratedFile(
                    path="tests/test_train.py",
                    content="def test(): pass\n",
                    purpose="test",
                    language="python",
                ),
            ],
        )
        report = validate_bundle(bundle)
        assert not report.valid
        assert len(report.ast_errors) > 0
