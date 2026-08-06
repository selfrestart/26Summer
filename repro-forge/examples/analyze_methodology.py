"""Example: Extract evidence-grounded methodology from a paper.

This demo uses a built-in sample paper and a fake LLM provider to
demonstrate the P2 methodology extraction pipeline without requiring
API keys or PDF files.

Usage:
    uv run python examples/analyze_methodology.py

To use with a real PDF and LLM:
    1. Install optional deps: uv sync --extra pdf --extra openai --group dev
    2. Set OPENAI_API_KEY (or DEEPSEEK_API_KEY) in .env
    3. Run: uv run python examples/analyze_methodology.py --pdf path/to/paper.pdf
"""

from __future__ import annotations

import asyncio
import json

from repro_forge.agents.methodologist import Methodologist
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.extractor.evidence import PaperEvidenceView
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from tests.conftest import FakeLLMProvider

SAMPLE_PAPER = Paper(
    metadata={"title": "Attention Is All You Need", "arxiv_id": "1706.03762", "year": 2017},
    sections=[
        Section(
            title="Abstract",
            content=(
                "The dominant sequence transduction models are based on complex "
                "recurrent or convolutional neural networks. We propose the "
                "Transformer, based solely on attention mechanisms, dispensing "
                "with recurrence and convolutions entirely."
            ),
            section_type=SectionType.ABSTRACT,
            token_count=50,
        ),
        Section(
            title="Model Architecture",
            content=(
                "The Transformer follows an encoder-decoder structure. The encoder "
                "is composed of 6 identical layers, each with a multi-head "
                "self-attention sub-layer and a position-wise feed-forward network. "
                "We use 8 attention heads with model dimension 512. We train with "
                "the Adam optimizer, learning rate 0.0001, warmup steps 4000, "
                "batch size 25000 tokens, and label smoothing 0.1."
            ),
            section_type=SectionType.METHOD,
            token_count=120,
        ),
        Section(
            title="Experiments",
            content=(
                "We evaluate on WMT 2014 English-German translation. Our big "
                "Transformer model achieves 28.4 BLEU, outperforming the best "
                "previous models by more than 2.0 BLEU. Training took 3.5 days "
                "on 8 NVIDIA P100 GPUs."
            ),
            section_type=SectionType.EXPERIMENTS,
            token_count=80,
        ),
    ],
    total_pages=11,
)

FAKE_ANALYSIS_JSON = json.dumps(
    {
        "problem_statement": "Sequence transduction models rely on recurrence, which prevents parallelization and limits efficiency.",
        "algorithms": [
            {
                "name": "Transformer",
                "purpose": "Sequence-to-sequence transduction without recurrence",
                "steps": [
                    {
                        "order": 1,
                        "description": "Multi-head self-attention over input representations",
                        "evidence": {
                            "section_title": "Model Architecture",
                            "quote": "multi-head self-attention sub-layer",
                        },
                    },
                    {
                        "order": 2,
                        "description": "Position-wise feed-forward network applied independently",
                        "evidence": {
                            "section_title": "Model Architecture",
                            "quote": "position-wise feed-forward network",
                        },
                    },
                ],
                "assumptions": ["Sequences processed in parallel"],
                "evidence": {
                    "section_title": "Model Architecture",
                    "quote": "The Transformer follows an encoder-decoder structure",
                },
            }
        ],
        "architecture": [
            {
                "name": "Encoder",
                "component_type": "encoder",
                "description": "6 identical layers, each with multi-head self-attention and FFN",
                "parameters": {
                    "num_layers": {"value": 6, "status": "verified"},
                    "num_heads": {"value": 8, "status": "verified"},
                    "d_model": {"value": 512, "status": "verified"},
                },
                "evidence": {
                    "section_title": "Model Architecture",
                    "quote": "composed of 6 identical layers",
                },
            },
        ],
        "training_recipe": {
            "optimizer": {"value": "Adam", "raw_text": "Adam optimizer", "status": "verified"},
            "learning_rate": {
                "value": 0.0001,
                "raw_text": "learning rate 0.0001",
                "status": "verified",
            },
            "batch_size": {
                "value": 25000,
                "raw_text": "batch size 25000 tokens",
                "status": "verified",
            },
            "epochs": {"value": None, "status": "not_reported"},
        },
        "evaluation_protocol": {
            "datasets": [{"value": "WMT 2014 En-De", "status": "verified"}],
            "metrics": [{"value": "BLEU", "status": "verified"}],
            "reported_claims": [
                {
                    "dataset": "WMT 2014 En-De",
                    "metric_name": "BLEU",
                    "reported_value": "28.4",
                    "status": "verified",
                    "evidence": {"section_title": "Experiments", "quote": "achieves 28.4 BLEU"},
                },
            ],
        },
        "equations": [],
        "reproducibility_gaps": [
            {
                "category": "config",
                "description": "Exact learning rate schedule parameters beyond warmup steps not fully detailed",
                "impact": "May affect exact reproduction of training dynamics",
                "suggested_resolution": "Check the reference implementation on GitHub",
            },
        ],
        "assumptions": [],
    }
)


async def main() -> None:
    print("=" * 60)
    print("  ReproForge — Methodology Extraction Demo (P2)")
    print("=" * 60)
    print()

    paper = SAMPLE_PAPER
    print(f"Paper: {paper.metadata.title}")
    print(f"arXiv: {paper.metadata.arxiv_id}")
    print(f"Sections: {len(paper.sections)}")
    print()

    provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_ANALYSIS_JSON}"])
    methodologist = Methodologist(
        config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=8),
        provider=provider,
    )
    view = PaperEvidenceView(paper)

    print("Extracting methodology...")
    analysis = await methodologist.analyze(view)
    print()

    print("-" * 60)
    print("  Problem Statement")
    print("-" * 60)
    print(f"  {analysis.problem_statement}")
    print()

    print("-" * 60)
    print("  Algorithms")
    print("-" * 60)
    for algo in analysis.algorithms:
        print(f"  {algo.name}: {algo.purpose}")
        for step in algo.steps:
            print(f"    {step.order}. {step.description}")
    print()

    print("-" * 60)
    print("  Architecture")
    print("-" * 60)
    for comp in analysis.architecture:
        params = ", ".join(f"{k}={v.value}" for k, v in comp.parameters.items())
        print(f"  {comp.name} [{comp.component_type}] ({params})")
    print()

    print("-" * 60)
    print("  Training Recipe")
    print("-" * 60)
    recipe = analysis.training_recipe
    print(f"  Optimizer: {recipe.optimizer.value}")
    print(f"  Learning rate: {recipe.learning_rate.value}")
    print(f"  Batch size: {recipe.batch_size.value}")
    print(
        f"  Epochs: {recipe.epochs.value if recipe.epochs.value is not None else '(not reported)'}"
    )
    print()

    print("-" * 60)
    print("  Reported Claims")
    print("-" * 60)
    for claim in analysis.evaluation_protocol.reported_claims:
        status = claim.status.value
        print(f"  [{claim.dataset}] {claim.metric_name}: {claim.reported_value} ({status})")
        if claim.evidence.quote:
            print(f'    quote: "{claim.evidence.quote}"')
    print()

    if analysis.reproducibility_gaps:
        print("-" * 60)
        print("  Reproducibility Gaps")
        print("-" * 60)
        for gap in analysis.reproducibility_gaps:
            print(f"  [{gap.category}] {gap.description}")
            print(f"    -> {gap.suggested_resolution}")
        print()

    print("=" * 60)
    print("  Demo complete. Use a real LLM for actual extraction.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
