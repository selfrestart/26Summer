"""Static validation and repair for generated code bundles."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from repro_forge.reproduction.schemas import DependencySpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import canonical_json

# ---------------------------------------------------------------------------
# AST / compile checks
# ---------------------------------------------------------------------------


def ast_check(file_path: str, source: str) -> tuple[bool, str]:
    """Parse *source* with ``ast``; return (ok, error_message)."""
    try:
        ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        return False, f"SyntaxError in {file_path}: {exc}"
    return True, ""


def compile_check(file_path: str, source: str) -> tuple[bool, str]:
    """Compile *source*; return (ok, error_message)."""
    try:
        compile(source, file_path, "exec")
    except Exception as exc:
        return False, f"CompileError in {file_path}: {exc}"
    return True, ""


# ---------------------------------------------------------------------------
# Import vs dependency declaration
# ---------------------------------------------------------------------------

_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S.*?)(?:\s+as\s+\S+)?$)",
    re.MULTILINE,
)


def _extract_top_level_imports(source: str) -> set[str]:
    modules: set[str] = set()
    for match in _IMPORT_RE.finditer(source):
        from_import = match.group(1)
        direct_import = match.group(2)
        if from_import:
            modules.add(from_import.split(".")[0])
        if direct_import:
            for part in direct_import.split(","):
                modules.add(part.strip().split(".")[0].split(" as ")[0].strip())
    return modules - {"__future__"}


def _is_stdlib(module: str) -> bool:
    import sys

    return module in sys.stdlib_module_names


_KNOWN_STDLIBS: set[str] = {
    "os",
    "sys",
    "re",
    "json",
    "math",
    "pathlib",
    "typing",
    "collections",
    "itertools",
    "functools",
    "datetime",
    "hashlib",
    "uuid",
    "ast",
    "copy",
    "argparse",
    "logging",
    "unittest",
    "subprocess",
    "tempfile",
    "shutil",
    "dataclasses",
    "enum",
    "abc",
    "inspect",
    "warnings",
    "textwrap",
    "types",
    "io",
    "csv",
    "xml",
    "html",
    "http",
    "urllib",
    "email",
    "socket",
    "ssl",
    "struct",
    "random",
    "statistics",
    "traceback",
    "pdb",
    "profile",
    "timeit",
    "doctest",
    "pydoc",
    "zipfile",
    "tarfile",
    "gzip",
    "bz2",
    "lzma",
    "configparser",
    "tomllib",
}


def _check_imports(
    source: str,
    deps: list[DependencySpec],
    local_modules: set[str],
) -> tuple[bool, list[str]]:
    imports = _extract_top_level_imports(source)
    declared = {
        (dependency.import_name or dependency.name.replace("-", "_")).lower() for dependency in deps
    }
    missing: list[str] = []
    for imp in imports:
        if imp in _KNOWN_STDLIBS:
            continue
        if imp in local_modules:
            continue
        if imp.lower() not in declared:
            missing.append(imp)
    return len(missing) == 0, missing


# ---------------------------------------------------------------------------
# Entry file existence
# ---------------------------------------------------------------------------


def check_entrypoint(files: list[GeneratedFile], entrypoint: list[str]) -> tuple[bool, str]:
    if not entrypoint:
        return False, "No entrypoint specified"
    if entrypoint[0] not in ("python", "python3"):
        return False, "P3 v1 entrypoint executable must be python or python3"
    py_files = [arg for arg in entrypoint[1:] if arg.endswith(".py")]
    if not py_files:
        return True, ""
    candidate = py_files[0]
    paths = {f.path for f in files}
    if candidate not in paths:
        return False, f"Entrypoint {candidate!r} not found in bundle files"
    return True, ""


# ---------------------------------------------------------------------------
# Config format validation
# ---------------------------------------------------------------------------


def _check_json_valid(content: str) -> bool:
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        return False


def _check_yaml_valid(content: str) -> bool:
    try:
        import yaml

        yaml.safe_load(content)
        return True
    except Exception:
        return False


_CONFIG_VALIDATORS: dict[str, Any] = {
    ".json": _check_json_valid,
    ".yaml": _check_yaml_valid,
    ".yml": _check_yaml_valid,
}


def validate_config_files(files: list[GeneratedFile]) -> list[str]:
    issues: list[str] = []
    for f in files:
        if f.purpose != "config":
            continue
        ext = PurePosixPath(f.path).suffix
        validator = _CONFIG_VALIDATORS.get(ext)
        if validator is None:
            continue
        if not validator(f.content):
            issues.append(f"Invalid {ext} in config file {f.path!r}")
    return issues


# ---------------------------------------------------------------------------
# Test file existence
# ---------------------------------------------------------------------------


def check_tests_exist(files: list[GeneratedFile]) -> tuple[bool, str]:
    test_files = [f for f in files if f.purpose == "test"]
    if not test_files:
        return False, "No test files found in bundle"
    return True, f"Found {len(test_files)} test file(s)"


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------


def check_manifest_integrity(bundle: ReproductionBundle) -> tuple[bool, str]:
    computed = bundle.compute_manifest_hash()
    if computed != bundle.manifest_hash:
        return (
            False,
            f"Manifest hash mismatch: stored={bundle.manifest_hash[:16]}... computed={computed[:16]}...",
        )
    for f in bundle.files:
        expected = hashlib.sha256(f.content.encode("utf-8")).hexdigest()
        if expected != f.content_hash:
            return (
                False,
                f"Content hash mismatch for {f.path!r}: stored={f.content_hash[:16]}... computed={expected[:16]}...",
            )
    manifests = [f for f in bundle.files if f.path == "reproforge-manifest.json"]
    if len(manifests) != 1:
        return False, "Bundle must contain exactly one reproforge-manifest.json"
    expected_document = canonical_json(bundle.manifest_document()) + "\n"
    if manifests[0].content != expected_document:
        return False, "Manifest file does not match bundle metadata"
    return True, ""


# ---------------------------------------------------------------------------
# Full validation report
# ---------------------------------------------------------------------------


class ValidationReport(BaseModel):
    """Result of a full static validation pass."""

    ast_errors: list[str] = Field(default_factory=list)
    compile_errors: list[str] = Field(default_factory=list)
    import_errors: list[str] = Field(default_factory=list)
    entrypoint_errors: list[str] = Field(default_factory=list)
    config_errors: list[str] = Field(default_factory=list)
    test_errors: list[str] = Field(default_factory=list)
    manifest_errors: list[str] = Field(default_factory=list)
    evidence_errors: list[str] = Field(default_factory=list)
    valid: bool = True

    def add(self, other: ValidationReport) -> ValidationReport:
        self.ast_errors.extend(other.ast_errors)
        self.compile_errors.extend(other.compile_errors)
        self.import_errors.extend(other.import_errors)
        self.entrypoint_errors.extend(other.entrypoint_errors)
        self.config_errors.extend(other.config_errors)
        self.test_errors.extend(other.test_errors)
        self.manifest_errors.extend(other.manifest_errors)
        self.evidence_errors.extend(other.evidence_errors)
        self.valid = self.valid and other.valid
        return self


def validate_bundle(bundle: ReproductionBundle) -> ValidationReport:
    report = ValidationReport()

    for f in bundle.files:
        if f.language != "python":
            continue
        ok, err = ast_check(f.path, f.content)
        if not ok:
            report.ast_errors.append(err)
            report.valid = False
        ok, err = compile_check(f.path, f.content)
        if not ok:
            report.compile_errors.append(err)
            report.valid = False

    for exp in bundle.experiments:
        ok, err = check_entrypoint(bundle.files, exp.entrypoint)
        if not ok:
            report.entrypoint_errors.append(err)
            report.valid = False

    local_modules: set[str] = set()
    for file in bundle.files:
        path = PurePosixPath(file.path)
        if len(path.parts) > 1:
            local_modules.add(path.parts[0])
        elif path.suffix == ".py":
            local_modules.add(path.stem)

    all_dependencies = [
        dependency for experiment in bundle.experiments for dependency in experiment.dependencies
    ]
    for f in bundle.files:
        if f.language != "python":
            continue
        ok, missing = _check_imports(f.content, all_dependencies, local_modules)
        if not ok:
            report.import_errors.append(f"Undeclared imports in {f.path!r}: {missing}")
            report.valid = False

    config_issues = validate_config_files(bundle.files)
    if config_issues:
        report.config_errors.extend(config_issues)
        report.valid = False

    ok, msg = check_tests_exist(bundle.files)
    if not ok:
        report.test_errors.append(msg)
        report.valid = False

    ok, msg = check_manifest_integrity(bundle)
    if not ok:
        report.manifest_errors.append(msg)
        report.valid = False

    allowed_evidence = set(bundle.source_evidence_ids)
    for file in bundle.files:
        unknown = sorted(set(file.evidence_ids) - allowed_evidence)
        if unknown:
            report.evidence_errors.append(f"Unknown evidence IDs in {file.path!r}: {unknown}")
            report.valid = False

    return report
