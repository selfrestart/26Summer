"""CodeForger agent — generate auditable reproduction bundles."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import BaseModel

from repro_forge.paper.extractor.schemas import EvidenceRef
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.reproduction.schemas import DependencySpec
from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import _sha256
from repro_forge.reproduction.schemas import canonical_json

if TYPE_CHECKING:
    from repro_forge.providers.base import BaseProvider

_CODE_FORGE_SYSTEM_PROMPT = """You are CodeForger, an agent that converts methodology analysis into
reproducible code bundles.  You receive a MethodAnalysis with evidence-grounded
details about a paper's algorithms, architecture, training recipe, and evaluation
protocol.  Your job is to produce Python code that faithfully implements
what the paper describes.

CRITICAL RULES:
1. Every implementation choice that corresponds to a paper detail MUST
   reference the evidence_id from the MethodAnalysis.
2. If a necessary value (learning rate, batch size, architecture detail, etc.)
   is NOT in the MethodAnalysis, you MUST flag it as an assumption or
   unresolved item — NEVER invent a plausible default silently.
3. You do NOT have access to a file system, Python interpreter, or shell.
   Only produce code and structured output.
4. Output ONLY valid JSON.  Do not include commentary outside the JSON.
"""

_FILE_PLAN_PROMPT = """Given the following MethodAnalysis, produce a file plan for the reproduction bundle.

For each file you plan to create, specify:
- path: POSIX relative path within the bundle (e.g. "src/model.py")
- purpose: one of "source", "test", "config", "doc", "data", "script"
- language: "python", "yaml", "json", "markdown", "text"
- evidence_ids: list of evidence IDs from the MethodAnalysis that this file implements
- is_entrypoint: true if this is the main entry point script

Also specify:
- experiments: list with a single entrypoint argv and resource limits
- dependencies: required Python packages with versions where known
- assumptions: what you had to assume (list strings)
- unresolved: what is still unknown (list strings)

MethodAnalysis:
{analysis_json}

Return ONLY valid JSON matching this structure:
{{
  "files": [
    {{"path": "...", "purpose": "...", "language": "...", "evidence_ids": [...], "is_entrypoint": false}}
  ],
  "experiments": [
    {{"experiment_name": "main", "entrypoint": ["python", "train.py"], "timeout_seconds": 3600, "random_seed": 42}}
  ],
  "dependencies": [
    {{"name": "torch", "version": null, "source": "pypi", "locked": false}}
  ],
  "assumptions": [],
  "unresolved": []
}}
"""

_GENERATE_FILE_PROMPT = """Generate the complete content for this file in the reproduction bundle.

File path: {file_path}
Purpose: {purpose}
Evidence IDs to implement: {evidence_ids}

MethodAnalysis context:
{analysis_json}

Previous files already generated (for imports compatibility):
{existing_files}

Return ONLY valid JSON:
{{
  "content": "the full file content as a string with \\n for newlines"
}}

IMPORTANT:
- Write complete, runnable code.  No placeholders like "# TODO".
- Reference evidence IDs in comments where appropriate.
- For Python files, include proper imports.
- For test files, include deterministic smoke tests, not random or LLM-generated tests.
- Use the imports from existing files to stay consistent.
"""

_REPAIR_FILE_PROMPT = """The file at '{file_path}' has validation errors:

{errors}

Previous files that this file depends on:
{existing_files}

