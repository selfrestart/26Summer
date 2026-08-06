"""Methodologist agent — extracts evidence-grounded methodology from papers.

Implements a ReAct agent that reads paper sections strategically and
produces a ``MethodAnalysis`` with evidence-referenced algorithms,
architecture, training recipes, and evaluation protocols.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError

from repro_forge.core.base import BaseAgent
from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import Observation
from repro_forge.core.types import TaskResult
from repro_forge.core.types import TaskSpec
from repro_forge.core.types import TaskStatus
from repro_forge.core.types import Thought
from repro_forge.paper.extractor.evidence import PaperEvidenceView
from repro_forge.paper.extractor.schemas import EquationParseStatus
from repro_forge.paper.extractor.schemas import EvidenceRef
from repro_forge.paper.extractor.schemas import EvidenceStatus
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.paper.schemas import PaperNote
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMToolCall

METHODOLOGIST_SYSTEM_PROMPT = """You are a CS research methodologist. Extract a structured, evidence-grounded analysis of the paper's methodology.

You have access to these tools:
- list_sections: view all section titles
- read_section(title, chunk_index=0): read one bounded part of a section
- search_paper(query): search for specific terms, hyperparameters, metrics
- get_paper_note(): get the P1 reading note (if available) as context hints

EXTRACTION RULES:
1. Every method step, architecture component, reported configuration, dataset,
   metric, and result claim MUST reference a section title and quote.
2. If a value is explicitly stated, use verified status with the quote.
3. If you must infer, mark as inferred and explain.
4. If the paper doesn't report something, mark as not_reported — NEVER fabricate.
5. If different sections conflict, mark as conflicting and note both sources.
6. Equations must only be captured from the actual paper text; if formulas are not readable in the text layer, output not_available.

When you have read enough sections, output DONE followed by a JSON object with these fields:
{
  "problem_statement": "What problem does the paper solve?",
  "algorithms": [
    {
      "name": "...", "purpose": "...",
      "steps": [{"order": 1, "description": "...", "evidence": {"section_title": "...", "quote": "..."}}],
      "assumptions": ["..."],
      "evidence": {"section_title": "...", "quote": "..."}
    }
  ],
  "architecture": [
    {"name": "...", "component_type": "...", "description": "...", "parameters": {}, "evidence": {"section_title": "...", "quote": "..."}}
  ],
  "training_recipe": {
    "learning_rate": {"value": null, "raw_text": "", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}},
    "batch_size": {"value": null, "raw_text": "", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}},
    "epochs": {"value": null, "raw_text": "", "status": "not_reported"},
    "optimizer": {"value": null, "raw_text": "", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}}
  },
  "evaluation_protocol": {
    "datasets": [{"value": "ImageNet", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}}],
    "metrics": [{"value": "Top-1 Accuracy", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}}],
    "reported_claims": [{"dataset": "...", "metric_name": "...", "reported_value": "...", "status": "verified", "evidence": {"section_title": "...", "quote": "..."}}]
  },
  "equations": [{"equation_id": "eq_1", "label": "(1)", "raw_text": "...", "parse_status": "captured"}],
  "reproducibility_gaps": [{"category": "config", "description": "...", "impact": "..."}],
  "assumptions": [{"value": "...", "status": "inferred", "notes": "..."}]
}

