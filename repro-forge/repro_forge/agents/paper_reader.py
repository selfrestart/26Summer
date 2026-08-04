"""PaperReader agent — reads academic papers and produces structured notes.

Implements a ReAct-style agent that strategically reads paper sections
and compiles a ``PaperNote`` with TL;DR, contributions, methodology
analysis, and key findings.
"""

from __future__ import annotations

import json

from repro_forge.core.base import BaseAgent
from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import Observation
from repro_forge.core.types import TaskResult
from repro_forge.core.types import TaskSpec
from repro_forge.core.types import TaskStatus
from repro_forge.core.types import Thought
from repro_forge.paper.chunker import PaperChunker
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperChunk
from repro_forge.paper.schemas import PaperNote
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMToolCall

PAPER_READER_SYSTEM_PROMPT = """You are an experienced CS paper reviewer. Your task is to read
a research paper and produce a structured analysis.

You have access to these tools:
- list_sections: returns all section titles in the paper
- read_section(section_title, chunk_index=0): returns one bounded part of a section
- search_paper(query): search for specific terms in the paper

READING STRATEGY:
1. First, list all sections to understand the paper's structure.
2. Always start with the abstract.
3. Read the introduction to understand context and contributions.
4. Read the method section for technical details.
5. Read the experiments/results for evaluation.
6. Only read other sections if you need more detail.

After reading, produce a structured analysis in this JSON format:
{
  "tldr": "3-sentence plain-language summary",
  "contributions": [{"description": "...", "supporting_sections": ["..."]}],
  "methodology_summary": "Brief description of the technical approach",
  "key_findings": [{"description": "...", "metric_name": "...", "metric_value": "...", "dataset": "..."}],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "questions": ["open questions or concerns"]
}

When you have enough information, respond with DONE followed by the JSON."""

PAPER_READER_TOOLS = [
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
            "description": "Read one token-bounded chunk of a specific section",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_title": {
                        "type": "string",
                        "description": "Exact section title to read",
                    },
                    "chunk_index": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                        "description": "Zero-based chunk within a long section",
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
            "description": "Search for specific terms in the full paper text",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
]


