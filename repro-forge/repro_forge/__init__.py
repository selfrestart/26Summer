"""ReproForge paper-reading and methodology-analysis runtime.

The current package provides the complete P0-P3 runtime:
provider boundary, PDF/arXiv paper models, PaperReader, Methodologist,
evidence-grounded analysis pipelines, code generation (CodeForger),
auditable bundle contracts, fail-closed code generation, dry-run, an immutable
local fixture runner, and a digest-pinned Docker backend whose real security
smoke covers isolation, resource controls, output collection, and cleanup.
P4-P8 remain planned capabilities.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "__version__",
]