IMPORTANT: quote_hash, source_hash, section_id, and evidence_id can be left empty — they will be filled by the validation layer."""

METHODOLOGIST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_sections",
            "description": "List all section titles in the paper",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_section",
            "description": "Read one bounded part of a section",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_title": {"type": "string", "description": "Section title to read"},
                    "chunk_index": {
                        "type": "integer",
                        "description": "Chunk index for long sections (0-based)",
                        "default": 0,
                    },
                },
                "required": ["section_title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_paper",
            "description": "Search for specific terms in the paper",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_note",
            "description": "Get the P1 paper reading note as context hints",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class Methodologist(BaseAgent):
    """Agent that extracts evidence-grounded methodology from papers.

    Usage::

        view = PaperEvidenceView(paper)
        methodologist = Methodologist(config, provider)
        analysis: MethodAnalysis = await methodologist.analyze(view, paper_note)
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        provider: BaseProvider | None = None,
    ) -> None:
        if provider is None:
            raise ValueError("Methodologist requires a provider")
        effective_config = config or AgentConfig(
            agent_type=AgentType.METHODOLOGIST,
            max_steps=15,
            temperature=0.0,
            model=provider.model if provider is not None else "gpt-4o",
        )
        # AgentConfig historically defaults to ``gpt-4o``.  When a provider
        # is injected (for example DeepSeek), inherit its model unless the
        # caller selected another model explicitly.  This keeps the public
        # constructor backwards compatible while preventing an accidental
        # cross-provider request.
        if (
            provider is not None
            and config is not None
            and config.model == "gpt-4o"
            and "model" not in config.model_fields_set
            and provider.model != config.model
        ):
            effective_config = config.model_copy(update={"model": provider.model})
        super().__init__(config=effective_config, provider=provider)
        self._view: PaperEvidenceView | None = None
        self._paper_note: PaperNote | None = None
        self._conversation: list[dict[str, object]] = []
        self._repair_attempted = False
        self._pending_tool_calls: list[LLMToolCall] = []

    async def analyze(
        self,
        view: PaperEvidenceView,
        paper_note: PaperNote | None = None,
    ) -> MethodAnalysis:
        """Extract methodology from a paper.

        Args:
            view: A ``PaperEvidenceView`` wrapping the paper.
            paper_note: Optional P1 reading note for context hints.

        Returns:
            A ``MethodAnalysis`` with evidence-grounded methodology.

        Raises:
            RuntimeError: If extraction fails after repair attempt.
        """
        self._view = view
        self._paper_note = paper_note
        self._repair_attempted = False
        self._pending_tool_calls = []

        task = TaskSpec(
            title=f"Analyze: {view.paper.metadata.title or 'Untitled'}",
            description=f"Extract methodology from {len(view.paper.sections)} sections",
            max_steps=self.config.max_steps,
        )

        result = await self.run(task)

        if result.status == TaskStatus.FAILED:
            raise RuntimeError(f"Methodologist failed: {result.error_message}")

        analysis_data = result.output.get("analysis", {})
        if isinstance(analysis_data, str):
            analysis_data = json.loads(analysis_data)

        if isinstance(analysis_data, dict):
            analysis_data["paper_id"] = view.paper.metadata.arxiv_id
            analysis_data["title"] = view.paper.metadata.title
            analysis_data["extraction_trace"] = self._format_extraction_trace()

        # Post-process: fill and validate evidence metadata from the canonical view.
        self._sanitize_equations(analysis_data)
        self._populate_evidence_metadata(analysis_data)
        self._downgrade_invalid_evidence(analysis_data)
        self._sanitize_equations(analysis_data)
        analysis = MethodAnalysis(**analysis_data)
        analysis.total_tokens_used = self._trace.total_tokens
        analysis.recalculate_evidence_coverage()
        return analysis

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        await super().setup()
        self._conversation = [
            {"role": "system", "content": METHODOLOGIST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "A paper has been loaded. Start by listing sections, "
                    "then read the method/approach/architecture sections, "
                    "then search for specific hyperparameters and metrics. "
                    "Output DONE with the JSON analysis when complete."
                ),
            },
        ]
        if self._paper_note:
            note_hint = (
                f"\n[System: P1 PaperNote available with TLDR: {self._paper_note.tldr[:300]}]"
            )
            self._conversation.append({"role": "system", "content": note_hint})

    # ------------------------------------------------------------------
    # ReAct loop
    # ------------------------------------------------------------------

    async def think(self, task: TaskSpec) -> Thought:
        if self._pending_tool_calls:
            return Thought(content="Continue pending native tool calls.")
        messages = self._conversation.copy()
        response = await self.provider.generate(
            LLMRequest(
                messages=messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=4096,
                tools=METHODOLOGIST_TOOLS,
                tool_choice="auto",
            )
        )
        self._trace.total_tokens += response.usage.get("total_tokens", 0)
        if response.tool_calls:
            self._pending_tool_calls = list(response.tool_calls)
            self._conversation.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": call.call_id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments, ensure_ascii=False),
                            },
                        }
                        for call in response.tool_calls
                    ],
                }
            )
        else:
            self._conversation.append({"role": "assistant", "content": response.content or ""})
        return Thought(content=response.content or "")

    async def act(self, thought: Thought) -> Action:
        if self._pending_tool_calls:
            call = self._pending_tool_calls.pop(0)
            return Action(
                id=call.call_id,
                tool_name=call.name,
                tool_input=call.arguments,
                reasoning="Native provider tool call",
            )
        content = thought.content.strip()

        if "DONE" in content.upper() and "{" in content:
            return Action(
                tool_name="finalize",
                tool_input={"raw_output": self._extract_json(content)},
                reasoning="Analysis complete",
            )

        return self._detect_tool_call(content) or Action(
            tool_name="list_sections",
            tool_input={},
            reasoning="Need to see what sections are available",
        )

    async def observe(self, action: Action) -> Observation:
        if action.tool_name == "finalize":
            return Observation(
                action_id=action.id,
                content="Analysis complete",
                metadata=action.tool_input,
            )

        result: str

        if action.tool_name == "list_sections":
            result = self._view.list_sections() if self._view else "No paper loaded"

        elif action.tool_name == "read_section":
            title = action.tool_input.get("section_title", "")
            chunk_idx = action.tool_input.get("chunk_index", 0)
            result = self._view.read_section(title, chunk_idx) if self._view else "No paper loaded"

        elif action.tool_name == "search_paper":
            query = action.tool_input.get("query", "")
            if self._view:
                results = self._view.search(query)
                result = (
                    "\n".join(f"[{r['section_title']}] {r['snippet']}" for r in results[:5])
                    or f"No matches for '{query}'"
                )
            else:
                result = "No paper loaded"

        elif action.tool_name == "get_paper_note":
            if self._paper_note:
                result = json.dumps(
                    {
                        "tldr": self._paper_note.tldr[:500],
                        "contributions": [
                            c.description for c in self._paper_note.contributions[:5]
                        ],
                        "methodology_summary": self._paper_note.methodology_summary[:500],
                        "key_findings": [
                            {"metric": k.metric_name, "value": k.metric_value}
                            for k in self._paper_note.key_findings[:5]
                        ],
                    }
                )
            else:
                result = "No P1 reading note available"

        else:
            result = f"Unknown tool: {action.tool_name}"

        self._conversation.append(
            {
                "role": "tool",
                "tool_call_id": action.id,
                "content": result,
            }
        )
        return Observation(action_id=action.id, content=result)

    async def should_stop(self, observation: Observation) -> bool:
        return bool(observation.metadata.get("raw_output"))

    async def finalize(self, task: TaskSpec) -> TaskResult:
        raw_output = ""
        for step in self._trace.steps:
            if step.action and step.action.tool_name == "finalize":
                raw_output = step.action.tool_input.get("raw_output", "")
                break

        # A parallel native-tool batch may cross the configured action-step
        # boundary. Finish that protocol turn before asking the model to repair
        # an output that it has not had a chance to produce yet.
        if not raw_output and self._conversation and self._conversation[-1].get("role") == "tool":
            return await self._retry_loop(task)

        try:
            analysis_data = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        except json.JSONDecodeError:
            if not self._repair_attempted and self._view:
                return await self._attempt_repair(task, raw_output)
            return self._failed_result(task, f"Invalid JSON: {raw_output[:200]}")

        if isinstance(analysis_data, dict):
            self._sanitize_equations(analysis_data)
            self._populate_evidence_metadata(analysis_data)
            self._downgrade_invalid_evidence(analysis_data)
            self._sanitize_equations(analysis_data)
        validated = self._validate_analysis(analysis_data)
        if isinstance(validated, str):
            if not self._repair_attempted and self._view:
                self._conversation.append(
                    {
                        "role": "user",
                        "content": f"Validation errors in your output:\n{validated}\nPlease fix these issues and output DONE with the corrected JSON.",
                    }
                )
                self._repair_attempted = True
                return await self._retry_loop(task)
            return self._failed_result(task, validated)

        try:
            normalized = MethodAnalysis(**validated).model_dump()
        except ValidationError as exc:
            error = f"Schema validation failed: {exc}"
            if not self._repair_attempted and self._view:
                self._conversation.append(
                    {
                        "role": "user",
                        "content": f"Validation errors in your output:\n{error}\nPlease fix these issues and output DONE with the corrected JSON.",
                    }
                )
                self._repair_attempted = True
                return await self._retry_loop(task)
            return self._failed_result(task, error)

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output={"analysis": normalized},
            trace=self._trace,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _populate_evidence_metadata(self, data: dict[str, object]) -> None:
        """Fill source_hash and section_id from PaperEvidenceView."""
        if not self._view:
            return

        import hashlib

        for evidence in self._iter_evidence_dicts(data):
            title = str(evidence.get("section_title", ""))
            quote = str(evidence.get("quote", ""))
            # Empty refs are schema placeholders for not-reported fields.
            # They must not be promoted into synthetic evidence records.
            if not title.strip() and not quote.strip():
                continue
            evidence["source_hash"] = self._view.source_hash
            evidence["section_id"] = self._view.get_section_id(title)
            evidence["paper_id"] = self._view.paper.metadata.arxiv_id
            normalized_quote = PaperEvidenceView.normalize_quote(quote)
            seed = "|".join(
                [
                    str(evidence["paper_id"]),
                    str(evidence["section_id"]),
                    normalized_quote,
                ]
            )
            evidence["evidence_id"] = "ev_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
            evidence["quote_hash"] = hashlib.sha256(normalized_quote.encode("utf-8")).hexdigest()[
                :16
            ]
            if evidence.get("chunk_index") is None:
                evidence["chunk_index"] = self._view.find_quote_chunk(quote, title)
            for page_key in ("page_start", "page_end"):
                if evidence.get(page_key) == 0:
                    evidence[page_key] = None

    @staticmethod
    def _sanitize_equations(data: dict[str, object]) -> None:
        """Do not publish captured equations without source text evidence."""
        equations = data.get("equations")
        if not isinstance(equations, list):
            return
        for equation in equations:
            if not isinstance(equation, dict):
                continue
            if equation.get("parse_status") != EquationParseStatus.CAPTURED.value:
                continue
            raw_text = str(equation.get("raw_text", "")).strip()
            evidence = equation.get("evidence")
            has_source_quote = (
                isinstance(evidence, dict)
                and bool(str(evidence.get("quote", "")).strip())
                and str(evidence.get("status", "")).lower()
                in {
                    "",
                    EvidenceStatus.VERIFIED.value,
                }
            )
            if not raw_text or not has_source_quote:
                equation["parse_status"] = (
                    EquationParseStatus.PARTIAL.value
                    if raw_text
                    else EquationParseStatus.NOT_AVAILABLE.value
                )

    def _downgrade_invalid_evidence(self, data: dict[str, object]) -> None:
        """Prevent invalid model references from being published as verified facts."""
        if not self._view:
            return

        evidence_dicts = list(self._iter_evidence_dicts(data))
        evidence_ids = {id(evidence) for evidence in evidence_dicts}
        for evidence in evidence_dicts:
            try:
                declared_status = str(evidence.get("status", "")).lower()
                if declared_status in {
                    EvidenceStatus.INFERRED.value,
                    EvidenceStatus.CONFLICTING.value,
                    EvidenceStatus.NOT_REPORTED.value,
                }:
                    status = declared_status
                else:
                    status = self._view.verify_evidence(EvidenceRef.model_validate(evidence))
            except Exception:
                status = EvidenceStatus.UNVERIFIED.value
            evidence["status"] = status

        def _check_parent(obj: object) -> None:
            if isinstance(obj, dict):
                for value in obj.values():
                    _check_parent(value)
                if (
                    id(obj) not in evidence_ids
                    and obj.get("status") == EvidenceStatus.VERIFIED.value
                ):
                    evidence = obj.get("evidence")
                    if not isinstance(evidence, dict):
                        obj["status"] = EvidenceStatus.UNVERIFIED.value
                    elif evidence.get("status") != EvidenceStatus.VERIFIED.value:
                        evidence_status = str(evidence.get("status", ""))
                        obj["status"] = (
                            evidence_status
                            if evidence_status in EvidenceStatus._value2member_map_
                            else EvidenceStatus.UNVERIFIED.value
                        )
            elif isinstance(obj, list):
                for value in obj:
                    _check_parent(value)

        _check_parent(data)

    def _validate_analysis(self, data: Any) -> dict[str, object] | str:
        """Validate the analysis against basic structural rules."""
        if not isinstance(data, dict):
            return "Analysis must be a JSON object"
        errors: list[str] = []

        if "problem_statement" not in data:
            errors.append("Missing problem_statement")

        algorithms = data.get("algorithms", [])
        if isinstance(algorithms, list):
            for algo in algorithms:
                if isinstance(algo, dict):
                    if not algo.get("name"):
                        errors.append("Algorithm missing name")
                    steps = algo.get("steps", [])
                    if isinstance(steps, list):
                        for step in steps:
                            if isinstance(step, dict) and not step.get("description"):
                                errors.append("AlgorithmStep missing description")

        claims: list[object] = []
        legacy_claims = data.get("reported_claims", [])
        if isinstance(legacy_claims, list):
            claims.extend(legacy_claims)
        evaluation_protocol = data.get("evaluation_protocol", {})
        if isinstance(evaluation_protocol, dict):
            nested_claims = evaluation_protocol.get("reported_claims", [])
            if isinstance(nested_claims, list):
                claims.extend(nested_claims)
        for claim in claims:
            if isinstance(claim, dict):
                if not claim.get("dataset"):
                    errors.append("ReportedClaimDraft missing dataset")
                if not claim.get("metric_name"):
                    errors.append("ReportedClaimDraft missing metric_name")

        if errors:
            return "; ".join(errors)
        return data

    @staticmethod
    def _iter_evidence_dicts(data: object) -> Iterator[dict[str, Any]]:
        """Yield only dictionaries occupying declared evidence fields."""
        if isinstance(data, dict):
            evidence = data.get("evidence")
            if isinstance(evidence, dict):
                yield evidence
            overrides = data.get("evidence_overrides")
            if isinstance(overrides, dict):
                for override in overrides.values():
                    if isinstance(override, dict):
                        yield override
            for value in data.values():
                yield from Methodologist._iter_evidence_dicts(value)
        elif isinstance(data, list):
            for value in data:
                yield from Methodologist._iter_evidence_dicts(value)

    def _format_extraction_trace(self) -> list[str]:
        """Expose tool names and outcomes without model reasoning or paper text."""
        trace: list[str] = []
        for step in self._trace.steps:
            tool_name = step.action.tool_name if step.action else "none"
            outcome = (
                "error" if step.observation is not None and step.observation.is_error else "ok"
            )
            trace.append(f"{step.step_index}:{tool_name}:{outcome}")
        return trace

    async def _attempt_repair(self, task: TaskSpec, raw_output: str) -> TaskResult:
        self._repair_attempted = True
        self._conversation.append(
            {
                "role": "user",
                "content": f"Your output was not valid JSON. Please fix and output DONE with corrected JSON.\nOriginal: {raw_output[:500]}",
            }
        )
        return await self._retry_loop(task)

    async def _retry_loop(self, task: TaskSpec) -> TaskResult:
        from repro_forge.core.types import AgentState
        from repro_forge.core.types import TraceStep

        self._state = AgentState.THINKING
        continuation_budget = min(
            5,
            max(self.config.max_steps, len(self._pending_tool_calls) + 1),
        )
        for _ in range(continuation_budget):
            thought = await self.think(task)
            action = await self.act(thought)
            step_index = len(self._trace.steps)
            step = TraceStep(
                step_index=step_index,
                thought=thought,
                action=action,
            )
            observation = await self.observe(action)
            step.observation = observation
            self._trace.steps.append(step)

            if action.tool_name == "finalize":
                raw = action.tool_input.get("raw_output", "")
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    validated = self._validate_analysis(data)
                    if isinstance(validated, str):
                        raise ValueError(validated)
                    self._sanitize_equations(validated)
                    self._populate_evidence_metadata(validated)
                    self._downgrade_invalid_evidence(validated)
                    self._sanitize_equations(validated)
                    analysis = MethodAnalysis(**validated)
                    analysis.total_tokens_used = self._trace.total_tokens
                    analysis.recalculate_evidence_coverage()
                    return TaskResult(
                        task_id=task.id,
                        status=TaskStatus.SUCCESS,
                        output={"analysis": analysis.model_dump()},
                        trace=self._trace,
                    )
                except Exception as e:
                    return self._failed_result(task, f"Repair failed: {e}")
        return self._failed_result(task, "Repair exhausted max steps")

    def _failed_result(self, task: TaskSpec, error: str) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error_message=error,
            trace=self._trace,
        )

    @staticmethod
    def _extract_json(content: str) -> str:
        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                inner = parts[1].split("```")
                return inner[0].strip()
        if "```" in content:
            parts = content.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            return content[brace_start : brace_end + 1]
        return content.strip()

    @staticmethod
    def _detect_tool_call(content: str) -> Action | None:
        content_lower = content.lower()

        if "list_sections" in content_lower or "list sections" in content_lower:
            return Action(tool_name="list_sections", tool_input={}, reasoning="Listing sections")

        if "get_paper_note" in content_lower or "reading note" in content_lower:
            return Action(
                tool_name="get_paper_note", tool_input={}, reasoning="Getting reading note"
            )

        read_triggers = ["read_section", "read the", "read section", "let me read"]
        for trigger in read_triggers:
            if trigger in content_lower:
                for keyword in [
                    "abstract",
                    "introduction",
                    "method",
                    "approach",
                    "architecture",
                    "model",
                    "experiment",
                    "evaluation",
                    "implementation",
                    "setup",
                    "results",
                    "conclusion",
                    "training",
                    "appendix",
                    "discussion",
                ]:
                    if keyword in content_lower:
                        return Action(
                            tool_name="read_section",
                            tool_input={"section_title": keyword},
                            reasoning=f"Reading {keyword} section",
                        )

        if "search_paper" in content_lower or "search for" in content_lower:
            query_match = re.search(
                r"(?:search(?:_paper)?|search for)\s*(?:['\"]([^'\"]+)['\"]|(\S+))",
                content,
                re.IGNORECASE,
            )
            query = (
                query_match.group(1) or query_match.group(2) if query_match else "hyperparameters"
            )
            return Action(
                tool_name="search_paper",
                tool_input={"query": query},
                reasoning=f"Searching for {query}",
            )

        return None