class PaperReader(BaseAgent):
    """Agent that reads academic papers and produces structured reading notes.

    Inherits the ReAct execution loop from ``BaseAgent`` and implements
    paper-specific think/act/observe logic.

    Usage::

        paper = pdf_parser.parse("path/to/paper.pdf")
        reader = PaperReader(config, provider)
        note: PaperNote = await reader.read(paper)
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        provider: BaseProvider | None = None,
    ) -> None:
        effective_config = config or AgentConfig(
            agent_type=AgentType.PAPER_READER,
            model=provider.model if provider is not None else "gpt-4o",
            max_steps=12,
            temperature=0.0,
        )
        super().__init__(config=effective_config, provider=provider)  # type: ignore[arg-type]
        self._paper: Paper | None = None
        self._chunks: list[PaperChunk] = []
        self._read_sections: list[str] = []
        self._conversation: list[dict[str, object]] = []
        self._pending_tool_calls: list[LLMToolCall] = []
        self._step_token_usage: dict[int, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def read(self, paper: Paper) -> PaperNote:
        """Read a paper and produce a structured note.

        Args:
            paper: The parsed ``Paper`` to read.

        Returns:
            A ``PaperNote`` with the agent's structured analysis.
        """
        chunker = PaperChunker(max_tokens=4000)
        if self.provider is None:
            raise ValueError("PaperReader requires a BaseProvider to read a paper")
        self._paper = paper
        self._chunks = chunker.chunk(paper)
        if not self._chunks:
            raise ValueError("Paper has no readable content")

        task = TaskSpec(
            title=f"Read: {paper.metadata.title or 'Untitled'}",
            description=(f"Read and analyze paper with {len(paper.sections)} sections"),
            input={"paper_title": paper.metadata.title},
            max_steps=self.config.max_steps,
        )

        result = await self.run(task)
        for step in self._trace.steps:
            step.token_usage = self._step_token_usage.get(step.step_index, {})

        if result.status == TaskStatus.FAILED:
            raise RuntimeError(f"PaperReader failed: {result.error_message}")

        note_data = result.output.get("note", {})
        if isinstance(note_data, str):
            note_data = json.loads(note_data)
        note = PaperNote(**note_data)
        note.paper_id = paper.metadata.arxiv_id
        note.arxiv_id = paper.metadata.arxiv_id
        note.title = paper.metadata.title
        note.reading_trace = self._read_sections
        note.total_tokens_used = self._trace.total_tokens
        return note

    # ------------------------------------------------------------------
    # Setup / Teardown
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        await super().setup()
        self._read_sections = []
        self._pending_tool_calls = []
        self._step_token_usage = {}
        self._conversation = [
            {"role": "system", "content": PAPER_READER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "A paper has been loaded. Start by listing its sections, "
                    "then read them strategically. Output DONE with JSON "
                    "when you have enough information."
                ),
            },
        ]

    # ------------------------------------------------------------------
    # ReAct loop methods
    # ------------------------------------------------------------------

    async def think(self, task: TaskSpec) -> Thought:
        if self._pending_tool_calls:
            return Thought(content="")

        messages = self._conversation.copy()
        response = await self.provider.generate(
            LLMRequest(
                messages=messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=2048,
                tools=PAPER_READER_TOOLS,
                tool_choice="auto",
            )
        )
        self._trace.total_tokens += response.usage.get("total_tokens", 0)
        self._step_token_usage[len(self._trace.steps)] = dict(response.usage)
        assistant_message: dict[str, object] = {
            "role": "assistant",
            "content": response.content or "",
        }
        if response.tool_calls:
            self._pending_tool_calls = list(response.tool_calls)
            assistant_message["tool_calls"] = [
                self._tool_call_payload(call.call_id, call.name, call.arguments)
                for call in self._pending_tool_calls
            ]
        else:
            self._pending_tool_calls = []
        self._conversation.append(assistant_message)
        return Thought(content=response.content or "")

    async def act(self, thought: Thought) -> Action:
        if self._pending_tool_calls:
            native_tool_call = self._pending_tool_calls.pop(0)
            return Action(
                id=native_tool_call.call_id,
                tool_name=native_tool_call.name,
                tool_input=native_tool_call.arguments,
                reasoning="Executing provider-requested tool call",
            )

        content = thought.content.strip()

        if "DONE" in content.upper() and "{" in content:
            return Action(
                tool_name="finalize",
                tool_input={
                    "raw_output": self._extract_json(content),
                    "sections_read": self._read_sections.copy(),
                },
                reasoning="Reading complete, producing final analysis",
            )

        if content:
            tool_call = self._detect_tool_call(content)
            if tool_call:
                self._attach_synthetic_tool_call(tool_call, thought)
                return tool_call

        fallback_action = Action(
            tool_name="list_sections",
            tool_input={},
            reasoning="Need to see what sections are available",
        )
        self._attach_synthetic_tool_call(fallback_action, thought)
        return fallback_action

    async def observe(self, action: Action) -> Observation:
        if action.tool_name == "finalize":
            return Observation(
                action_id=action.id,
                content="Analysis complete",
                metadata=action.tool_input,
            )

        if action.tool_name == "list_sections":
            if self._paper:
                titles = self._paper.section_titles
            else:
                titles = [c.section_title for c in self._chunks]
            unique_titles = list(dict.fromkeys(titles))
            result = "Sections:\n" + "\n".join(f"  - {t}" for t in unique_titles)
            self._conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": action.id,
                    "content": result,
                }
            )
            return Observation(action_id=action.id, content=result)

        if action.tool_name == "read_section":
            section_title = action.tool_input.get("section_title")
            if not isinstance(section_title, str) or not section_title.strip():
                return self._tool_error_observation(
                    action,
                    "read_section requires a non-empty 'section_title' string",
                )
            section_title = section_title.strip()
            chunk_index = action.tool_input.get("chunk_index", 0)
            if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 0:
                return self._tool_error_observation(
                    action,
                    "read_section requires 'chunk_index' to be a non-negative integer",
                )
            try:
                content = self._find_section_content(section_title, chunk_index)
            except LookupError as exc:
                return self._tool_error_observation(action, str(exc))
            self._read_sections.append(section_title)
            self._conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": action.id,
                    "content": content,
                }
            )
            return Observation(action_id=action.id, content=content)

        if action.tool_name == "search_paper":
            query = action.tool_input.get("query")
            if not isinstance(query, str) or not query.strip():
                return self._tool_error_observation(
                    action,
                    "search_paper requires a non-empty 'query' string",
                )
            query = query.strip()
            result = self._search_paper_content(query)
            self._conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": action.id,
                    "content": result,
                }
            )
            return Observation(action_id=action.id, content=result)

        return self._tool_error_observation(
            action,
            f"Unknown tool: {action.tool_name}",
        )

    async def should_stop(self, observation: Observation) -> bool:
        if observation.metadata.get("raw_output"):
            return True
        return len(self._read_sections) >= self.config.max_steps

    async def finalize(self, task: TaskSpec) -> TaskResult:
        for step in self._trace.steps:
            if step.action and step.action.tool_name == "finalize":
                raw = step.action.tool_input.get("raw_output", "")
                try:
                    note_data = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    note_data = {"tldr": raw[:500]}
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    output={
                        "note": note_data,
                        "sections_read": self._read_sections,
                    },
                    trace=self._trace,
                )

        while self._pending_tool_calls:
            skipped_call = self._pending_tool_calls.pop(0)
            self._conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": skipped_call.call_id,
                    "content": (
                        f"Tool '{skipped_call.name}' was skipped because the reading step budget "
                        "was exhausted."
                    ),
                }
            )
        self._conversation.append(
            {
                "role": "user",
                "content": (
                    "The reading step budget is exhausted. Do not call tools. "
                    "Return only the final analysis JSON in the requested schema."
                ),
            }
        )
        response = await self.provider.generate(
            LLMRequest(
                messages=self._conversation.copy(),
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=2048,
            )
        )
        self._trace.total_tokens += response.usage.get("total_tokens", 0)
        raw_output = self._extract_json(response.content)
        try:
            note_data = json.loads(raw_output)
        except json.JSONDecodeError:
            note_data = {"tldr": response.content[:500]}
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output={
                "note": note_data,
                "sections_read": self._read_sections,
            },
            trace=self._trace,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tool_error_observation(self, action: Action, error: str) -> Observation:
        content = f"Tool error: {error}"
        self._conversation.append(
            {
                "role": "tool",
                "tool_call_id": action.id,
                "content": content,
            }
        )
        return Observation(
            action_id=action.id,
            content=content,
            error=error,
        )

    @staticmethod
    def _tool_call_payload(
        call_id: str,
        name: str,
        arguments: object,
    ) -> dict[str, object]:
        return {
            "id": call_id,
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(arguments),
            },
        }

    def _attach_synthetic_tool_call(self, action: Action, thought: Thought) -> None:
        payload = self._tool_call_payload(action.id, action.tool_name, action.tool_input)
        if self._conversation and self._conversation[-1].get("role") == "assistant":
            self._conversation[-1]["tool_calls"] = [payload]
            return
        self._conversation.append(
            {
                "role": "assistant",
                "content": thought.content,
                "tool_calls": [payload],
            }
        )

    def _find_section_content(self, title: str, chunk_index: int = 0) -> str:
        """Find one bounded part of a section (exact match first, then fuzzy)."""
        title_lower = title.lower().strip()

        section = None
        if self._paper:
            section = next(
                (s for s in self._paper.sections if s.title.lower().strip() == title_lower),
                None,
            )
            if section is None:
                section = next(
                    (s for s in self._paper.sections if title_lower in s.title.lower()),
                    None,
                )

        if section is not None:
            estimated_tokens = max(
                section.token_count,
                max(1, (len(section.content) + 3) // 4),
            )
            if estimated_tokens <= 4000:
                if chunk_index != 0:
                    raise IndexError(
                        f"chunk_index {chunk_index} is out of range for section "
                        f"'{section.title}'; valid index: 0"
                    )
                return section.content

            section_title = section.title.lower().strip()
            matching_chunks = [
                chunk
                for chunk in self._chunks
                if chunk.section_title.lower().strip() == section_title
            ]
            if not matching_chunks:
                matching_chunks = PaperChunker(max_tokens=4000).chunk(Paper(sections=[section]))
            if chunk_index >= len(matching_chunks):
                raise IndexError(
                    f"chunk_index {chunk_index} is out of range for section "
                    f"'{section.title}'; valid range: 0-{len(matching_chunks) - 1}"
                )
            chunk = matching_chunks[chunk_index]
            position = chunk_index + 1
            guidance = ""
            if position < len(matching_chunks):
                guidance = (
                    f"\n\nContinue with read_section(section_title='{section.title}', "
                    f"chunk_index={chunk_index + 1})."
                )
            return (
                f"Section '{section.title}', chunk {position} of {len(matching_chunks)}:\n"
                f"{chunk.text}{guidance}"
            )

        matching_chunks = [
            chunk for chunk in self._chunks if title_lower in chunk.section_title.lower()
        ]
        if matching_chunks:
            if chunk_index >= len(matching_chunks):
                raise IndexError(
                    f"chunk_index {chunk_index} is out of range for section "
                    f"'{title}'; valid range: 0-{len(matching_chunks) - 1}"
                )
            return matching_chunks[chunk_index].text

        available = (
            self._paper.section_titles if self._paper else [c.section_title for c in self._chunks]
        )
        raise LookupError(f"Section '{title}' not found. Available: " + ", ".join(available))

    def _search_paper_content(self, query: str) -> str:
        """Search paper sections for a keyword and retain source attribution."""
        query_lower = query.lower()
        results: list[str] = []
        if self._paper:
            for section in self._paper.sections:
                searchable = f"{section.title}\n{section.content}"
                if query_lower in searchable.lower():
                    snippet = self._snippet(searchable, query, 200)
                    results.append(f"[{section.title}] {snippet}")
        else:
            for chunk in self._chunks:
                if query_lower in chunk.text.lower():
                    snippet = self._snippet(chunk.text, query, 200)
                    results.append(f"[{chunk.section_title}] {snippet}")
        if not results:
            return f"No matches for '{query}'"
        return "\n".join(results[:5])

    @staticmethod
    def _snippet(text: str, query: str, context: int = 200) -> str:
        """Extract a snippet around the query term."""
        idx = text.lower().find(query.lower())
        if idx < 0:
            return text[:context] + "..."
        start = max(0, idx - context // 2)
        end = min(len(text), idx + len(query) + context // 2)
        snippet = text[start:end]
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{snippet}{suffix}"

    @staticmethod
    def _extract_json(content: str) -> str:
        """Extract JSON block from agent output."""
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
        """Heuristically detect tool calls from LLM text output."""
        content_lower = content.lower()

        if "list_sections" in content_lower or "list sections" in content_lower:
            return Action(
                tool_name="list_sections",
                tool_input={},
                reasoning="Listing all paper sections",
            )

        read_patterns = ["read_section(", "read section", "read the", "let me read"]
        for pattern in read_patterns:
            if pattern in content_lower:
                for chunk_title in [
                    "abstract",
                    "introduction",
                    "related work",
                    "method",
                    "approach",
                    "model",
                    "architecture",
                    "experiment",
                    "evaluation",
                    "result",
                    "discussion",
                    "conclusion",
                ]:
                    if chunk_title in content_lower:
                        return Action(
                            tool_name="read_section",
                            tool_input={"section_title": chunk_title},
                            reasoning=f"Reading {chunk_title} section",
                        )
                return Action(
                    tool_name="read_section",
                    tool_input={"section_title": "method"},
                    reasoning="Reading method section by default",
                )

        if "search_paper" in content_lower or "search" in content_lower:
            import re

            queries = re.findall(r"search(?:_paper)?\s*[\(\)]?\s*['\"]?([^'\"]+)['\"]?", content)
            query = queries[0] if queries else "attention"
            return Action(
                tool_name="search_paper",
                tool_input={"query": query},
                reasoning=f"Searching for '{query}'",
            )

        return None
