"""Trusted Docker runtime profile resolution for P3."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

_DIGEST_IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
_PROFILE_ENV = {
    "python-cpu": "REPROFORGE_P3_PYTHON_CPU_IMAGE",
}


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    image: str


def resolve_runtime_profile(name: str) -> RuntimeProfile | None:
    """Resolve an operator-reviewed exact image digest without pulling it."""
    env_name = _PROFILE_ENV.get(name)
    if env_name is None:
        return None
    image = os.getenv(env_name, "").strip()
    if not _DIGEST_IMAGE_RE.fullmatch(image):
        return None
    return RuntimeProfile(name=name, image=image)