Please repair the file. Return ONLY valid JSON:
{{
  "content": "the repaired full file content as a string with \\n for newlines",
  "changes": "brief description of what was fixed"
}}
"""


class GenerationError(RuntimeError):
    """Raised when CodeForger cannot produce a valid auditable bundle."""


def _collect_evidence_ids(analysis: MethodAnalysis) -> list[str]:
    ids: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, EvidenceRef) and obj.evidence_id:
            ids.add(obj.evidence_id)
            return
        if isinstance(obj, BaseModel):
            for field_name in type(obj).model_fields:
                _walk(getattr(obj, field_name))
            return
        if isinstance(obj, list):
            for item in obj:
                _walk(item)
            return
        if isinstance(obj, dict):
            for value in obj.values():
                _walk(value)

    _walk(analysis)
    return sorted(ids)


def _build_analysis_summary(analysis: MethodAnalysis) -> dict[str, object]:
    summary = analysis.model_dump(mode="json")
    summary["evidence_ids"] = _collect_evidence_ids(analysis)
    return cast(dict[str, object], summary)


def _validate_plan(plan: dict[str, object], allowed_evidence_ids: set[str]) -> None:
    raw_files = plan.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise GenerationError("CodeForger plan must contain at least one file")
    for raw_file in raw_files:
        if not isinstance(raw_file, dict):
            raise GenerationError("CodeForger plan contains an invalid file entry")
        evidence_ids = raw_file.get("evidence_ids", [])
        if not isinstance(evidence_ids, list) or not all(
            isinstance(evidence_id, str) for evidence_id in evidence_ids
        ):
            raise GenerationError("CodeForger plan contains malformed evidence IDs")
        unknown = sorted(set(evidence_ids) - allowed_evidence_ids)
        if unknown:
            raise GenerationError(f"CodeForger plan references unknown evidence IDs: {unknown}")


def _check_python_source(source: str) -> tuple[bool, str]:
    import ast

    try:
        ast.parse(source)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"
    return True, ""


class CodeForger:
    """Generate a ``ReproductionBundle`` from a ``MethodAnalysis`` using an LLM provider.

    The forger follows a Plan-then-Execute workflow:
    1. Analyse the MethodAnalysis and produce a file plan with dependencies.
    2. Generate each file one at a time, using the plan and prior files as context.
    3. Run static validation.
    4. If validation fails, attempt at most ONE targeted repair pass.
    5. Return the bundle (with unresolved/assumption items tracked).
    """

    def __init__(self, provider: BaseProvider) -> None:
        self._provider = provider

    async def forge(self, analysis: MethodAnalysis) -> ReproductionBundle:
        """Generate a complete reproduction bundle from the analysis."""
        import json as _json

        analysis_json = _json.dumps(_build_analysis_summary(analysis), indent=2)

        allowed_evidence_ids = set(_collect_evidence_ids(analysis))
        plan = await self._generate_plan(analysis_json)
        _validate_plan(plan, allowed_evidence_ids)
        files = await self._generate_files(plan, analysis_json)
        bundle = self._assemble_bundle(analysis, plan, files)

        from repro_forge.reproduction.verification.static_check import validate_bundle

        report = validate_bundle(bundle)
        if not report.valid:
            bundle = await self._repair_bundle(bundle, report, plan, analysis_json)
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
            raise GenerationError(f"CodeForger validation failed: {'; '.join(errors)}")
        return bundle

    async def _generate_plan(self, analysis_json: str) -> dict[str, object]:
        import json as _json

        from repro_forge.providers.base import LLMRequest

        prompt = _FILE_PLAN_PROMPT.format(analysis_json=analysis_json)
        request = LLMRequest(
            messages=[
                {"role": "system", "content": _CODE_FORGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
            temperature=0.1,
        )
        response = await self._provider.generate(request)
        try:
            parsed = _json.loads(response.content)
        except _json.JSONDecodeError as exc:
            raise GenerationError(f"CodeForger plan was not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise GenerationError("CodeForger plan must be a JSON object")
        return cast(dict[str, object], parsed)

    async def _generate_files(
        self,
        plan: dict[str, object],
        analysis_json: str,
    ) -> list[GeneratedFile]:
        import json as _json

        from repro_forge.providers.base import LLMRequest

        file_specs: list[dict[str, object]] = []
        raw_files = plan.get("files")
        if isinstance(raw_files, list):
            file_specs = [fs for fs in raw_files if isinstance(fs, dict)]
        existing: list[dict[str, str]] = []
        files: list[GeneratedFile] = []

        for spec in file_specs:
            path = str(spec.get("path", ""))
            purpose = str(spec.get("purpose", "source"))
            ev_ids_raw = spec.get("evidence_ids", [])
            evidence_ids = list(ev_ids_raw) if isinstance(ev_ids_raw, list) else []
            is_entrypoint = bool(spec.get("is_entrypoint", False))

            existing_summary = _json.dumps(
                [{"path": e["path"], "purpose": e["purpose"]} for e in existing]
            )

            prompt = _GENERATE_FILE_PROMPT.format(
                file_path=path,
                purpose=purpose,
                evidence_ids=evidence_ids,
                analysis_json=analysis_json,
                existing_files=existing_summary,
            )
            request = LLMRequest(
                messages=[
                    {"role": "system", "content": _CODE_FORGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8192,
                temperature=0.1,
            )
            response = await self._provider.generate(request)
            try:
                result = _json.loads(response.content)
            except _json.JSONDecodeError as exc:
                raise GenerationError(f"Generated file {path!r} was not valid JSON: {exc}") from exc
            if not isinstance(result, dict):
                raise GenerationError(f"Generated file {path!r} response must be an object")

            content = str(result.get("content", ""))
            language = str(spec.get("language", "python"))

            gf = GeneratedFile(
                path=path,
                content=content,
                language=language,
                purpose=purpose,
                evidence_ids=evidence_ids,
                is_entrypoint=is_entrypoint,
            )
            files.append(gf)
            existing.append({"path": path, "purpose": purpose})

        return files

    def _assemble_bundle(
        self,
        analysis: MethodAnalysis,
        plan: dict[str, object],
        files: list[GeneratedFile],
    ) -> ReproductionBundle:
        deps: list[DependencySpec] = []
        raw_deps = plan.get("dependencies")
        if isinstance(raw_deps, list):
            for d in raw_deps:
                if isinstance(d, dict):
                    deps.append(DependencySpec(**cast(dict[str, Any], d)))

        raw_assumptions = plan.get("assumptions")
        assumptions: list[str] = []
        if isinstance(raw_assumptions, list):
            assumptions = [str(a) for a in raw_assumptions]

        raw_unresolved = plan.get("unresolved")
        unresolved: list[str] = []
        if isinstance(raw_unresolved, list):
            unresolved = [str(u) for u in raw_unresolved]

        exp_spec = ExperimentSpec(
            experiment_name="main",
            entrypoint=["python", "train.py"],
            dependencies=deps,
            timeout_seconds=3600,
            assumptions=assumptions,
            unresolved=unresolved,
        )

        raw_experiments = plan.get("experiments")
        if isinstance(raw_experiments, list) and raw_experiments:
            exp_data = raw_experiments[0]
            if isinstance(exp_data, dict):
                raw_ep = exp_data.get("entrypoint")
                entrypoint = (
                    cast(list[str], raw_ep) if isinstance(raw_ep, list) else exp_spec.entrypoint
                )
                exp_spec = ExperimentSpec(
                    experiment_name=str(exp_data.get("experiment_name", "main")),
                    entrypoint=entrypoint,
                    dependencies=deps,
                    timeout_seconds=int(exp_data.get("timeout_seconds", 3600)),
                    random_seed=int(exp_data.get("random_seed", 42)),
                    resource_limits=cast(dict[str, object], exp_data.get("resource_limits", {})),
                    runtime_profile=str(exp_data.get("runtime_profile", "python-cpu")),
                    artifact_allowlist=cast(list[str], exp_data.get("artifact_allowlist", [])),
                    assumptions=assumptions,
                    unresolved=unresolved,
                )

        analysis_payload = analysis.model_dump(mode="json")
        risk_warnings = [
            f"dependency {dependency.name} is not locked"
            for dependency in deps
            if not dependency.locked
        ]
        bundle = ReproductionBundle(
            paper_id=analysis.paper_id,
            method_analysis_hash=_sha256(canonical_json(analysis_payload)),
            files=files,
            experiments=[exp_spec],
            source_evidence_ids=_collect_evidence_ids(analysis),
            assumptions=assumptions,
            unresolved=unresolved,
            risk_warnings=risk_warnings,
            generation_trace=["plan:ok", f"files:{len(files)}", "validation:pending"],
        )
        return bundle

    async def _repair_bundle(
        self,
        bundle: ReproductionBundle,
        report: object,
        plan: dict[str, object],
        analysis_json: str,
    ) -> ReproductionBundle:
        import json as _json

        from repro_forge.providers.base import LLMRequest
        from repro_forge.reproduction.verification.static_check import ValidationReport

        if not isinstance(report, ValidationReport) or report.valid:
            return bundle

        repaired_files = [file for file in bundle.files if file.path != "reproforge-manifest.json"]
        for i, f in enumerate(repaired_files):
            if f.language != "python":
                continue
            ok, _ = _check_python_source(f.content)
            if ok:
                continue

            existing_summary = _json.dumps(
                [
                    {
                        "path": gf.path,
                        "content_preview": gf.content[:200],
                    }
                    for j, gf in enumerate(repaired_files)
                    if j != i
                ]
            )
            errors = report.ast_errors if hasattr(report, "ast_errors") else []
            error_text = "\n".join(e for e in errors if f.path in e)
            if not error_text:
                comp_errors = report.compile_errors if hasattr(report, "compile_errors") else []
                error_text = "\n".join(e for e in comp_errors if f.path in e)
            if not error_text:
                error_text = "Unknown validation error"

            prompt = _REPAIR_FILE_PROMPT.format(
                file_path=f.path,
                errors=error_text,
                existing_files=existing_summary,
            )
            request = LLMRequest(
                messages=[
                    {"role": "system", "content": _CODE_FORGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8192,
                temperature=0.1,
            )
            response = await self._provider.generate(request)
            try:
                result = _json.loads(response.content)
            except _json.JSONDecodeError as exc:
                raise GenerationError(f"Repair for {f.path!r} was not valid JSON: {exc}") from exc
            if not isinstance(result, dict):
                raise GenerationError(f"Repair for {f.path!r} must be a JSON object")

            new_content = str(result.get("content", f.content))
            repaired_files[i] = GeneratedFile(
                path=f.path,
                content=new_content,
                language=f.language,
                purpose=f.purpose,
                evidence_ids=f.evidence_ids,
                is_entrypoint=f.is_entrypoint,
            )

        return ReproductionBundle(
            paper_id=bundle.paper_id,
            method_analysis_hash=bundle.method_analysis_hash,
            files=repaired_files,
            experiments=bundle.experiments,
            source_evidence_ids=bundle.source_evidence_ids,
            assumptions=bundle.assumptions,
            unresolved=bundle.unresolved,
            risk_warnings=bundle.risk_warnings,
            generation_trace=[*bundle.generation_trace, "repair:attempted"],
        )
